import time
import logging
import requests
import xml.etree.ElementTree as ET
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

# Signatures that indicate a bot-protection challenge page rather than real content
_BOT_CHALLENGE_SIGNATURES = [
    'checking your browser',
    'just a moment',
    'please wait while we verify',
    'cloudflare',
    'ddos-guard',
    'ray id',
    'enable javascript',
    'checking if the site connection is secure',
]

# URL patterns that identify individual product/content pages worth prioritising
_PRODUCT_URL_PATTERNS = [
    '/product/', '/products/', '/shop/', '/item/', '/p/',
    '/collections/', '/catalog/', '/store/', '/buy/',
]

# URL patterns to skip entirely (low-value admin/utility pages)
_SKIP_URL_PATTERNS = [
    '/wp-admin/', '/wp-login', '/wp-json/', '/xmlrpc',
    '/cart', '/checkout', '/my-account', '/login', '/register',
    '/cdn-cgi/', '/feed/', '?replytocom=', '/page/', '/tag/',
]

# XML sitemap namespace
_SITEMAP_NS = 'http://www.sitemaps.org/schemas/sitemap/0.9'


def clean_html(html_content):
    """Strip HTML tags and return clean readable text."""
    soup = BeautifulSoup(html_content, "html.parser")
    for tag in soup(['script', 'style', 'nav', 'footer', 'header',
                     'noscript', 'iframe', 'form']):
        tag.decompose()
    return soup.get_text(separator=" ", strip=True)


def _is_bot_challenge(html, status_code):
    """Return True if the response looks like a bot-protection challenge page."""
    if status_code in (403, 503):
        return True
    lower = html.lower()
    return any(sig in lower for sig in _BOT_CHALLENGE_SIGNATURES)


def _fetch_url(url, use_playwright_fallback=True):
    """
    Fetch a URL with requests. If the response looks like a bot challenge,
    fall back to Playwright automatically.
    Returns (html, final_url) or (None, url) on failure.
    """
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=15)
        html = resp.text
        if _is_bot_challenge(html, resp.status_code) and use_playwright_fallback:
            logger.info(f'[_fetch_url] Bot protection detected at {url}, using Playwright')
            pw_html = _fetch_with_playwright(url)
            if pw_html:
                return pw_html, url
            return None, url
        if resp.status_code != 200:
            return None, url
        return html, url
    except Exception as e:
        logger.warning(f'[_fetch_url] requests failed for {url}: {e}')
        return None, url


# ── Strategy 1: WordPress REST API ──────────────────────────────────────────

def fetch_wordpress_data(site_url):
    """
    Fetch posts, pages, AND WooCommerce products (product CPT) via the WP REST API.
    Returns a list of standard {title, content, url, product_id} dicts.
    """
    all_docs = []
    base = site_url.rstrip('/')

    # wp/v2 endpoints: posts + pages for blog content; product for WooCommerce
    for endpoint in ['posts', 'pages', 'product']:
        page = 1
        while True:
            try:
                response = requests.get(
                    f"{base}/wp-json/wp/v2/{endpoint}",
                    params={'per_page': 100, 'page': page, '_embed': 1},
                    headers=_HEADERS,
                    timeout=15,
                )
                if response.status_code not in (200, 201):
                    break
                data = response.json()
                if not data or not isinstance(data, list):
                    break

                for p in data:
                    title = p.get('title', {}).get('rendered', '')
                    html  = p.get('content', {}).get('rendered', '')
                    link  = p.get('link', base)
                    pid   = str(p.get('id', ''))
                    excerpt = BeautifulSoup(
                        p.get('excerpt', {}).get('rendered', ''), 'html.parser'
                    ).get_text(' ', True)

                    # Build content with URL embedded so AI always has the direct link
                    parts = [f"Title: {title}", f"URL: {link}"]
                    if excerpt:
                        parts.append(excerpt)
                    parts.append(clean_html(html))

                    all_docs.append({
                        'title': title,
                        'content': '\n'.join(parts),
                        'url': link,
                        'product_id': pid,
                    })

                page += 1
                if len(data) < 100:
                    break
            except Exception as e:
                logger.warning(f'[fetch_wordpress_data] Error on {endpoint} page {page}: {e}')
                break

    logger.info(f'[fetch_wordpress_data] Fetched {len(all_docs)} items from {site_url}')
    return all_docs


# ── Strategy 2: Sitemap-based URL discovery ──────────────────────────────────

def fetch_sitemap_urls(site_url, max_urls=300):
    """
    Discover all page/product URLs from the site's XML sitemap(s).
    Tries WordPress native sitemap, Yoast SEO, and generic sitemap.xml.
    Returns a flat list of unique page URLs, with product URLs first.
    """
    base = site_url.rstrip('/')

    sitemap_candidates = [
        f'{base}/wp-sitemap.xml',        # WordPress 5.5+ native
        f'{base}/sitemap_index.xml',     # Yoast SEO index
        f'{base}/sitemap.xml',           # Generic / other plugins
        f'{base}/product-sitemap.xml',   # Yoast product-specific
        f'{base}/post-sitemap.xml',
    ]

    raw_urls = []

    for sm_url in sitemap_candidates:
        try:
            resp = requests.get(sm_url, headers=_HEADERS, timeout=10)
            if resp.status_code != 200:
                continue
            text = resp.text.strip()
            if not text.startswith('<'):
                continue  # Bot challenge or HTML page, not XML

            root = ET.fromstring(text)

            # Sitemap index? -> fetch each sub-sitemap
            sub_locs = root.findall(f'{{{_SITEMAP_NS}}}sitemap/{{{_SITEMAP_NS}}}loc')
            if sub_locs:
                for loc in sub_locs:
                    sub_url = loc.text.strip()
                    try:
                        sr = requests.get(sub_url, headers=_HEADERS, timeout=10)
                        if sr.status_code == 200 and sr.text.strip().startswith('<'):
                            sr_root = ET.fromstring(sr.text)
                            raw_urls += [
                                u.text.strip()
                                for u in sr_root.findall(f'{{{_SITEMAP_NS}}}url/{{{_SITEMAP_NS}}}loc')
                            ]
                    except Exception:
                        pass
            else:
                # Plain sitemap
                raw_urls += [
                    u.text.strip()
                    for u in root.findall(f'{{{_SITEMAP_NS}}}url/{{{_SITEMAP_NS}}}loc')
                ]

            if raw_urls:
                logger.info(f'[fetch_sitemap_urls] Found {len(raw_urls)} raw URLs from {sm_url}')
                break

        except Exception as e:
            logger.debug(f'[fetch_sitemap_urls] {sm_url}: {e}')

    # Clean, deduplicate, skip binary/admin URLs, sort products first
    skip_exts = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg',
                 '.pdf', '.zip', '.css', '.js', '.xml', '.ico')
    seen = set()
    products = []
    others = []

    for u in raw_urls:
        u = u.strip()
        if u in seen:
            continue
        if any(u.lower().endswith(e) for e in skip_exts):
            continue
        if any(pat in u for pat in _SKIP_URL_PATTERNS):
            continue
        seen.add(u)

        if any(pat in u for pat in _PRODUCT_URL_PATTERNS):
            products.append(u)
        else:
            others.append(u)

    ordered = products + others
    logger.info(f'[fetch_sitemap_urls] {len(products)} product URLs + {len(others)} other URLs')
    return ordered[:max_urls]


def fetch_pages_from_urls(urls, max_pages=150):
    """
    Scrape a list of URLs and return {title, content, url} dicts.
    Uses Playwright automatically for bot-protected pages.
    """
    documents = []
    for url in urls[:max_pages]:
        html, _ = _fetch_url(url, use_playwright_fallback=True)
        if not html:
            continue
        soup = BeautifulSoup(html, 'html.parser')
        title = soup.title.string.strip() if soup.title else url
        text = clean_html(html)
        if len(text) < 80:
            continue

        # Extract WooCommerce-specific structured data if present
        wc_data = _extract_woocommerce_product(soup, url)
        if wc_data:
            documents.append({**wc_data, 'url': url})
        else:
            documents.append({'title': title, 'content': f"Title: {title}\nURL: {url}\n\n{text}", 'url': url})

        time.sleep(0.2)

    logger.info(f'[fetch_pages_from_urls] Scraped {len(documents)} pages')
    return documents


def _extract_woocommerce_product(soup, url):
    """
    If the page is a WooCommerce product page, extract structured product data.
    Returns a {title, content, url} dict or None if not a product page.
    """
    # WooCommerce product pages have a specific body class
    body = soup.find('body')
    body_classes = body.get('class', []) if body else []
    if not any('single-product' in c or 'posttype-product' in c for c in body_classes):
        return None

    title_el = soup.find(class_='product_title') or soup.find('h1')
    title = title_el.get_text(strip=True) if title_el else ''
    if not title:
        return None

    # Price
    price_el = soup.find(class_='woocommerce-Price-amount')
    price = price_el.get_text(strip=True) if price_el else ''

    # Original price (if on sale)
    del_price = soup.find('del')
    original_price = del_price.get_text(strip=True) if del_price else ''

    # Short description
    short_desc_el = soup.find(class_='woocommerce-product-details__short-description')
    short_desc = short_desc_el.get_text(' ', strip=True) if short_desc_el else ''

    # Full description (tab)
    full_desc_el = soup.find(id='tab-description') or soup.find(class_='woocommerce-Tabs-panel--description')
    full_desc = full_desc_el.get_text(' ', strip=True) if full_desc_el else ''

    # SKU / categories
    sku_el = soup.find(class_='sku')
    sku = sku_el.get_text(strip=True) if sku_el else ''
    cat_els = soup.find_all(class_='posted_in')
    categories = ', '.join(c.get_text(strip=True).replace('Category:', '').strip() for c in cat_els)

    parts = [f"Product: {title}", f"URL: {url}"]
    if price:
        parts.append(f"Price: {price}")
    if original_price:
        parts.append(f"Original Price: {original_price}")
    if sku:
        parts.append(f"SKU: {sku}")
    if categories:
        parts.append(f"Categories: {categories}")
    if short_desc:
        parts.append(short_desc)
    if full_desc:
        parts.append(full_desc)

    return {'title': title, 'content': '\n'.join(parts)}


# ── Strategy 3: Generic HTML crawl ──────────────────────────────────────────

def fetch_generic_site(site_url, max_pages=100):
    """
    Breadth-first crawl with product URL prioritisation and bot-challenge detection.
    Product URLs (/product/, /shop/, etc.) are pushed to the front of the queue.
    """
    visited = set()
    # (priority, url) — lower priority = visited first; product URLs get priority 0
    queue = [(1, site_url.rstrip('/'))]
    documents = []
    base_domain = urlparse(site_url).netloc

    while queue and len(visited) < max_pages:
        queue.sort(key=lambda x: x[0])  # keep product URLs at front
        _, url = queue.pop(0)

        if url in visited:
            continue
        # Skip known low-value paths
        if any(pat in url for pat in _SKIP_URL_PATTERNS):
            continue
        visited.add(url)

        html, _ = _fetch_url(url, use_playwright_fallback=True)
        if not html:
            continue

        soup = BeautifulSoup(html, 'html.parser')
        title = soup.title.string.strip() if soup.title else url
        text = clean_html(html)

        if len(text) > 80:
            # Try WooCommerce structured extraction first
            wc_data = _extract_woocommerce_product(soup, url)
            if wc_data:
                documents.append({**wc_data, 'url': url})
            else:
                documents.append({
                    'title': title,
                    'content': f"Title: {title}\nURL: {url}\n\n{text}",
                    'url': url,
                })

        # Enqueue same-domain links, prioritising product URLs
        for a in soup.find_all('a', href=True):
            href = a['href']
            full = urljoin(url, href).split('#')[0].split('?')[0]
            if urlparse(full).netloc != base_domain:
                continue
            if full in visited:
                continue
            priority = 0 if any(pat in full for pat in _PRODUCT_URL_PATTERNS) else 1
            queue.append((priority, full))

    logger.info(f'[fetch_generic_site] Scraped {len(documents)} pages from {site_url}')
    return documents


def _fetch_with_playwright(url):
    """
    Use a headless Chromium browser to fetch a JS-rendered or bot-protected page.
    Waits for the network to become idle so dynamic content is fully loaded.
    Returns rendered HTML string, or None if Playwright is not available.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.warning('[_fetch_with_playwright] Playwright not installed — skipping')
        return None

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=_HEADERS['User-Agent'],
                viewport={'width': 1280, 'height': 800},
            )
            page = context.new_page()
            page.goto(url, wait_until='networkidle', timeout=25000)
            # Wait for common WooCommerce product containers
            try:
                page.wait_for_selector('.woocommerce-loop-product, .product_title, main', timeout=5000)
            except Exception:
                pass
            html = page.content()
            browser.close()
            return html
    except Exception as e:
        logger.warning(f'[_fetch_with_playwright] Failed for {url}: {e}')
        return None


# ── Strategy 4: Shopify JSON API ─────────────────────────────────────────────

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
                handle = p.get('handle', '')
                product_url = f"{site_url.rstrip('/')}/products/{handle}"
                content_parts = [f"Product: {title}", f"URL: {product_url}", body]
                if variants:
                    content_parts.append(f"Variants: {variants}")
                documents.append({
                    'title': title,
                    'content': '\n'.join(content_parts),
                    'url': product_url,
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

    Priority order:
      1. WordPress REST API  (posts + pages + WooCommerce product CPT)
      2. XML Sitemap discovery → scrape each URL
      3. Shopify /products.json
      4. Generic HTML crawl with product-URL prioritisation + bot-challenge detection
    """
    url = client.domain_url
    platform = (client.platform or '').upper()

    if platform == 'WORDPRESS':
        docs = fetch_wordpress_data(url)
        if docs:
            logger.info(f'[auto_scrape] WP REST API: {len(docs)} docs for {url}')
            # Also try sitemap to catch any product pages not in the REST API
            sitemap_urls = fetch_sitemap_urls(url)
            product_sitemap_urls = [
                u for u in sitemap_urls
                if any(pat in u for pat in _PRODUCT_URL_PATTERNS)
                and u not in {d['url'] for d in docs}
            ]
            if product_sitemap_urls:
                logger.info(f'[auto_scrape] Augmenting with {len(product_sitemap_urls)} product URLs from sitemap')
                extra = fetch_pages_from_urls(product_sitemap_urls, max_pages=200)
                docs.extend(extra)
            return docs

        # WP API returned nothing — try sitemap
        logger.info(f'[auto_scrape] WP REST API empty for {url}, trying sitemap')
        sitemap_urls = fetch_sitemap_urls(url)
        if sitemap_urls:
            logger.info(f'[auto_scrape] Sitemap found {len(sitemap_urls)} URLs for {url}')
            return fetch_pages_from_urls(sitemap_urls, max_pages=200)

        logger.info(f'[auto_scrape] Falling back to generic crawl for {url}')
        return fetch_generic_site(url)

    if platform == 'SHOPIFY':
        docs = fetch_shopify_data(url)
        if docs:
            return docs

    # CUSTOM or Shopify fallback — try sitemap first, then generic crawl
    sitemap_urls = fetch_sitemap_urls(url)
    if sitemap_urls:
        logger.info(f'[auto_scrape] Custom/fallback: sitemap with {len(sitemap_urls)} URLs for {url}')
        return fetch_pages_from_urls(sitemap_urls, max_pages=200)

    return fetch_generic_site(url)


# ── Shared ingestion pipeline ─────────────────────────────────────────────────

def ingest_documents(client, documents, progress_cb=None):
    """
    Takes a list of {title, content, url, product_id?} dicts,
    chunks, embeds, and stores DocumentChunk rows.
    Returns the number of chunks created.

    The URL is embedded directly in the chunk content text (not only as metadata)
    so the AI retrieval context always contains the exact link to cite.
    """
    if not documents:
        return 0

    chunks_text = []
    chunks_meta = []

    for doc in documents:
        title      = doc.get('title', '')
        text       = doc.get('content', '') or title
        source_url = doc.get('url', '')

        if not text or len(text.strip()) < 30:
            continue

        splits = _SPLITTER.split_text(text)
        for split in splits:
            # Always prefix with title AND URL so the AI sees the direct link
            # in the retrieved context, not just as external metadata.
            if 'URL:' in split:
                # Content already has URL embedded (WC product pages, WP API docs)
                prefixed = f"Title: {title}\n\n{split}" if title else split
            else:
                # Generic content — inject URL so the AI knows where it came from
                prefixed = (
                    f"Title: {title}\nURL: {source_url}\n\n{split}"
                    if title else f"URL: {source_url}\n\n{split}"
                )
            chunks_text.append(prefixed)
            chunks_meta.append({
                'source_url': source_url,
                'product_id': doc.get('product_id', ''),
                'title': title,
            })

    if not chunks_text:
        return 0

    total = len(chunks_text)
    if progress_cb:
        progress_cb(0, total)

    # Delete existing chunks for this client before re-ingesting
    DocumentChunk.objects.filter(client=client).delete()

    all_embeddings = []
    for i, chunk in enumerate(chunks_text):
        try:
            embs = batch_embed_texts([chunk])
            emb = embs[0] if embs else [0.0] * 1024
        except Exception as e:
            logger.warning(f'[ingest_documents] Embedding failed for chunk {i}: {e}')
            emb = [0.0] * 1024
        if len(emb) < 1024:
            emb = emb + [0.0] * (1024 - len(emb))
        elif len(emb) > 1024:
            emb = emb[:1024]
        all_embeddings.append(emb)
        if progress_cb and (i + 1) % 5 == 0:
            progress_cb(i + 1, total)
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
