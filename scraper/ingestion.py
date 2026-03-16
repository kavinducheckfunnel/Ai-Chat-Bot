import time
import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from langchain_text_splitters import RecursiveCharacterTextSplitter
from .models import DocumentChunk
from .embeddings import batch_embed_texts

logger = logging.getLogger(__name__)

_SPLITTER = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=100,
    separators=["\n\n", "\n", " ", ""],
)

_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/124.0.0.0 Safari/537.36'
    )
}


def clean_html(html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    # Remove noisy boilerplate elements
    for tag in soup(['script', 'style', 'nav', 'footer', 'header',
                     'noscript', 'iframe', 'form']):
        tag.decompose()
    return soup.get_text(separator=" ", strip=True)


# ── Strategy 1: WordPress REST API ──────────────────────────────────────────

def fetch_wordpress_data(site_url):
    """
    Fetches posts or products from the WordPress REST API.
    Handles pagination.
    """
    api_url = f"{site_url.rstrip('/')}/wp-json/wp/v2/posts"
    all_posts = []
    page = 1
    per_page = 100
    
    while True:
        try:
            # Added headers because some sites block python requests User-Agent
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(api_url, params={'per_page': per_page, 'page': page}, headers=headers, timeout=10)
            if response.status_code != 200:
                print(f"Failed to fetch from {api_url}: {response.status_code}")
                break
            
            data = response.json()
            if not data:
                break
                
            all_posts.extend(data)
            page += 1
        except Exception as e:
            print(f"Error fetching data: {e}")
            break
            
    return all_posts

# ── Strategy 2: Generic HTML crawl (requests + BeautifulSoup) ───────────────

def fetch_generic_site(site_url, max_pages=50):
    """
    Breadth-first crawl of a site using requests.
    Returns list of dicts: {title, content, url}
    Falls back to Playwright if the page looks like a JS-rendered SPA.
    """
    visited = set()
    queue = [site_url.rstrip('/')]
    documents = []
    base_domain = urlparse(site_url).netloc

    while queue and len(visited) < max_pages:
        url = queue.pop(0)
        if url in visited:
            continue
        visited.add(url)

        try:
            resp = requests.get(url, headers=_HEADERS, timeout=15)
            if resp.status_code != 200:
                continue
            html = resp.text
        except Exception as e:
            logger.warning(f'[fetch_generic_site] requests failed for {url}: {e}')
            continue

        soup = BeautifulSoup(html, 'html.parser')

        # SPA detection: if body text is very short but there are <script> tags,
        # it's likely a JS-rendered app — use Playwright fallback.
        body_text = soup.get_text(strip=True)
        if len(body_text) < 200 and soup.find_all('script'):
            logger.info(f'[fetch_generic_site] SPA detected at {url}, trying Playwright')
            html = _fetch_with_playwright(url)
            if html:
                soup = BeautifulSoup(html, 'html.parser')

        title = soup.title.string.strip() if soup.title else url
        text = clean_html(html)

        if len(text) > 100:
            documents.append({'title': title, 'content': text, 'url': url})

        # Enqueue same-domain links
        for a in soup.find_all('a', href=True):
            href = a['href']
            full = urljoin(url, href).split('#')[0].split('?')[0]
            if urlparse(full).netloc == base_domain and full not in visited:
                queue.append(full)

    logger.info(f'[fetch_generic_site] Scraped {len(documents)} pages from {site_url}')
    return documents


def _fetch_with_playwright(url):
    """
    Use a headless Chromium browser to fetch a JS-rendered page.
    Returns rendered HTML string, or None if Playwright is not available.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.warning('[_fetch_with_playwright] Playwright not installed — skipping SPA fallback')
        return None

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until='networkidle', timeout=20000)
            html = page.content()
            browser.close()
            return html
    except Exception as e:
        logger.warning(f'[_fetch_with_playwright] Failed for {url}: {e}')
        return None


# ── Strategy 3: Shopify JSON API ─────────────────────────────────────────────

def fetch_shopify_data(site_url):
    """
    Fetch products from Shopify's public /products.json endpoint (no auth needed).
    Returns list of dicts: {title, content, url}
    """
    api_url = f"{site_url.rstrip('/')}/products.json"
    documents = []
    page = 1
    while True:
        try:
            resp = requests.get(
                api_url,
                params={'limit': 250, 'page': page},
                headers=_HEADERS,
                timeout=15,
            )
            if resp.status_code != 200:
                break
            products = resp.json().get('products', [])
            if not products:
                break
            for p in products:
                title = p.get('title', '')
                body = BeautifulSoup(p.get('body_html', ''), 'html.parser').get_text(' ', True)
                variants = ', '.join(
                    f"{v['title']} ${v['price']}"
                    for v in p.get('variants', [])
                    if v.get('price')
                )
                content = f"Product: {title}\n{body}"
                if variants:
                    content += f"\nVariants: {variants}"
                handle = p.get('handle', '')
                documents.append({
                    'title': title,
                    'content': content,
                    'url': f"{site_url.rstrip('/')}/products/{handle}",
                    'product_id': str(p.get('id', '')),
                })
            page += 1
        except Exception as e:
            logger.warning(f'[fetch_shopify_data] Error: {e}')
            break
    logger.info(f'[fetch_shopify_data] Fetched {len(documents)} products from {site_url}')
    return documents


# ── Master scraper: auto-detect strategy ─────────────────────────────────────

def auto_scrape(client):
    """
    Detect the best scraping strategy for a client and return raw document dicts.
    Order of preference:
      1. WordPress REST API (fastest, structured)
      2. Shopify /products.json
      3. Generic HTML crawl + Playwright SPA fallback
    """
    url = client.domain_url
    platform = (client.platform or '').upper()

    if platform == 'WORDPRESS':
        posts = fetch_wordpress_data(url)
        if posts:
            # Convert WP post format → standard format
            docs = []
            for p in posts:
                title = p.get('title', {}).get('rendered', '')
                html = p.get('content', {}).get('rendered', '')
                docs.append({
                    'title': title,
                    'content': f"Title: {title}\n\n{clean_html(html)}",
                    'url': p.get('link', url),
                    'product_id': str(p.get('id', '')),
                })
            return docs
        # WP API returned nothing — fall through to generic
        logger.info(f'[auto_scrape] WP REST API empty for {url}, falling back to generic crawl')

    if platform == 'SHOPIFY':
        docs = fetch_shopify_data(url)
        if docs:
            return docs

    # Generic fallback for CUSTOM or when platform-specific APIs fail
    return fetch_generic_site(url)


# ── Shared ingestion pipeline ─────────────────────────────────────────────────

def ingest_documents(client, documents):
    """
    Takes a list of {title, content, url, product_id?} dicts,
    chunks them, embeds them, and stores DocumentChunk rows.
    Returns the number of chunks created.
    """
    if not documents:
        return 0

    chunks_text = []
    chunks_meta = []

    for doc in documents:
        text = doc.get('content', '') or doc.get('title', '')
        if not text or len(text.strip()) < 30:
            continue
        splits = _SPLITTER.split_text(text)
        for split in splits:
            chunks_text.append(split)
            chunks_meta.append({
                'source_url': doc.get('url', ''),
                'product_id': doc.get('product_id', ''),
                'title': doc.get('title', ''),
            })

    if not chunks_text:
        return 0

    # Delete existing chunks for this client before re-ingesting
    DocumentChunk.objects.filter(client=client).delete()

    # Embed in batches of 1 (rate-limit safe)
    all_embeddings = []
    for i, chunk in enumerate(chunks_text):
        try:
            embs = batch_embed_texts([chunk])
            emb = embs[0] if embs else [0.0] * 1536
        except Exception as e:
            logger.warning(f'[ingest_documents] Embedding failed for chunk {i}: {e}')
            emb = [0.0] * 1536
        # Normalise to 1536 dims
        if len(emb) < 1536:
            emb = emb + [0.0] * (1536 - len(emb))
        elif len(emb) > 1536:
            emb = emb[:1536]
        all_embeddings.append(emb)
        time.sleep(0.5)

    docs_to_create = [
        DocumentChunk(
            client=client,
            content=chunks_text[i],
            embedding=all_embeddings[i],
            source_url=chunks_meta[i]['source_url'],
            product_id=chunks_meta[i]['product_id'] or None,
            metadata={'title': chunks_meta[i]['title']},
        )
        for i in range(len(chunks_text))
    ]
    DocumentChunk.objects.bulk_create(docs_to_create, batch_size=100)
    logger.info(f'[ingest_documents] Created {len(docs_to_create)} chunks for client {client.pk}')
    return len(docs_to_create)


def process_and_store_website_data(site_url, client=None, dry_run=False):
    print(f"Starting crawl of: {site_url}")
    posts = fetch_wordpress_data(site_url)
    print(f"Found {len(posts)} posts/pages.")
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=100,
        separators=["\n\n", "\n", " ", ""]
    )
    
    chunks_to_embed = []
    metadata_list = []
    
    for post in posts:
        title = post.get('title', {}).get('rendered', '')
        content_html = post.get('content', {}).get('rendered', '')
        content_text = clean_html(content_html)
        link = post.get('link', '')
        post_id = post.get('id')
        
        full_text = f"Title: {title}\n\n{content_text}"
        
        split_texts = text_splitter.split_text(full_text)
        for text in split_texts:
            chunks_to_embed.append(text)
            metadata_list.append({
                'source_url': link,
                'product_id': post_id,
                'metadata': {
                    'title': title,
                    'type': 'post'
                }
            })
            
    if chunks_to_embed:
        import time
        # Batch size handling
        batch_size = 1
        all_embeddings = []
        
        if dry_run:
            print(f"DRY RUN: Successfully scraped {len(chunks_to_embed)} chunks from {site_url}.")
            print("First chunk content sample:")
            print("---")
            print(chunks_to_embed[0])
            print("---")
            print("Skipping Gemini Embeddings due to pure-scraping test.")
            return

        print("Generating AWS Bedrock Embeddings...")
        for i in range(0, len(chunks_to_embed), batch_size):
            batch_texts = chunks_to_embed[i:i+batch_size]
            batch_embs = batch_embed_texts(batch_texts)
            all_embeddings.extend(batch_embs)
            print(f"Embedded chunk {i+1} out of {len(chunks_to_embed)}...")
            time.sleep(1.0)  # Avoid AWS Throttling limits
            
        # Bulk create DocumentChunks
        docs_to_create = []
        for i in range(len(chunks_to_embed)):
            emb = all_embeddings[i]
            # Since we set pgvector dimensions=1536 but gemini might return 768 by default
            # Actually, let's pad vectors to 1536 if gemini returns 768. 
            # Or pass task_type="RETRIEVAL_DOCUMENT" etc. Wait, we should just let it be stored.
            if len(emb) < 1536:
                emb = emb + [0.0] * (1536 - len(emb))
            elif len(emb) > 1536:
                emb = emb[:1536]
                
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
        print(f"Successfully processed and stored {len(docs_to_create)} chunks.")
    else:
        print("No content to process.")

def process_single_wordpress_post(client, post_data):
    """
    Ingest a single WordPress post from webhook payload.
    post_data should be a dict from the WP REST API representing one post.
    """
    post_id = post_data.get('id')
    if not post_id:
        return {"status": "error", "message": "No post ID provided"}
        
    # 1. Delete old chunks for this post to avoid duplicates on update
    DocumentChunk.objects.filter(client=client, product_id=str(post_id)).delete()
    
    # 2. Extract content
    title = post_data.get('title', {}).get('rendered', '')
    content_html = post_data.get('content', {}).get('rendered', '')
    content_text = clean_html(content_html)
    link = post_data.get('link', '')
    
    full_text = f"Title: {title}\n\n{content_text}"
    
    # 3. Split Text
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=100,
        separators=["\n\n", "\n", " ", ""]
    )
    split_texts = text_splitter.split_text(full_text)
    
    if not split_texts:
        return {"status": "ignored", "message": "Post had no text content"}
        
    # 4. Embed
    import time
    all_embeddings = []
    
    print(f"Generating Bedrock Embeddings for post {post_id}...")
    for text in split_texts:
        batch_embs = batch_embed_texts([text])
        all_embeddings.extend(batch_embs)
        time.sleep(1.0) # Avoid AWS limits
        
    # 5. Save
    docs_to_create = []
    for i, text in enumerate(split_texts):
        emb = all_embeddings[i]
        if len(emb) < 1536:
            emb = emb + [0.0] * (1536 - len(emb))
        elif len(emb) > 1536:
            emb = emb[:1536]
            
        docs_to_create.append(
            DocumentChunk(
                client=client,
                content=text,
                embedding=emb,
                source_url=link,
                product_id=str(post_id),
                metadata={'title': title, 'type': 'post'}
            )
        )
        
    DocumentChunk.objects.bulk_create(docs_to_create)
    return {"status": "success", "message": f"Ingested {len(docs_to_create)} chunks for post {post_id}"}
