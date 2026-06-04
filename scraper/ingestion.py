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


def fetch_sitemap_with_lastmod(site_url, max_urls=1000):
    """
    Like fetch_sitemap_urls() but preserves the <lastmod> for each entry.
    Returns [(url, lastmod_iso_string_or_None), ...].

    Used by the periodic sitemap watcher (scraper.tasks.watch_sitemaps_for_changes)
    to detect which individual pages changed since their last embed without
    triggering a full re-crawl. Skips binary/admin URLs the same way as the
    plain helper, but does NOT prioritise products — we want every page.
    """
    base = site_url.rstrip('/')
    sitemap_candidates = [
        f'{base}/wp-sitemap.xml',
        f'{base}/sitemap_index.xml',
        f'{base}/sitemap.xml',
        f'{base}/product-sitemap.xml',
        f'{base}/post-sitemap.xml',
    ]

    entries = []  # list of (url, lastmod)

    def _parse_urlset(root):
        """Yield (url, lastmod) from a <urlset>."""
        for url_el in root.findall(f'{{{_SITEMAP_NS}}}url'):
            loc = url_el.find(f'{{{_SITEMAP_NS}}}loc')
            if loc is None or not loc.text:
                continue
            lm_el = url_el.find(f'{{{_SITEMAP_NS}}}lastmod')
            lastmod = lm_el.text.strip() if lm_el is not None and lm_el.text else None
            yield loc.text.strip(), lastmod

    for sm_url in sitemap_candidates:
        try:
            resp = requests.get(sm_url, headers=_HEADERS, timeout=10)
            if resp.status_code != 200 or not resp.text.strip().startswith('<'):
                continue
            root = ET.fromstring(resp.text)

            # Sitemap index → recurse into each sub-sitemap
            sub_locs = root.findall(f'{{{_SITEMAP_NS}}}sitemap/{{{_SITEMAP_NS}}}loc')
            if sub_locs:
                for loc in sub_locs:
                    try:
                        sr = requests.get(loc.text.strip(), headers=_HEADERS, timeout=10)
                        if sr.status_code == 200 and sr.text.strip().startswith('<'):
                            sr_root = ET.fromstring(sr.text)
                            entries.extend(_parse_urlset(sr_root))
                    except Exception:
                        pass
            else:
                entries.extend(_parse_urlset(root))

            if entries:
                logger.info(f'[fetch_sitemap_with_lastmod] {len(entries)} entries from {sm_url}')
                break
        except Exception as e:
            logger.debug(f'[fetch_sitemap_with_lastmod] {sm_url}: {e}')

    # Dedupe + skip binary/admin URLs (preserve order)
    skip_exts = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg',
                 '.pdf', '.zip', '.css', '.js', '.xml', '.ico')
    seen = set()
    cleaned = []
    for url, lastmod in entries:
        if url in seen:
            continue
        if any(url.lower().endswith(e) for e in skip_exts):
            continue
        if any(pat in url for pat in _SKIP_URL_PATTERNS):
            continue
        seen.add(url)
        cleaned.append((url, lastmod))

    return cleaned[:max_urls]


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
#
# Public, no-auth Shopify endpoints. Each helper returns a flat list of
# document dicts in the same shape the embedder expects:
#   {title, content, url, product_id (optional), metadata: {type, ...}}
#
# `metadata.type` is one of {product, page, article, collection} so RAG
# retrieval and the activity feed can route by resource type.
# `metadata.shopify_resource` is a stable key
# (e.g. `product_<id>`, `page_<id>`, `article_<id>`, `collection_<id>`)
# used by the inventory + delete webhooks to find/update the right chunk
# without having to re-scan the whole catalog.

def _shopify_paginate(api_url, key, site_url, max_pages=40, limit=250):
    """
    Walk a paginated Shopify JSON endpoint until empty / 4xx / max_pages.

    Returns the concatenated list under `key`. Wrapped in try/except so a
    transient blip doesn't abort the whole sync — `fetch_shopify_data`
    keeps the partial results from earlier endpoints.
    """
    out = []
    for page in range(1, max_pages + 1):
        try:
            resp = requests.get(
                api_url,
                params={'limit': limit, 'page': page},
                headers=_HEADERS,
                timeout=15,
            )
            if resp.status_code != 200:
                break
            items = (resp.json() or {}).get(key, []) or []
            if not items:
                break
            out.extend(items)
            if len(items) < limit:
                break  # last page
        except Exception as e:
            logger.warning(f'[_shopify_paginate] {api_url} page={page}: {e}')
            break
    return out


def _shopify_products(site_url):
    """Fetch all products. Captures variants[].inventory_item_id so the
    Phase-C inventory webhook can find affected chunks."""
    base = site_url.rstrip('/')
    products = _shopify_paginate(f'{base}/products.json', 'products', site_url)
    docs = []
    for p in products:
        title = p.get('title') or ''
        body = BeautifulSoup(p.get('body_html', '') or '', 'html.parser').get_text(' ', True)
        handle = p.get('handle') or ''
        url = f'{base}/products/{handle}'
        variant_rows = p.get('variants', []) or []
        # Human-readable variant blurb for the AI to read out
        variants_blurb = ', '.join(
            f"{v.get('title', '?')} ${v.get('price')}"
            for v in variant_rows if v.get('price')
        )
        # Structured variant list for inventory bookkeeping. Each entry
        # carries the inventory_item_id that Shopify's
        # `inventory_levels/update` webhook references.
        variants_struct = [
            {
                'variant_id': v.get('id'),
                'inventory_item_id': v.get('inventory_item_id'),
                'sku': v.get('sku') or '',
                'price': v.get('price') or '',
                'available': v.get('available'),
            }
            for v in variant_rows
        ]
        content_parts = [f'Product: {title}', f'URL: {url}', body]
        if variants_blurb:
            content_parts.append(f'Variants: {variants_blurb}')
        docs.append({
            'title': title,
            'content': '\n'.join(content_parts),
            'url': url,
            'product_id': str(p.get('id', '')),
            'metadata': {
                'title': title,
                'type': 'product',
                'shopify_resource': f"product_{p.get('id', '')}",
                'variants': variants_struct,
                'is_active': True,
            },
        })
    return docs


def _shopify_pages(site_url):
    """Static pages: About, Shipping, FAQ, Returns, Privacy, T&C, etc."""
    base = site_url.rstrip('/')
    pages = _shopify_paginate(f'{base}/pages.json', 'pages', site_url)
    docs = []
    for p in pages:
        title = p.get('title') or ''
        body = BeautifulSoup(p.get('body_html', '') or '', 'html.parser').get_text(' ', True)
        handle = p.get('handle') or ''
        url = f'{base}/pages/{handle}'
        docs.append({
            'title': title,
            'content': f'Page: {title}\nURL: {url}\n{body}',
            'url': url,
            'metadata': {
                'title': title,
                'type': 'page',
                'shopify_resource': f"page_{p.get('id', '')}",
            },
        })
    return docs


def _shopify_blogs_and_articles(site_url, max_blogs=20):
    """Blog articles (capped at `max_blogs` blogs per tenant to avoid
    pathological multi-blog stores)."""
    base = site_url.rstrip('/')
    blogs = _shopify_paginate(f'{base}/blogs.json', 'blogs', site_url)
    if len(blogs) > max_blogs:
        logger.warning(
            f'[_shopify_blogs_and_articles] {site_url} has {len(blogs)} blogs; '
            f'capping at {max_blogs}'
        )
        blogs = blogs[:max_blogs]
    docs = []
    for blog in blogs:
        blog_handle = blog.get('handle') or ''
        articles = _shopify_paginate(
            f'{base}/blogs/{blog_handle}/articles.json',
            'articles',
            site_url,
        )
        for a in articles:
            title = a.get('title') or ''
            body = BeautifulSoup(a.get('body_html', '') or '', 'html.parser').get_text(' ', True)
            handle = a.get('handle') or ''
            url = f'{base}/blogs/{blog_handle}/{handle}'
            docs.append({
                'title': title,
                'content': f'Article: {title}\nURL: {url}\n{body}',
                'url': url,
                'metadata': {
                    'title': title,
                    'type': 'article',
                    'shopify_resource': f"article_{a.get('id', '')}",
                    'blog_handle': blog_handle,
                },
            })
    return docs


def _shopify_collections(site_url):
    """Product collections. Shopify exposes `/collections.json` (custom
    collections) and `/smart_collections` style endpoints; the public
    `/collections.json` returns both kinds for most stores."""
    base = site_url.rstrip('/')
    collections = _shopify_paginate(f'{base}/collections.json', 'collections', site_url)
    docs = []
    for c in collections:
        title = c.get('title') or ''
        body = BeautifulSoup(c.get('body_html', '') or '', 'html.parser').get_text(' ', True)
        handle = c.get('handle') or ''
        url = f'{base}/collections/{handle}'
        content = f'Collection: {title}\nURL: {url}\n{body}'.strip()
        docs.append({
            'title': title,
            'content': content,
            'url': url,
            'metadata': {
                'title': title,
                'type': 'collection',
                'shopify_resource': f"collection_{c.get('id', '')}",
            },
        })
    return docs


def fetch_shopify_data(site_url):
    """
    Fetch the full public Shopify catalog: products, pages, blog articles,
    and collections. All endpoints are unauthenticated. Returns a flat
    list of document dicts ready for embedding.

    Individual sub-fetches swallow their own errors so a single failing
    endpoint (e.g. a tenant with `/pages.json` disabled by their theme)
    doesn't drop the rest of the catalog.
    """
    documents = []
    documents.extend(_shopify_products(site_url))
    documents.extend(_shopify_pages(site_url))
    documents.extend(_shopify_blogs_and_articles(site_url))
    documents.extend(_shopify_collections(site_url))

    # Tally per-type for the log line so we can spot e.g. "products fetched
    # but pages always 0" patterns in production logs.
    by_type = {}
    for d in documents:
        t = (d.get('metadata') or {}).get('type', 'unknown')
        by_type[t] = by_type.get(t, 0) + 1
    logger.info(
        f'[fetch_shopify_data] Fetched {len(documents)} docs from {site_url} '
        f'(breakdown: {by_type})'
    )
    return documents


# ── Strategy 4b: WooCommerce Store API ───────────────────────────────────────
#
# WordPress + WooCommerce sites expose a PUBLIC, no-auth product feed at
# /wp-json/wc/store/v1/products that includes real prices, currency, sale
# state, and stock — exactly the data the WP REST API (`/wp-json/wp/v2/product`)
# omits. The WP REST product CPT only carries the lorem-ipsum description,
# which is why the bot couldn't answer "how much is the cap?" — the price
# was never in the embedded chunk. This fetcher fills that gap.
#
# Price arithmetic: WooCommerce returns integer minor units + a
# `currency_minor_unit` (e.g. price="1600", minor_unit=2 → 16.00) plus the
# currency symbol and prefix/suffix placement. `_format_wc_price` renders a
# human string the AI can read out verbatim ("රු16.00").

def _format_wc_price(prices: dict) -> str:
    """
    Render a WooCommerce Store-API `prices` object into a readable line.
    Returns '' when there's no usable price (e.g. external/grouped products
    with a null price_range and empty price).
    """
    if not isinstance(prices, dict):
        return ''

    minor = prices.get('currency_minor_unit')
    try:
        minor = int(minor)
    except (TypeError, ValueError):
        minor = 2
    symbol = (prices.get('currency_symbol') or '').strip()
    prefix = prices.get('currency_prefix') or ''
    suffix = prices.get('currency_suffix') or ''

    def _money(raw):
        """Convert integer-minor-unit string → display string with symbol."""
        if raw in (None, '', 'null'):
            return ''
        try:
            value = int(raw) / (10 ** minor)
        except (TypeError, ValueError):
            return ''
        amount = f'{value:,.{minor}f}'
        # Prefer explicit prefix/suffix; fall back to a leading symbol.
        if prefix or suffix:
            return f'{prefix}{amount}{suffix}'.strip()
        if symbol:
            return f'{symbol}{amount}'
        return amount

    price = _money(prices.get('price'))
    regular = _money(prices.get('regular_price'))
    sale = _money(prices.get('sale_price'))

    # Price range (variable products) — Woo returns {min_amount, max_amount}.
    price_range = prices.get('price_range')
    if isinstance(price_range, dict) and price_range.get('min_amount'):
        lo = _money(price_range.get('min_amount'))
        hi = _money(price_range.get('max_amount'))
        if lo and hi and lo != hi:
            return f'{lo} – {hi}'
        if lo:
            return lo

    if not price:
        return ''

    # On sale → show current + struck regular for context.
    on_sale = bool(sale and regular and sale != regular)
    if on_sale:
        return f'{price} (on sale, was {regular})'
    return price


def fetch_woocommerce_data(site_url, timeout=15):
    """
    Fetch all products from the public WooCommerce Store API
    (/wp-json/wc/store/v1/products), with prices. Returns a flat list of
    document dicts in the standard shape used by ingest_documents.

    Returns [] (not None) when the endpoint is absent / disabled, so the
    caller can cleanly fall back to the WP REST + crawl path.
    """
    base = site_url.rstrip('/')
    api = f'{base}/wp-json/wc/store/v1/products'
    documents = []
    page = 1
    while page <= 40:  # 40 * 100 = 4000 products hard cap
        try:
            resp = requests.get(
                api,
                params={'per_page': 100, 'page': page},
                headers=_HEADERS,
                timeout=timeout,
            )
            if resp.status_code != 200:
                break
            products = resp.json()
            if not isinstance(products, list) or not products:
                break
        except Exception as e:
            logger.warning(f'[fetch_woocommerce_data] {api} page={page}: {e}')
            break

        for p in products:
            title = (p.get('name') or '').strip()
            if not title:
                continue
            url = p.get('permalink') or f'{base}/?p={p.get("id", "")}'
            short = BeautifulSoup(p.get('short_description', '') or '', 'html.parser').get_text(' ', True)
            full = BeautifulSoup(p.get('description', '') or '', 'html.parser').get_text(' ', True)
            sku = (p.get('sku') or '').strip()
            prices = p.get('prices') or {}
            price_line = _format_wc_price(prices)
            categories = ', '.join(
                c.get('name', '') for c in (p.get('categories') or []) if c.get('name')
            )
            in_stock = (p.get('is_in_stock') is not False)

            parts = [f'Product: {title}', f'URL: {url}']
            if price_line:
                parts.append(f'Price: {price_line}')
            if sku:
                parts.append(f'SKU: {sku}')
            if categories:
                parts.append(f'Categories: {categories}')
            if not in_stock:
                parts.append('Stock: OUT OF STOCK')
            if short:
                parts.append(short)
            elif full:
                parts.append(full)

            documents.append({
                'title': title,
                'content': '\n'.join(parts),
                'url': url,
                'product_id': str(p.get('id', '')),
                'metadata': {
                    'title': title,
                    'type': 'product',
                    'woo_resource': f"product_{p.get('id', '')}",
                    'price_display': price_line,
                    'currency': (prices.get('currency_code') or '') if isinstance(prices, dict) else '',
                    'is_active': bool(in_stock),
                },
            })

        if len(products) < 100:
            break
        page += 1

    logger.info(f'[fetch_woocommerce_data] Fetched {len(documents)} products from {site_url}')
    return documents


# ── Platform auto-detection (Phase D) ────────────────────────────────────────

def detect_platform(site_url: str, timeout: int = 6) -> str:
    """
    Inspect a public site URL and return the most likely Client.platform value.

    Returns one of: 'SHOPIFY', 'WORDPRESS', 'CUSTOM'.

    Detection ladder (fast → slow):
      1. `*.myshopify.com` host → Shopify (no network call needed).
      2. `/products.json` returns JSON with a `products` key → Shopify.
      3. Homepage HTML contains `window.Shopify`, `cdn.shopify.com`, or a
         `Shopify-` cookie hint → Shopify.
      4. `/wp-json/` returns 200 with a `namespaces` field → WordPress.
      5. Homepage HTML contains `wp-content/`, `wp-includes/`, or a
         `generator` meta tag mentioning WordPress → WordPress.
      6. Otherwise → CUSTOM (caller can keep manual choice).

    Conservative on purpose — false positives are worse than false negatives
    because a misidentified platform routes the catalog through the wrong
    scraper. When uncertain we return CUSTOM and let the merchant choose.
    """
    if not site_url:
        return 'CUSTOM'

    # 1. Cheap shortcut: domain pattern. `*.myshopify.com` is always Shopify.
    try:
        from urllib.parse import urlparse
        host = (urlparse(site_url).hostname or '').lower()
    except Exception:
        host = ''
    if host.endswith('.myshopify.com'):
        return 'SHOPIFY'

    # 2. /products.json — Shopify's tell-tale public endpoint.
    base = site_url.rstrip('/')
    try:
        r = requests.get(
            f'{base}/products.json',
            params={'limit': 1},
            headers=_HEADERS,
            timeout=timeout,
        )
        if r.status_code == 200:
            try:
                if 'products' in (r.json() or {}):
                    return 'SHOPIFY'
            except ValueError:
                pass
    except Exception:
        pass

    # 4. /wp-json/ — WordPress REST API root.
    try:
        r = requests.get(f'{base}/wp-json/', headers=_HEADERS, timeout=timeout)
        if r.status_code == 200:
            try:
                if 'namespaces' in (r.json() or {}):
                    return 'WORDPRESS'
            except ValueError:
                pass
    except Exception:
        pass

    # 3+5. Last-ditch homepage sniff for embedded markers.
    try:
        r = requests.get(base, headers=_HEADERS, timeout=timeout)
        if r.status_code == 200:
            body = (r.text or '')[:200_000].lower()  # cap to avoid huge SPA bundles
            if 'cdn.shopify.com' in body or 'window.shopify' in body or 'shopify.theme' in body:
                return 'SHOPIFY'
            if 'wp-content/' in body or 'wp-includes/' in body or '<meta name="generator" content="wordpress' in body:
                return 'WORDPRESS'
    except Exception:
        pass

    return 'CUSTOM'


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

            # ── WooCommerce price enrichment ─────────────────────────────
            # The WP REST product CPT omits prices (price is WC meta, not
            # post content), so the embedded chunk for a product has the
            # description but no price — the bot can't answer "how much is
            # X?". The public WooCommerce Store API DOES carry prices, so
            # we fetch it and let the price-rich version REPLACE the bare
            # WP-REST version for the same product URL.
            woo_docs = fetch_woocommerce_data(url)
            if woo_docs:
                woo_urls = {d['url'] for d in woo_docs}
                # Drop WP-REST docs that WooCommerce now covers with price.
                docs = [d for d in docs if d['url'] not in woo_urls]
                docs.extend(woo_docs)
                logger.info(
                    f'[auto_scrape] WooCommerce Store API enriched '
                    f'{len(woo_docs)} products with prices for {url}'
                )

            # Also try sitemap to catch any product pages not in the REST API
            sitemap_urls = fetch_sitemap_urls(url)
            covered = {d['url'] for d in docs}
            product_sitemap_urls = [
                u for u in sitemap_urls
                if any(pat in u for pat in _PRODUCT_URL_PATTERNS)
                and u not in covered
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
        # `metadata` on the input doc is optional — Shopify ingestion sets
        # `{type, shopify_resource, variants, is_active}` so the inventory
        # webhook + RAG retrieval can route by resource type. Older
        # producers (WordPress, generic crawl) leave it empty and just get
        # the `{title}` default.
        doc_meta = dict(doc.get('metadata') or {})

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
                'doc_meta': doc_meta,
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
            # Merge the doc-level metadata (Shopify type, variants, etc.)
            # with the canonical {title} so downstream code always sees
            # title where it expects it.
            metadata={'title': chunks_meta[i]['title'], **(chunks_meta[i].get('doc_meta') or {})},
        )
        for i in range(len(chunks_text))
    ]
    DocumentChunk.objects.bulk_create(docs_to_create, batch_size=100)
    logger.info(f'[ingest_documents] Created {len(docs_to_create)} chunks for client {client.pk}')
    return len(docs_to_create)
