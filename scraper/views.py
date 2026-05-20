import hashlib
import hmac
import logging

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from users.models import Client
from scraper.models import DocumentChunk, WebhookEvent

logger = logging.getLogger(__name__)


def _log_event(client, source, event_type, resource_id, resource_title):
    """
    Create a WebhookEvent audit row in `queued` state. The Celery task that
    actually does the re-embedding updates this row to done / failed via
    _mark_event_status (called from scraper/tasks.py).
    """
    return WebhookEvent.objects.create(
        client=client,
        source=source,
        event_type=event_type[:60],
        resource_id=str(resource_id)[:64] if resource_id else '',
        resource_title=(resource_title or '')[:300],
        status='queued',
    )


# ── Shared async re-embed helper ─────────────────────────────────────────────

def _queue_product_update(client, product_id, title, body_html, price, url, event_id=None):
    """
    Mark the client as syncing and enqueue a Celery task to do the actual
    re-embedding asynchronously so the webhook response is instant.

    event_id lets the task close the loop on the WebhookEvent audit row.
    """
    Client.objects.filter(pk=client.pk).update(
        ingestion_status='RUNNING',
        updated_at=timezone.now(),
    )
    from scraper.tasks import re_embed_product
    re_embed_product.delay(
        str(client.pk), str(product_id), title, body_html, str(price), url,
        event_id,
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

    event = _log_event(client, 'shopify', 'product.update', product_id, title)
    _queue_product_update(client, product_id, title, body_html, price, url, event.id)
    return Response({'status': 'queued', 'event_id': event.id}, status=202)


# ── WooCommerce ───────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def woocommerce_webhook(request, client_id):
    """Receives WooCommerce product.updated webhook."""
    client = get_object_or_404(Client, id=client_id)

    # HMAC-SHA256 verification (WooCommerce sends X-WC-Webhook-Signature)
    secret = client.webhook_secret
    if secret:
        wc_sig = request.headers.get('X-WC-Webhook-Signature', '')
        digest = hmac.new(
            secret.encode('utf-8'),
            request.body,
            hashlib.sha256,
        ).digest()
        import base64
        expected = base64.b64encode(digest).decode()
        if not hmac.compare_digest(expected, wc_sig):
            return Response({'status': 'unauthorized'}, status=401)

    data = request.data
    product_id = data.get('id')
    title = data.get('name', '')
    body_html = data.get('description', '') or data.get('short_description', '')
    price = data.get('price', '0')
    permalink = data.get('permalink', '')
    slug = data.get('slug', '')
    url = permalink or (f"{client.domain_url.rstrip('/')}/product/{slug}" if slug else '')
    if not url:
        return Response({'status': 'skipped — no permalink or slug'}, status=400)

    if not (product_id and title):
        return Response({'status': 'skipped — missing id or name'}, status=400)

    event = _log_event(client, 'woocommerce', 'product.updated', product_id, title)
    _queue_product_update(client, product_id, title, body_html, price, url, event.id)
    return Response({'status': 'queued', 'event_id': event.id}, status=202)


# ── WordPress ─────────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def wordpress_webhook(request, client_id):
    """Receives WordPress post create/update webhook."""
    client = get_object_or_404(Client, id=client_id)

    # HMAC-SHA256 verification (header: X-WP-Webhook-Signature or X-Hub-Signature-256)
    secret = client.webhook_secret
    if secret:
        sig_header = (
            request.headers.get('X-WP-Webhook-Signature') or
            request.headers.get('X-Hub-Signature-256', '')
        )
        digest = 'sha256=' + hmac.new(
            secret.encode('utf-8'),
            request.body,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(digest, sig_header):
            return Response({'status': 'unauthorized'}, status=401)

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
    event = _log_event(client, 'wordpress', 'post.save', post_id, title)
    from scraper.tasks import re_embed_wordpress_post
    re_embed_wordpress_post.delay(
        str(client.pk), str(post_id), title, content_html, link, event.id,
    )
    return Response({'status': 'queued', 'event_id': event.id}, status=202)
