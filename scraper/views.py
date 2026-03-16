import hashlib
import hmac
import logging

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from users.models import Client
from scraper.models import DocumentChunk

logger = logging.getLogger(__name__)


# ── Shared async re-embed helper ─────────────────────────────────────────────

def _queue_product_update(client, product_id, title, body_html, price, url):
    """
    Mark the client as syncing and enqueue a Celery task to do the actual
    re-embedding asynchronously so the webhook response is instant.
    """
    Client.objects.filter(pk=client.pk).update(
        ingestion_status='RUNNING',
        updated_at=timezone.now(),
    )
    from scraper.tasks import re_embed_product
    re_embed_product.delay(
        str(client.pk), str(product_id), title, body_html, str(price), url
    )


# ── Shopify ───────────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def shopify_webhook(request, client_id):
    """Receives Shopify products/update or products/create webhook."""
    client = get_object_or_404(Client, id=client_id)

    # Optional HMAC verification using webhook_secret
    secret = client.webhook_secret
    if secret:
        shopify_hmac = request.headers.get('X-Shopify-Hmac-Sha256', '')
        digest = hmac.new(
            secret.encode('utf-8'),
            request.body,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(digest, shopify_hmac):
            return Response({'status': 'unauthorized'}, status=401)

    data = request.data
    product_id = data.get('id')
    title = data.get('title', '')
    body_html = data.get('body_html', '')
    variants = data.get('variants', [])
    price = variants[0].get('price', '0') if variants else '0'
    handle = data.get('handle', '')
    url = f"{client.domain_url.rstrip('/')}/products/{handle}"

    if not (product_id and title):
        return Response({'status': 'skipped — missing id or title'}, status=400)

    _queue_product_update(client, product_id, title, body_html, price, url)
    return Response({'status': 'queued'}, status=202)


# ── WooCommerce ───────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def woocommerce_webhook(request, client_id):
    """Receives WooCommerce product.updated webhook."""
    client = get_object_or_404(Client, id=client_id)

    data = request.data
    product_id = data.get('id')
    title = data.get('name', '')
    body_html = data.get('description', '') or data.get('short_description', '')
    price = data.get('price', '0')
    url = data.get('permalink', client.domain_url)

    if not (product_id and title):
        return Response({'status': 'skipped — missing id or name'}, status=400)

    _queue_product_update(client, product_id, title, body_html, price, url)
    return Response({'status': 'queued'}, status=202)


# ── WordPress ─────────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def wordpress_webhook(request, client_id):
    """Receives WordPress post create/update webhook."""
    client = get_object_or_404(Client, id=client_id)

    data = request.data
    # Some WP webhook plugins wrap the payload in {"post": {...}}
    post_data = data.get('post', data)

    post_id = post_data.get('id')
    if not post_id:
        return Response({'status': 'error', 'message': 'No post ID in payload'}, status=400)

    title = (post_data.get('title') or {}).get('rendered', '') or post_data.get('post_title', '')
    content_html = (post_data.get('content') or {}).get('rendered', '') or post_data.get('post_content', '')
    link = post_data.get('link', '') or post_data.get('guid', '')

    if not title:
        return Response({'status': 'skipped — no title'}, status=400)

    Client.objects.filter(pk=client.pk).update(
        ingestion_status='RUNNING',
        updated_at=timezone.now(),
    )
    from scraper.tasks import re_embed_wordpress_post
    re_embed_wordpress_post.delay(str(client.pk), str(post_id), title, content_html, link)
    return Response({'status': 'queued'}, status=202)
