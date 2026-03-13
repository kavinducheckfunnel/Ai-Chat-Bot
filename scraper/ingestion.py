import requests
import json
from bs4 import BeautifulSoup
from langchain_text_splitters import RecursiveCharacterTextSplitter
from .models import DocumentChunk
from .embeddings import batch_embed_texts


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

BROWSER_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/124.0.0.0 Safari/537.36'
    )
}

TEXT_SPLITTER = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=100,
    separators=["\n\n", "\n", " ", ""]
)


def clean_html(html_content):
    """Strip HTML tags and return clean readable text."""
    soup = BeautifulSoup(html_content, "html.parser")
    return soup.get_text(separator=" ", strip=True)


def _fetch_wp_endpoint(base_url, endpoint):
    """
    Generic paginated fetcher for any WP REST API endpoint
    (posts, pages, custom post types, etc.).
    Returns a flat list of all items across all pages.
    """
    api_url = f"{base_url.rstrip('/')}/wp-json/wp/v2/{endpoint}"
    all_items = []
    page = 1

    while True:
        try:
            response = requests.get(
                api_url,
                params={'per_page': 100, 'page': page, '_embed': 1},
                headers=BROWSER_HEADERS,
                timeout=15
            )
            # WP returns 400 when page is out of range
            if response.status_code not in (200, 201):
                break

            data = response.json()
            if not data:
                break

            all_items.extend(data)
            page += 1

            # WP tells us total pages via header
            total_pages = int(response.headers.get('X-WP-TotalPages', 1))
            if page > total_pages:
                break

        except Exception as e:
            print(f"[Ingestion] Error fetching {api_url} page {page}: {e}")
            break

    return all_items


def fetch_wordpress_data(site_url):
    """Fetch all posts from WordPress REST API (paginated)."""
    return _fetch_wp_endpoint(site_url, 'posts')


def fetch_wordpress_pages(site_url):
    """Fetch all pages from WordPress REST API (paginated)."""
    return _fetch_wp_endpoint(site_url, 'pages')


def _extract_text_from_post(post):
    """
    Extract a clean text representation from a WP REST API post/page object.
    Returns (title, content_text, link, post_id).
    """
    title = post.get('title', {}).get('rendered', '') or ''
    content_html = post.get('content', {}).get('rendered', '') or ''
    excerpt_html = post.get('excerpt', {}).get('rendered', '') or ''
    link = post.get('link', '') or ''
    post_id = str(post.get('id', ''))

    # Use excerpt as a summary prefix if available
    excerpt_text = clean_html(excerpt_html)
    content_text = clean_html(content_html)

    if excerpt_text and excerpt_text not in content_text:
        full_text = f"Title: {title}\nSummary: {excerpt_text}\n\n{content_text}"
    else:
        full_text = f"Title: {title}\n\n{content_text}"

    return title, full_text, link, post_id


def _build_chunks(items, content_type='post'):
    """
    Given a list of WP REST API items, return:
    - chunks_to_embed: list of text strings
    - metadata_list:   list of matching metadata dicts
    """
    chunks_to_embed = []
    metadata_list = []

    for item in items:
        title, full_text, link, post_id = _extract_text_from_post(item)

        if not full_text.strip():
            continue

        split_texts = TEXT_SPLITTER.split_text(full_text)
        for text in split_texts:
            chunks_to_embed.append(text)
            metadata_list.append({
                'source_url': link,
                'product_id': post_id,
                'metadata': {
                    'title': title,
                    'type': content_type,
                }
            })

    return chunks_to_embed, metadata_list


def _embed_and_store(client, chunks_to_embed, metadata_list):
    """
    Embed chunks in batches of 10 and bulk-insert into DocumentChunk.
    Deduplication is handled BEFORE calling this function.
    """
    import time

    BATCH_SIZE = 10
    all_embeddings = []

    total = len(chunks_to_embed)
    print(f"[Ingestion] Embedding {total} chunks in batches of {BATCH_SIZE}…")

    for i in range(0, total, BATCH_SIZE):
        batch_texts = chunks_to_embed[i:i + BATCH_SIZE]
        batch_embs = batch_embed_texts(batch_texts)
        all_embeddings.extend(batch_embs)
        print(f"[Ingestion]   Embedded {min(i + BATCH_SIZE, total)}/{total}")
        time.sleep(0.3)  # Gentle throttle to avoid AWS rate limits

    docs_to_create = []
    for i in range(len(chunks_to_embed)):
        emb = all_embeddings[i]
        meta_info = metadata_list[i]
        docs_to_create.append(
            DocumentChunk(
                client=client,
                content=chunks_to_embed[i],
                embedding=emb,
                source_url=meta_info['source_url'],
                product_id=meta_info['product_id'],
                metadata=meta_info['metadata']
            )
        )

    DocumentChunk.objects.bulk_create(docs_to_create)
    print(f"[Ingestion] Stored {len(docs_to_create)} chunks.")
    return len(docs_to_create)


# ─────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────

def process_and_store_website_data(site_url, client=None, dry_run=False):
    """
    Full-site ingestion:
      1. Fetches all posts AND pages from the WP REST API.
      2. Deduplicates by deleting all old chunks for this client first.
      3. Splits, embeds, and stores new chunks.
    """
    print(f"[Ingestion] Starting full crawl of: {site_url}")

    posts = fetch_wordpress_data(site_url)
    print(f"[Ingestion] Found {len(posts)} posts.")

    pages = fetch_wordpress_pages(site_url)
    print(f"[Ingestion] Found {len(pages)} pages.")

    post_chunks, post_meta = _build_chunks(posts, content_type='post')
    page_chunks, page_meta = _build_chunks(pages, content_type='page')

    chunks_to_embed = post_chunks + page_chunks
    metadata_list = post_meta + page_meta

    if not chunks_to_embed:
        print("[Ingestion] No content found to process.")
        return

    if dry_run:
        print(f"[DRY RUN] Would embed {len(chunks_to_embed)} chunks.")
        print("Sample chunk:\n---")
        print(chunks_to_embed[0])
        print("---")
        return

    # ── Deduplication: wipe all old chunks for this client before re-ingesting ──
    if client:
        deleted, _ = DocumentChunk.objects.filter(client=client).delete()
        print(f"[Ingestion] Cleared {deleted} stale chunks for client '{client}'.")
    else:
        # No client (global) – clear global chunks
        deleted, _ = DocumentChunk.objects.filter(client__isnull=True).delete()
        print(f"[Ingestion] Cleared {deleted} stale global chunks.")

    # ── Embed & store ──
    total_stored = _embed_and_store(client, chunks_to_embed, metadata_list)

    # ── Update client ingestion status ──
    if client:
        client.total_pages_ingested = len(posts) + len(pages)
        client.ingestion_status = 'DONE'
        client.save(update_fields=['total_pages_ingested', 'ingestion_status'])

    print(f"[Ingestion] ✅ Complete. {total_stored} chunks stored for {site_url}.")


def process_single_wordpress_post(client, post_data):
    """
    Ingest or re-ingest a single WordPress post/page from a webhook payload.
    Atomically replaces old chunks for that post ID.
    """
    post_id = str(post_data.get('id', ''))
    if not post_id:
        return {"status": "error", "message": "No post ID in payload"}

    # ── Strip old chunks for this post so updates don't accumulate ──
    DocumentChunk.objects.filter(client=client, product_id=post_id).delete()

    title, full_text, link, _ = _extract_text_from_post(post_data)

    if not full_text.strip():
        return {"status": "ignored", "message": "Post had no text content"}

    split_texts = TEXT_SPLITTER.split_text(full_text)
    if not split_texts:
        return {"status": "ignored", "message": "Text splitter produced no chunks"}

    import time
    all_embeddings = []
    BATCH_SIZE = 10

    print(f"[Ingestion] Embedding {len(split_texts)} chunks for post {post_id}…")
    for i in range(0, len(split_texts), BATCH_SIZE):
        batch = split_texts[i:i + BATCH_SIZE]
        all_embeddings.extend(batch_embed_texts(batch))
        time.sleep(0.3)

    docs_to_create = []
    for i, text in enumerate(split_texts):
        docs_to_create.append(
            DocumentChunk(
                client=client,
                content=text,
                embedding=all_embeddings[i],
                source_url=link,
                product_id=post_id,
                metadata={'title': title, 'type': 'post'}
            )
        )

    DocumentChunk.objects.bulk_create(docs_to_create)
    return {
        "status": "success",
        "message": f"Ingested {len(docs_to_create)} chunks for post {post_id}"
    }
