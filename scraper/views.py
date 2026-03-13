import requests
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from users.models import Client
from scraper.models import DocumentChunk
from scraper.embeddings import batch_embed_texts
from scraper.ingestion import process_single_wordpress_post


BROWSER_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/124.0.0.0 Safari/537.36'
    )
}


# ─────────────────────────────────────────────────────────────────────────────
# CORE: Regenerate embedding for a single product (Shopify / WooCommerce)
# ─────────────────────────────────────────────────────────────────────────────

def regenerate_product_embedding(client, product_id, title, description, price, url):
    """
    Atomically replaces the embedding for a single product in the vector DB.
    Used by Shopify and WooCommerce webhook handlers.
    """
    from bs4 import BeautifulSoup
    clean_desc = BeautifulSoup(description or '', 'html.parser').get_text(separator=' ', strip=True)
    content = f"Product: {title}\nPrice: ${price}\nDescription: {clean_desc}"
    source_url_marker = url or f"product_{product_id}"

    # Atomic swap: delete stale → embed → insert fresh
    DocumentChunk.objects.filter(client=client, product_id=str(product_id)).delete()

    embeddings = batch_embed_texts([content])
    if embeddings:
        DocumentChunk.objects.create(
            client=client,
            content=content,
            embedding=embeddings[0],
            source_url=source_url_marker,
            product_id=str(product_id),
            metadata={'title': title, 'type': 'product'},
        )
        return True
    return False


# ─────────────────────────────────────────────────────────────────────────────
# SHOPIFY WEBHOOK  — products/create  &  products/update
# ─────────────────────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def shopify_webhook(request, client_id):
    """Receives Shopify product webhooks and updates the vector DB."""
    client = get_object_or_404(Client, id=client_id)
    # TODO (production): verify Shopify HMAC header

    data = request.data
    product_id  = data.get('id')
    title       = data.get('title', '')
    description = data.get('body_html', '')

    price = 0.0
    variants = data.get('variants', [])
    if variants:
        price = variants[0].get('price', 0.0)

    url = f"https://{client.domain_url}/products/{data.get('handle', '')}"

    if product_id and title:
        regenerate_product_embedding(client, product_id, title, description, price, url)
        return Response({"status": "synced"}, status=200)

    return Response({"status": "skipped", "reason": "missing id or title"}, status=400)


# ─────────────────────────────────────────────────────────────────────────────
# WOOCOMMERCE WEBHOOK  — product.updated  &  product.created
# ─────────────────────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def woocommerce_webhook(request, client_id):
    """Receives WooCommerce product webhooks and updates the vector DB."""
    client = get_object_or_404(Client, id=client_id)
    # TODO (production): verify WooCommerce secret header

    data = request.data
    product_id  = data.get('id')
    title       = data.get('name', '')
    description = data.get('description', '')
    price       = data.get('price', 0.0)
    url         = data.get('permalink', '')

    if product_id and title:
        regenerate_product_embedding(client, product_id, title, description, price, url)
        return Response({"status": "synced"}, status=200)

    return Response({"status": "skipped", "reason": "missing id or name"}, status=400)


# ─────────────────────────────────────────────────────────────────────────────
# WORDPRESS WEBHOOK  — post created / updated
#
# Handles three common payload formats:
#   Format A (WP REST API-style):
#       { "id": 123, "title": {"rendered": "..."}, "content": {"rendered": "..."}, "link": "..." }
#   Format B (WP Webhooks plugin — flat keys):
#       { "ID": 123, "post_title": "...", "post_content": "...", "guid": "url" }
#   Format C (bare post_id only — we fetch fresh from WP REST API):
#       { "post_id": 123 }
# ─────────────────────────────────────────────────────────────────────────────

def _normalize_wp_payload(raw_data, client_domain):
    """
    Normalise any WP webhook payload into the WP REST API dict format that
    process_single_wordpress_post() expects.
    Returns None if the payload cannot be parsed.
    """
    # ── Format A: WP REST API style (nested title/content dicts) ──
    if 'id' in raw_data and isinstance(raw_data.get('title'), dict):
        return raw_data

    # ── Resolve post_id from any common key ──
    post_id = (
        raw_data.get('ID')
        or raw_data.get('post_ID')
        or raw_data.get('post_id')
        or raw_data.get('id')
    )

    if not post_id:
        return None

    # ── Format B: Flat WP Webhooks-style with inline content ──
    if raw_data.get('post_title') or raw_data.get('post_content'):
        link = (
            raw_data.get('guid', '')
            or raw_data.get('post_permalink', '')
            or f"https://{client_domain}/?p={post_id}"
        )
        return {
            'id':      int(post_id),
            'title':   {'rendered': raw_data.get('post_title', '')},
            'content': {'rendered': raw_data.get('post_content', '')},
            'excerpt': {'rendered': raw_data.get('post_excerpt', '')},
            'link':    link,
        }

    # ── Format C: Only a post_id — fetch fresh from WP REST API ──
    return _fetch_post_from_wp_api(client_domain, int(post_id))


def _fetch_post_from_wp_api(domain, post_id):
    """Fetch a single post/page by ID directly from the WP REST API."""
    if not domain:
        return None
    base = f"https://{domain.rstrip('/')}"
    for endpoint in (f"{base}/wp-json/wp/v2/posts/{post_id}",
                     f"{base}/wp-json/wp/v2/pages/{post_id}"):
        try:
            resp = requests.get(endpoint, headers=BROWSER_HEADERS, timeout=10)
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            print(f"[Webhook] Error fetching {endpoint}: {e}")
    return None


@api_view(['POST'])
@permission_classes([AllowAny])
def wordpress_webhook(request, client_id):
    """
    Receives WordPress post-create/update webhooks and re-ingests the post.
    Compatible with WP Webhooks plugin, WP REST API hooks, and custom plugins.
    """
    client = get_object_or_404(Client, id=client_id)
    raw_data = request.data

    # Unwrap nested 'post' key if present (some plugins wrap the payload)
    if 'post' in raw_data and isinstance(raw_data.get('post'), dict):
        raw_data = raw_data['post']

    client_domain = (
        (client.domain_url or '')
        .replace('https://', '')
        .replace('http://', '')
        .rstrip('/')
    )

    post_data = _normalize_wp_payload(raw_data, client_domain)

    if not post_data:
        return Response(
            {
                "status": "error",
                "message": (
                    "Unrecognised payload format. "
                    "Expected one of: WP REST API, WP Webhooks plugin, or a bare post_id."
                )
            },
            status=400
        )

    result = process_single_wordpress_post(client, post_data)

    status_code = 200 if result.get('status') in ('success', 'ignored') else 400
    return Response(result, status=status_code)
