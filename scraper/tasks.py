import time
import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def re_embed_product(self, client_id, product_id, title, body_html, price, url):
    """
    Re-embed a single product after a Shopify / WooCommerce webhook.
    Deletes old chunks for this product then creates a fresh one.
    """
    from users.models import Client
    from scraper.models import DocumentChunk
    from scraper.ingestion import clean_html
    from scraper.embeddings import batch_embed_texts

    try:
        client = Client.objects.get(pk=client_id)
    except Client.DoesNotExist:
        return

    try:
        description = clean_html(body_html) if body_html else ''
        content = f"Product: {title}\nPrice: ${price}\n{description}".strip()

        DocumentChunk.objects.filter(client=client, product_id=product_id).delete()

        embeddings = batch_embed_texts([content])
        if not embeddings:
            raise ValueError('Empty embedding response')

        emb = embeddings[0]
        if len(emb) < 1536:
            emb = emb + [0.0] * (1536 - len(emb))
        elif len(emb) > 1536:
            emb = emb[:1536]

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
        logger.info(f'[re_embed_product] Updated product {product_id} for client {client_id}')

    except Exception as exc:
        logger.error(f'[re_embed_product] Failed: {exc}')
        Client.objects.filter(pk=client_id).update(ingestion_status='FAILED')
        raise self.retry(exc=exc, countdown=30)


@shared_task(bind=True, max_retries=3)
def re_embed_wordpress_post(self, client_id, post_id, title, content_html, link):
    """
    Re-embed a single WordPress post after a webhook update.
    Deletes old chunks for this post then re-chunks + re-embeds.
    """
    from users.models import Client
    from scraper.models import DocumentChunk
    from scraper.ingestion import clean_html, _SPLITTER
    from scraper.embeddings import batch_embed_texts

    try:
        client = Client.objects.get(pk=client_id)
    except Client.DoesNotExist:
        return

    try:
        text = f"Title: {title}\n\n{clean_html(content_html)}"
        splits = _SPLITTER.split_text(text)
        if not splits:
            return

        DocumentChunk.objects.filter(client=client, product_id=post_id).delete()

        docs = []
        for chunk in splits:
            try:
                embs = batch_embed_texts([chunk])
                emb = embs[0] if embs else [0.0] * 1536
            except Exception:
                emb = [0.0] * 1536
            if len(emb) < 1536:
                emb = emb + [0.0] * (1536 - len(emb))
            elif len(emb) > 1536:
                emb = emb[:1536]
            docs.append(DocumentChunk(
                client=client,
                content=chunk,
                embedding=emb,
                source_url=link,
                product_id=post_id,
                metadata={'title': title, 'type': 'post'},
            ))
            time.sleep(0.5)

        DocumentChunk.objects.bulk_create(docs)
        from django.utils import timezone
        Client.objects.filter(pk=client_id).update(
            ingestion_status='DONE',
            updated_at=timezone.now(),
        )
        logger.info(f'[re_embed_wordpress_post] Re-embedded post {post_id} ({len(docs)} chunks)')

    except Exception as exc:
        logger.error(f'[re_embed_wordpress_post] Failed: {exc}')
        Client.objects.filter(pk=client_id).update(ingestion_status='FAILED')
        raise self.retry(exc=exc, countdown=30)


@shared_task(bind=True, max_retries=2)
def scrape_client_website(self, client_id):
    """
    Async task to crawl a client's website using the best available strategy:
      1. WordPress REST API  (if platform == WORDPRESS)
      2. Shopify products API (if platform == SHOPIFY)
      3. Generic HTML crawl + Playwright SPA fallback (CUSTOM / fallback)
    """
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
        client.save(update_fields=['ingestion_status', 'total_pages_ingested'])
        logger.info(f'[scrape_client_website] Done — {count} chunks for "{client.name}"')

    except Exception as exc:
        logger.error(f'[scrape_client_website] Failed for "{client.name}": {exc}')
        client.ingestion_status = 'FAILED'
        client.save(update_fields=['ingestion_status'])
        raise self.retry(exc=exc, countdown=60)
