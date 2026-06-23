"""
Shopify order lookup for the chatbot's order-status feature.

Security: an order is only returned when BOTH the order number AND the email on
the order match what the visitor provided — same standard as Shopify's own order
status page. We never reveal whether an order exists for a non-matching email.
"""
import logging
import re

import requests as http_requests
from django.conf import settings

logger = logging.getLogger(__name__)

# "where's my order", "track order", "order status", "is it shipped/delivered", etc.
ORDER_STATUS_RE = re.compile(
    r'\b('
    r'where.{0,12}(order|package|parcel|delivery|shipment)|'
    r'track(ing)?.{0,12}(order|package|number|id)?|'
    r'order\s*status|status\s*of\s*my\s*order|my\s*order|'
    r'(has|is|was).{0,12}(it|order|package).{0,12}(ship|deliver|dispatch|sent|arriv)|'
    r'when.{0,15}(arrive|deliver|get|receive)|'
    r'order\s*(number|no\.?|id|#)|delivered|shipped'
    r')\b',
    re.IGNORECASE,
)

# Order number like "#1042", "1042", "order 1042" — captures the digits.
_ORDER_NUM_RE = re.compile(r'#?\b(\d{3,10})\b')


def is_order_query(text: str) -> bool:
    return bool(text) and bool(ORDER_STATUS_RE.search(text))


def extract_order_number(text: str) -> str:
    """Best-effort order-number extraction from free text. Returns '' if none."""
    if not text:
        return ''
    # Prefer a #-prefixed token, else the first 3-10 digit run.
    m = re.search(r'#(\d{3,10})', text) or _ORDER_NUM_RE.search(text)
    return m.group(1) if m else ''


def is_connected(client) -> bool:
    return bool(getattr(client, 'shopify_access_token', '') and getattr(client, 'shopify_shop_domain', ''))


def lookup_order(client, order_number: str, email: str) -> dict:
    """
    Look up one order by number, verifying it belongs to `email`.

    Returns:
      {'ok': True, 'order': {...}}            on a verified match
      {'ok': False, 'reason': 'not_connected'|'missing'|'not_found'|'error'}
    """
    if not is_connected(client):
        return {'ok': False, 'reason': 'not_connected'}
    order_number = (order_number or '').strip().lstrip('#')
    email = (email or '').strip().lower()
    if not order_number or not email:
        return {'ok': False, 'reason': 'missing'}

    shop = client.shopify_shop_domain
    version = settings.SHOPIFY_API_VERSION
    url = f'https://{shop}/admin/api/{version}/orders.json'
    headers = {'X-Shopify-Access-Token': client.shopify_access_token}
    # `name` matches the customer-facing order number (e.g. "#1042" or "1042").
    params = {'status': 'any', 'name': order_number, 'limit': 5,
              'fields': 'id,name,order_number,email,contact_email,financial_status,'
                        'fulfillment_status,created_at,line_items,fulfillments,current_total_price,currency'}
    try:
        resp = http_requests.get(url, headers=headers, params=params, timeout=12)
        if resp.status_code == 401:
            return {'ok': False, 'reason': 'error'}
        orders = (resp.json() or {}).get('orders', []) if resp.ok else []
    except Exception as e:
        logger.warning('[shopify_orders] lookup failed for %s: %s', shop, e)
        return {'ok': False, 'reason': 'error'}

    # Verify ownership by email (case-insensitive). Never reveal a mismatch.
    match = None
    for o in orders:
        o_email = (o.get('email') or o.get('contact_email') or '').strip().lower()
        if o_email and o_email == email:
            match = o
            break
    if not match:
        return {'ok': False, 'reason': 'not_found'}

    return {'ok': True, 'order': _normalize(match)}


def _normalize(o: dict) -> dict:
    fulfillments = []
    for f in (o.get('fulfillments') or []):
        fulfillments.append({
            'carrier': f.get('tracking_company') or '',
            'tracking_number': f.get('tracking_number') or '',
            'tracking_url': (f.get('tracking_urls') or [None])[0] or f.get('tracking_url') or '',
            'shipment_status': f.get('shipment_status') or '',
            'status': f.get('status') or '',
        })
    items = [{'title': li.get('title', ''), 'quantity': li.get('quantity', 1)}
             for li in (o.get('line_items') or [])][:10]
    return {
        'number': o.get('name') or f"#{o.get('order_number', '')}",
        'financial_status': o.get('financial_status') or '',
        'fulfillment_status': o.get('fulfillment_status') or 'unfulfilled',
        'fulfillments': fulfillments,
        'items': items,
        'total': o.get('current_total_price') or '',
        'currency': o.get('currency') or '',
        'created_at': o.get('created_at') or '',
    }


def format_order_context(order: dict) -> str:
    """Render a compact, factual order summary for injection into the LLM prompt."""
    lines = [f"ORDER {order['number']}:"]
    fs = order.get('fulfillment_status') or 'unfulfilled'
    lines.append(f"- Fulfillment status: {fs}")
    if order.get('financial_status'):
        lines.append(f"- Payment status: {order['financial_status']}")
    for f in order.get('fulfillments', []):
        bits = []
        if f.get('shipment_status'):
            bits.append(f"shipment: {f['shipment_status']}")
        if f.get('carrier'):
            bits.append(f"carrier: {f['carrier']}")
        if f.get('tracking_number'):
            bits.append(f"tracking #: {f['tracking_number']}")
        if f.get('tracking_url'):
            bits.append(f"tracking link: {f['tracking_url']}")
        if bits:
            lines.append('- Shipment: ' + ', '.join(bits))
    if order.get('items'):
        items = ', '.join(f"{i['quantity']}× {i['title']}" for i in order['items'])
        lines.append(f"- Items: {items}")
    if order.get('created_at'):
        lines.append(f"- Placed: {order['created_at'][:10]}")
    return '\n'.join(lines)
