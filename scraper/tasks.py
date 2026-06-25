import time
import logging
from django.db import models
from celery import shared_task

logger = logging.getLogger(__name__)


def _close_event(event_id, status, error='', started_at=None):
    """
    Mark a WebhookEvent row done / failed once the embedding task finishes.
    Best-effort: never raises so it can't break the embedding task itself.
    """
    if not event_id:
        return
    try:
        from scraper.models import WebhookEvent
        update = {'status': status, 'error_message': (error or '')[:5000]}
        if started_at is not None:
            update['duration_ms'] = int((time.time() - started_at) * 1000)
        WebhookEvent.objects.filter(pk=event_id).update(**update)
    except Exception as e:
        logger.warning(f'[_close_event] Could not update event {event_id}: {e}')


@shared_task(bind=True, max_retries=3)
def re_embed_product(self, client_id, product_id, title, body_html, price, url, event_id=None):
    """
    Re-embed a single product after a Shopify / WooCommerce webhook.
    Deletes old chunks for this product then creates a fresh one.
    """
    from users.models import Client
    from scraper.models import DocumentChunk
    from scraper.ingestion import clean_html
    from scraper.embeddings import batch_embed_texts

    started = time.time()
    try:
        client = Client.objects.get(pk=client_id)
    except Client.DoesNotExist:
        _close_event(event_id, 'failed', 'Client not found', started)
        return

    try:
        description = clean_html(body_html) if body_html else ''
        content = f"Product: {title}\nPrice: ${price}\n{description}".strip()

        DocumentChunk.objects.filter(client=client, product_id=product_id).delete()

        embeddings = batch_embed_texts([content])
        if not embeddings:
            raise ValueError('Empty embedding response')

        emb = embeddings[0]
        if len(emb) < 1024:
            emb = emb + [0.0] * (1024 - len(emb))
        elif len(emb) > 1024:
            emb = emb[:1024]

        DocumentChunk.objects.create(
            client=client,
            content=content,
            embedding=emb,
            source_url=url,
            product_id=product_id,
            metadata={'title': title, 'type': 'product'},
        )
        from django.utils import timezone
        Client.objects.filter(pk=client_id).update(
            ingestion_status='DONE',
            updated_at=timezone.now(),
        )
        _close_event(event_id, 'done', '', started)
        logger.info(f'[re_embed_product] Updated product {product_id} for client {client_id}')

    except Exception as exc:
        logger.error(f'[re_embed_product] Failed: {exc}')
        Client.objects.filter(pk=client_id).update(ingestion_status='FAILED')
        _close_event(event_id, 'failed', str(exc), started)
        raise self.retry(exc=exc, countdown=30)


@shared_task(bind=True, max_retries=3)
def re_embed_wordpress_post(self, client_id, post_id, title, content_html, link, event_id=None, post_type='post'):
    """
    Re-embed a single WordPress post or page after a webhook update.
    Deletes old chunks for this post then re-chunks + re-embeds.

    post_type is tagged into metadata.type so the inbox/timeline UI can
    show "Page" vs "Post" labels and the AI can prioritise differently
    when answering "what's on your About page" vs blog-content questions.
    """
    from users.models import Client
    from scraper.models import DocumentChunk
    from scraper.ingestion import clean_html, _SPLITTER
    from scraper.embeddings import batch_embed_texts

    started = time.time()
    try:
        client = Client.objects.get(pk=client_id)
    except Client.DoesNotExist:
        _close_event(event_id, 'failed', 'Client not found', started)
        return

    try:
        text = f"Title: {title}\n\n{clean_html(content_html)}"
        splits = _SPLITTER.split_text(text)
        if not splits:
            _close_event(event_id, 'done', '', started)
            return

        DocumentChunk.objects.filter(client=client, product_id=post_id).delete()

        docs = []
        for chunk in splits:
            # Prefix every chunk with the title so mid-article chunks
            # remain identifiable to the AI.
            prefixed = f"Title: {title}\n\n{chunk}"
            try:
                embs = batch_embed_texts([prefixed])
                emb = embs[0] if embs else [0.0] * 1024
            except Exception:
                emb = [0.0] * 1024
            if len(emb) < 1024:
                emb = emb + [0.0] * (1024 - len(emb))
            elif len(emb) > 1024:
                emb = emb[:1024]
            docs.append(DocumentChunk(
                client=client,
                content=prefixed,
                embedding=emb,
                source_url=link,
                product_id=post_id,
                metadata={'title': title, 'type': post_type or 'post'},
            ))
            time.sleep(0.5)

        DocumentChunk.objects.bulk_create(docs)
        from django.utils import timezone
        Client.objects.filter(pk=client_id).update(
            ingestion_status='DONE',
            updated_at=timezone.now(),
        )
        _close_event(event_id, 'done', '', started)
        logger.info(f'[re_embed_wordpress_post] Re-embedded post {post_id} ({len(docs)} chunks)')

    except Exception as exc:
        logger.error(f'[re_embed_wordpress_post] Failed: {exc}')
        Client.objects.filter(pk=client_id).update(ingestion_status='FAILED')
        _close_event(event_id, 'failed', str(exc), started)
        raise self.retry(exc=exc, countdown=30)


@shared_task(bind=True, max_retries=2)
def scrape_client_website(self, client_id):
    """
    Async task to crawl a client's website using the best available strategy:
      1. WordPress REST API  (if platform == WORDPRESS)
      2. Shopify products API (if platform == SHOPIFY)
      3. Generic HTML crawl + Playwright SPA fallback (CUSTOM / fallback)
    """
    from django.utils import timezone
    from users.models import Client
    from scraper.ingestion import auto_scrape, ingest_documents

    try:
        client = Client.objects.get(pk=client_id)
    except Client.DoesNotExist:
        logger.warning(f'[scrape_client_website] Client {client_id} not found')
        return

    logger.info(f'[scrape_client_website] Starting scrape for "{client.name}" ({client.platform})')
    client.ingestion_status = 'RUNNING'
    client.save(update_fields=['ingestion_status'])

    try:
        documents = auto_scrape(client)
        count = ingest_documents(client, documents)

        client.ingestion_status = 'DONE'
        client.total_pages_ingested = count
        client.last_scraped_at = timezone.now()
        client.save(update_fields=['ingestion_status', 'total_pages_ingested', 'last_scraped_at'])
        logger.info(f'[scrape_client_website] Done — {count} chunks for "{client.name}"')

        try:
            sync_site_pages(client)
        except Exception as e:
            logger.warning(f'[scrape_client_website] site-page sync failed: {e}')

    except Exception as exc:
        logger.error(f'[scrape_client_website] Failed for "{client.name}": {exc}')
        client.ingestion_status = 'FAILED'
        client.save(update_fields=['ingestion_status'])
        raise self.retry(exc=exc, countdown=60)


def sync_site_pages(client):
    """Rebuild the high-level SitePage list for a client from its embedded
    pages. Collapsed to ONE representative page per page_type (so a store with
    thousands of products yields a clean ~10-row list the tenant attaches
    rules to), keyed by chat.page_rules.classify_path.
    """
    from urllib.parse import urlparse
    from scraper.models import DocumentChunk, SitePage
    from chat.page_rules import classify_path

    seen = {}  # page_type -> (path, url, title)
    rows = (DocumentChunk.objects
            .filter(client=client)
            .values_list('source_url', 'metadata')[:5000])
    for url, meta in rows:
        if not url:
            continue
        try:
            path = urlparse(url).path or '/'
        except Exception:
            path = '/'
        pt = classify_path(path)
        if pt in seen:
            continue
        title = ''
        if isinstance(meta, dict):
            title = (meta.get('title') or '')[:300]
        seen[pt] = (path, url, title)

    keep_paths = []
    for pt, (path, url, title) in seen.items():
        SitePage.objects.update_or_create(
            client=client, path=path,
            defaults={'url': url, 'title': title, 'page_type': pt},
        )
        keep_paths.append(path)
    # Drop stale rows no longer represented.
    SitePage.objects.filter(client=client).exclude(path__in=keep_paths).delete()
    return len(keep_paths)


@shared_task
def auto_rescrape_stale_clients():
    """
    Periodic safety-net task — runs daily at 02:00 UTC via Celery Beat.
    Finds every active client whose knowledge base is stale (last scraped
    > 24 hours ago, or never scraped) and queues a fresh full crawl.

    Real-time changes are covered by per-platform webhooks
    (see scraper/views.py). This task only catches what webhooks missed:
    new pages on custom HTML sites, drift in deleted-but-still-embedded
    chunks, tenants who haven't configured webhooks yet, etc.

    Skips clients currently being scraped (RUNNING) to avoid overlap.
    """
    from django.utils import timezone
    from datetime import timedelta
    from users.models import Client

    threshold = timezone.now() - timedelta(hours=24)

    stale_clients = Client.objects.filter(
        is_active=True,
        domain_url__isnull=False,
    ).exclude(
        ingestion_status='RUNNING',
    ).filter(
        # Never scraped, or last scrape was more than 3 hours ago
        models.Q(last_scraped_at__isnull=True) | models.Q(last_scraped_at__lt=threshold)
    )

    count = stale_clients.count()
    if count == 0:
        logger.info('[auto_rescrape] All clients are up to date, nothing to scrape.')
        return

    logger.info(f'[auto_rescrape] Queuing rescrape for {count} stale client(s).')
    for client in stale_clients:
        scrape_client_website.delay(str(client.id))
        logger.info(f'[auto_rescrape] Queued: {client.name} (last scraped: {client.last_scraped_at})')


# ─── Phase 2: targeted single-URL re-embed (sitemap watcher uses this) ───────

@shared_task(bind=True, max_retries=2)
def re_embed_url(self, client_id, url, event_id=None):
    """
    Fetch a single page, clean it, chunk it, embed it, replace any prior
    chunks for that source_url. Used by:
      - the sitemap watcher when it sees a page's <lastmod> advance
      - any future "this URL changed" webhook variant

    Different from re_embed_wordpress_post in that we don't have a
    post_id — chunks are identified by source_url instead.
    """
    from users.models import Client
    from scraper.models import DocumentChunk
    from scraper.ingestion import _fetch_url, clean_html, _SPLITTER
    from scraper.embeddings import batch_embed_texts

    started = time.time()
    try:
        client = Client.objects.get(pk=client_id)
    except Client.DoesNotExist:
        _close_event(event_id, 'failed', 'Client not found', started)
        return

    try:
        # _fetch_url returns (html, final_url) — must unpack. The old code
        # was treating the whole tuple as html, which made every sitemap
        # re-embed fail with "expected string or bytes-like object, got
        # 'tuple'" downstream in clean_html. That's the 672/24h failure
        # rate from the original bug report.
        html, _final_url = _fetch_url(url)
        if not html:
            _close_event(event_id, 'failed', 'Fetch returned empty body', started)
            return

        title = ''
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            t = soup.find('title')
            if t and t.text:
                title = t.text.strip()[:200]
        except Exception:
            pass

        text = clean_html(html)
        if not text or len(text) < 80:
            _close_event(event_id, 'done', 'Page too short to embed', started)
            return

        prefixed_text = f'Title: {title}\n\n{text}' if title else text
        splits = _SPLITTER.split_text(prefixed_text)
        if not splits:
            _close_event(event_id, 'done', '', started)
            return

        # Replace prior chunks for THIS url. source_url is the natural key.
        DocumentChunk.objects.filter(client=client, source_url=url).delete()

        docs = []
        for chunk in splits:
            try:
                embs = batch_embed_texts([chunk])
                emb = embs[0] if embs else [0.0] * 1024
            except Exception:
                emb = [0.0] * 1024
            if len(emb) < 1024:
                emb = emb + [0.0] * (1024 - len(emb))
            elif len(emb) > 1024:
                emb = emb[:1024]
            docs.append(DocumentChunk(
                client=client,
                content=chunk,
                embedding=emb,
                source_url=url,
                metadata={'title': title, 'type': 'page', 'via': 'sitemap'},
            ))
            time.sleep(0.3)

        DocumentChunk.objects.bulk_create(docs)
        from django.utils import timezone
        Client.objects.filter(pk=client_id).update(
            ingestion_status='DONE',
            updated_at=timezone.now(),
        )
        _close_event(event_id, 'done', '', started)
        logger.info(f'[re_embed_url] Re-embedded {url} ({len(docs)} chunks) for client {client_id}')
    except Exception as exc:
        logger.error(f'[re_embed_url] Failed for {url}: {exc}')
        _close_event(event_id, 'failed', str(exc), started)
        raise self.retry(exc=exc, countdown=60)


# ─── Phase C: Real-time inventory sync (Shopify) ──────────────────────────────


@shared_task(bind=True, max_retries=3)
def update_inventory_for_variant(self, client_id, inventory_item_id, available, event_id=None):
    """
    Apply a Shopify `inventory_levels/update` webhook to the affected
    DocumentChunk.

    Lookup path:
      chunk.metadata.variants[].inventory_item_id == inventory_item_id
      (captured during the catalog scrape by `_shopify_products`).

    What we update:
      • the matching variant's `available` count in metadata.variants
      • a top-level metadata.is_active flag so RAG can suppress sold-out chunks
      • the chunk content gets a stable `Stock: N units` / `Stock: SOLD OUT`
        line so the LLM picks up the change at retrieval time without
        having to re-read metadata at runtime
      • re-embed the chunk so similarity search reflects the new wording

    This is a *write-affected-only* path — we never touch chunks that
    don't reference this inventory_item_id, so a 50-product store with
    one stock change does exactly one embedding call.
    """
    from django.utils import timezone
    from users.models import Client
    from scraper.models import DocumentChunk
    from scraper.embeddings import batch_embed_texts

    started = time.time()
    try:
        client = Client.objects.get(pk=client_id)
    except Client.DoesNotExist:
        _close_event(event_id, 'failed', 'Client not found', started)
        return 'no_client'

    try:
        # Postgres JSONB contains query — fast & uses the GIN index if
        # one's added later. Falls back to a Python filter for tests that
        # use SQLite, which doesn't support `__contains` on JSONField for
        # nested arrays.
        try:
            candidate_chunks = list(
                DocumentChunk.objects.filter(
                    client=client,
                    metadata__variants__contains=[{'inventory_item_id': int(inventory_item_id)}],
                )
            )
        except Exception:
            candidate_chunks = []
        if not candidate_chunks:
            # Fallback: in-memory scan of this client's product chunks.
            # Only relevant if the JSONB query above isn't available
            # (e.g. SQLite in tests) or if inventory_item_id stored as str.
            candidate_chunks = [
                c for c in DocumentChunk.objects.filter(client=client)
                if any(
                    str(v.get('inventory_item_id')) == str(inventory_item_id)
                    for v in (c.metadata or {}).get('variants', []) or []
                )
            ]

        if not candidate_chunks:
            _close_event(event_id, 'done', 'No matching chunk', started)
            logger.info(
                f'[update_inventory_for_variant] No chunk for '
                f'inventory_item_id={inventory_item_id} on client {client_id}'
            )
            return 'no_chunk'

        updated_count = 0
        for chunk in candidate_chunks:
            md = dict(chunk.metadata or {})
            variants = list(md.get('variants') or [])
            for v in variants:
                if str(v.get('inventory_item_id')) == str(inventory_item_id):
                    v['available'] = int(available)
            md['variants'] = variants
            # Top-level flag: any variant available → active; all 0 → inactive.
            any_in_stock = any((v.get('available') or 0) > 0 for v in variants)
            md['is_active'] = bool(any_in_stock)

            # Append / refresh a stable stock line in the chunk content
            # so the LLM sees it as part of the retrieved context.
            stock_line = (
                f'Stock: {int(available)} units'
                if int(available) > 0 else 'Stock: SOLD OUT'
            )
            content_lines = [
                ln for ln in (chunk.content or '').splitlines()
                if not ln.startswith('Stock:')
            ]
            content_lines.append(stock_line)
            new_content = '\n'.join(content_lines)

            embeddings = batch_embed_texts([new_content])
            emb = embeddings[0] if embeddings else [0.0] * 1024
            if len(emb) < 1024:
                emb = emb + [0.0] * (1024 - len(emb))
            elif len(emb) > 1024:
                emb = emb[:1024]

            chunk.metadata = md
            chunk.content = new_content
            chunk.embedding = emb
            chunk.save(update_fields=['metadata', 'content', 'embedding'])
            updated_count += 1

        Client.objects.filter(pk=client_id).update(updated_at=timezone.now())
        _close_event(event_id, 'done', f'Updated {updated_count} chunk(s)', started)
        logger.info(
            f'[update_inventory_for_variant] Updated {updated_count} chunk(s) '
            f'for inventory_item_id={inventory_item_id}, client {client_id}'
        )
        return f'updated:{updated_count}'

    except Exception as exc:
        logger.error(f'[update_inventory_for_variant] Failed: {exc}')
        _close_event(event_id, 'failed', str(exc), started)
        raise self.retry(exc=exc, countdown=30)


# ─── Phase 2: DELETE handler (Shopify/WC/WP product or post deleted) ─────────

@shared_task
def delete_chunks_for_resource(client_id, resource_id, event_id=None):
    """
    Remove all chunks for a resource (product / post / page) after the CMS
    fired a delete webhook. Stops the AI from recommending products that
    no longer exist or quoting pages that were taken down.

    resource_id matches DocumentChunk.product_id which is reused across
    products AND wordpress posts (both store their CMS id there).
    """
    from django.utils import timezone
    from users.models import Client
    from scraper.models import DocumentChunk

    started = time.time()
    try:
        deleted, _ = DocumentChunk.objects.filter(
            client_id=client_id,
            product_id=str(resource_id),
        ).delete()
        Client.objects.filter(pk=client_id).update(updated_at=timezone.now())
        _close_event(event_id, 'done', f'Deleted {deleted} chunk(s)', started)
        logger.info(f'[delete_chunks_for_resource] Removed {deleted} chunk(s) for resource {resource_id}, client {client_id}')
    except Exception as exc:
        logger.error(f'[delete_chunks_for_resource] Failed: {exc}')
        _close_event(event_id, 'failed', str(exc), started)


# ─── Phase 2: sitemap-based change watcher (covers custom HTML sites) ────────

@shared_task
def watch_sitemaps_for_changes():
    """
    Periodic task — runs every 15 minutes via Celery Beat.

    For every active client with a domain_url, fetches the site's sitemap
    and compares each URL's <lastmod> against the most recent
    DocumentChunk.created_at for the same source_url. Any URL whose
    lastmod is newer (or that's never been embedded) gets a targeted
    re_embed_url() — giving near-real-time push semantics to sites that
    have no native webhook story (Webflow, Squarespace, static HTML,
    Notion, etc.).

    Lightweight: a single HTTP GET to sitemap.xml per client, no
    embedding API call unless content actually changed.
    """
    from datetime import datetime
    from users.models import Client
    from scraper.ingestion import fetch_sitemap_with_lastmod
    from scraper.models import DocumentChunk, WebhookEvent

    clients = list(
        Client.objects
        .filter(is_active=True, domain_url__isnull=False)
        .exclude(domain_url='')
    )
    if not clients:
        return

    logger.info(f'[watch_sitemaps] Checking {len(clients)} client(s) for sitemap changes.')

    total_queued = 0
    for client in clients:
        try:
            entries = fetch_sitemap_with_lastmod(client.domain_url, max_urls=500)
        except Exception as e:
            logger.warning(f'[watch_sitemaps] Sitemap fetch failed for {client.name}: {e}')
            continue
        if not entries:
            continue

        # Map current URLs → latest chunk created_at for this client
        urls = [u for u, _ in entries]
        existing = {
            row['source_url']: row['latest']
            for row in DocumentChunk.objects
                .filter(client=client, source_url__in=urls)
                .values('source_url')
                .annotate(latest=models.Max('created_at'))
        }

        queued_for_client = 0
        for url, lastmod in entries:
            should_embed = False
            if url not in existing:
                # Never seen before
                should_embed = True
            elif lastmod:
                try:
                    # lastmod is ISO 8601 in sitemaps. fromisoformat handles
                    # the common shapes; if it fails we conservatively skip.
                    lm_dt = datetime.fromisoformat(lastmod.replace('Z', '+00:00'))
                    if lm_dt > existing[url]:
                        should_embed = True
                except Exception:
                    pass

            if should_embed:
                event = WebhookEvent.objects.create(
                    client=client,
                    source='sitemap',
                    event_type='page.changed',
                    resource_id='',
                    resource_title=url[:300],
                    status='queued',
                )
                re_embed_url.delay(str(client.id), url, event.id)
                queued_for_client += 1
                # Per-client safety cap so a freshly added giant site
                # doesn't flood the embed queue in one tick.
                if queued_for_client >= 25:
                    break

        if queued_for_client:
            logger.info(f'[watch_sitemaps] Queued {queued_for_client} URL(s) for {client.name}.')
            total_queued += queued_for_client

    logger.info(f'[watch_sitemaps] Total queued this run: {total_queued}.')
