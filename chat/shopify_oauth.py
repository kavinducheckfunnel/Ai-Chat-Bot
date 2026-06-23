"""
Shopify OAuth (public app) — one app, installed by many merchant stores.

Flow:
  1. Tenant (authenticated) calls GET /api/shopify/authorize-url?client_id=<uuid>&shop=<store>.myshopify.com
     → we return the Shopify authorize URL (with a signed `state` that binds the
       install to this tenant's Client). The SPA then redirects the browser there.
  2. Merchant approves on Shopify → Shopify redirects to
     GET /api/shopify/oauth/callback?code=...&shop=...&state=...&hmac=...
     → we verify the request HMAC + state, exchange `code` for a permanent offline
       access token, and save it on the Client.

Also exposes the 3 GDPR mandatory webhook endpoints Shopify requires for review.
"""
import hashlib
import hmac
import re
import logging

import requests as http_requests
from django.conf import settings
from django.core import signing
from django.http import HttpResponseRedirect, HttpResponse
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from users.models import Client
from users.permissions import get_accessible_clients

logger = logging.getLogger(__name__)

_SHOP_RE = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9\-]*\.myshopify\.com$')
_STATE_SALT = 'shopify-oauth-install'


def _normalize_shop(shop: str) -> str:
    """Coerce input to a canonical <store>.myshopify.com, or '' if invalid."""
    if not shop:
        return ''
    shop = shop.strip().lower().replace('https://', '').replace('http://', '').rstrip('/')
    if '.myshopify.com' not in shop:
        shop = f'{shop}.myshopify.com'
    return shop if _SHOP_RE.match(shop) else ''


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def shopify_authorize_url(request):
    """Return the Shopify OAuth authorize URL for a tenant's Client + shop."""
    if not settings.SHOPIFY_APP_CLIENT_ID:
        return Response({'detail': 'Shopify app not configured on the server.'}, status=503)

    client_id = request.query_params.get('client_id', '')
    shop = _normalize_shop(request.query_params.get('shop', ''))
    if not shop:
        return Response({'detail': 'Enter a valid myshopify.com store domain.'}, status=400)

    # The Client must belong to the requesting tenant.
    try:
        client = get_accessible_clients(request.user).get(pk=client_id)
    except (Client.DoesNotExist, ValueError):
        return Response({'detail': 'Not found.'}, status=404)

    state = signing.dumps({'client_id': str(client.id), 'shop': shop}, salt=_STATE_SALT)
    redirect_uri = f'{settings.BACKEND_PUBLIC_URL.rstrip("/")}/api/shopify/oauth/callback'
    url = (
        f'https://{shop}/admin/oauth/authorize'
        f'?client_id={settings.SHOPIFY_APP_CLIENT_ID}'
        f'&scope={settings.SHOPIFY_APP_SCOPES}'
        f'&redirect_uri={redirect_uri}'
        f'&state={state}'
    )
    return Response({'url': url})


def _verify_callback_hmac(query: dict) -> bool:
    """Verify the OAuth callback HMAC (sorted query string, app secret)."""
    secret = settings.SHOPIFY_APP_CLIENT_SECRET
    received = query.get('hmac', '')
    if not secret or not received:
        return False
    pairs = sorted(f'{k}={v}' for k, v in query.items() if k != 'hmac')
    msg = '&'.join(pairs).encode('utf-8')
    digest = hmac.new(secret.encode('utf-8'), msg, hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, received)


@api_view(['GET'])
@permission_classes([AllowAny])
def shopify_oauth_callback(request):
    """Shopify redirects here after the merchant approves. Exchange code → token."""
    portal = f'{settings.BACKEND_PUBLIC_URL.rstrip("/")}/portal/integrations'
    q = {k: v for k, v in request.query_params.items()}
    shop = _normalize_shop(q.get('shop', ''))
    code = q.get('code', '')
    state = q.get('state', '')

    if not shop or not code or not _verify_callback_hmac(q):
        return HttpResponseRedirect(f'{portal}?shopify=error')

    try:
        data = signing.loads(state, salt=_STATE_SALT, max_age=3600)
    except signing.BadSignature:
        return HttpResponseRedirect(f'{portal}?shopify=error')
    if data.get('shop') != shop:
        return HttpResponseRedirect(f'{portal}?shopify=error')

    try:
        client = Client.objects.get(pk=data.get('client_id'))
    except (Client.DoesNotExist, ValueError):
        return HttpResponseRedirect(f'{portal}?shopify=error')

    # Exchange the authorization code for a permanent offline access token.
    try:
        resp = http_requests.post(
            f'https://{shop}/admin/oauth/access_token',
            json={
                'client_id': settings.SHOPIFY_APP_CLIENT_ID,
                'client_secret': settings.SHOPIFY_APP_CLIENT_SECRET,
                'code': code,
            },
            timeout=15,
        )
        body = resp.json() if resp.content else {}
        token = body.get('access_token')
    except Exception as e:
        logger.exception('[shopify_oauth] token exchange failed: %s', e)
        token = None

    if not token:
        return HttpResponseRedirect(f'{portal}?shopify=error')

    client.shopify_shop_domain = shop
    client.shopify_access_token = token
    client.shopify_scopes = body.get('scope', settings.SHOPIFY_APP_SCOPES)
    client.shopify_connected_at = timezone.now()
    if client.platform != 'SHOPIFY':
        client.platform = 'SHOPIFY'
    client.save(update_fields=['shopify_shop_domain', 'shopify_access_token',
                               'shopify_scopes', 'shopify_connected_at', 'platform'])
    logger.info('[shopify_oauth] connected %s to client %s', shop, client.id)
    return HttpResponseRedirect(f'{portal}?shopify=connected')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def shopify_disconnect(request, client_id):
    """Tenant disconnects their Shopify store (clears the stored token)."""
    try:
        client = get_accessible_clients(request.user).get(pk=client_id)
    except (Client.DoesNotExist, ValueError):
        return Response({'detail': 'Not found.'}, status=404)
    client.shopify_shop_domain = ''
    client.shopify_access_token = ''
    client.shopify_scopes = ''
    client.shopify_connected_at = None
    client.save(update_fields=['shopify_shop_domain', 'shopify_access_token',
                               'shopify_scopes', 'shopify_connected_at'])
    return Response({'detail': 'Disconnected.'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def shopify_status(request, client_id):
    """Connection status for the portal Integrations UI."""
    try:
        client = get_accessible_clients(request.user).get(pk=client_id)
    except (Client.DoesNotExist, ValueError):
        return Response({'detail': 'Not found.'}, status=404)
    return Response({
        'connected': bool(client.shopify_access_token and client.shopify_shop_domain),
        'shop_domain': client.shopify_shop_domain,
        'scopes': client.shopify_scopes,
        'connected_at': client.shopify_connected_at.isoformat() if client.shopify_connected_at else None,
    })


# ── GDPR mandatory webhooks (required for app review) ─────────────────────────
def _verify_webhook_hmac(request) -> bool:
    secret = settings.SHOPIFY_APP_CLIENT_SECRET
    received = request.headers.get('X-Shopify-Hmac-Sha256', '')
    if not secret or not received:
        return False
    import base64
    digest = base64.b64encode(hmac.new(secret.encode('utf-8'), request.body, hashlib.sha256).digest()).decode()
    return hmac.compare_digest(digest, received)


@api_view(['POST'])
@permission_classes([AllowAny])
def shopify_gdpr_customers_data_request(request):
    if not _verify_webhook_hmac(request):
        return HttpResponse(status=401)
    # We store no Shopify customer PII beyond transient order lookups — nothing to export.
    return HttpResponse(status=200)


@api_view(['POST'])
@permission_classes([AllowAny])
def shopify_gdpr_customers_redact(request):
    if not _verify_webhook_hmac(request):
        return HttpResponse(status=401)
    return HttpResponse(status=200)


@api_view(['POST'])
@permission_classes([AllowAny])
def shopify_gdpr_shop_redact(request):
    """Shop uninstalled / data erasure — drop the stored token for that shop."""
    if not _verify_webhook_hmac(request):
        return HttpResponse(status=401)
    try:
        shop = _normalize_shop((request.data or {}).get('shop_domain', ''))
        if shop:
            for c in Client.objects.filter(shopify_shop_domain=shop):
                c.shopify_access_token = ''
                c.shopify_connected_at = None
                c.save(update_fields=['shopify_access_token', 'shopify_connected_at'])
    except Exception:
        pass
    return HttpResponse(status=200)
