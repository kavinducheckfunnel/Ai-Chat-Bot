"""
Page-aware trigger rules — shared server-side logic for URL → page-type
classification, rule matching, and greeting-text resolution.

A "page rule" (stored on Client.page_rules as JSON, or the defaults below) is:
    {
      "id": "uuid",
      "label": "Single Product",
      "match_type": "contains" | "prefix" | "exact" | "regex",
      "pattern": "/products/",
      "page_type": "product",
      "priority": 60,
      "enabled_widget": true,        # False = hide the widget on this page
      "greeting_enabled": true,      # False = no proactive greeting here
      "greeting_message": "Interested in the {product_name}? ...",
      "behavior_prompt": ""          # how the AI should act on this page (in-chat)
    }

The SAME matching/classification semantics are mirrored in the widget
(embedCodeGenerator.js) so the client can render greetings instantly without a
round-trip, while the server re-derives authoritatively for persistence.
"""
import re

# Canonical page types we recognise.
PAGE_TYPES = (
    'home', 'collection', 'product', 'cart', 'checkout', 'contact',
    'about', 'faq', 'offers', 'track', 'fallback',
)


def classify_path(path):
    """Map a URL path to a canonical page_type using Shopify/Woo/common
    conventions. Order matters — most specific first."""
    p = (path or '/').lower()
    # strip query/hash
    p = p.split('?', 1)[0].split('#', 1)[0]
    if p in ('', '/', '/home', '/home/'):
        return 'home'
    # checkout before cart (some carts live under /checkout)
    if '/checkout' in p:
        return 'checkout'
    if '/cart' in p:
        return 'cart'
    if '/products/' in p or '/product/' in p:
        return 'product'
    if '/collections/' in p or '/category/' in p or '/product-category/' in p or '/shop' in p:
        return 'collection'
    if '/order-tracking' in p or '/track' in p or '/orders/' in p:
        return 'track'
    if '/offers' in p or '/pricing' in p or '/deals' in p or '/sale' in p:
        return 'offers'
    if '/contact' in p:
        return 'contact'
    if '/about' in p:
        return 'about'
    if '/faq' in p or '/help' in p:
        return 'faq'
    return 'fallback'


# Default rules seeded from the GrowMiq URL-trigger brief. Tenants can edit /
# extend these in the portal; if Client.page_rules is empty we fall back here.
DEFAULT_PAGE_RULES = [
    {'label': 'Single Product', 'match_type': 'contains', 'pattern': '/products/', 'page_type': 'product', 'priority': 60,
     'enabled_widget': True, 'greeting_enabled': True,
     'greeting_message': "Interested in the {product_name}? I can help you with details, pricing, sizing/color options, or even suggest similar items.",
     'behavior_prompt': ''},
    {'label': 'Checkout', 'match_type': 'contains', 'pattern': '/checkout', 'page_type': 'checkout', 'priority': 58,
     'enabled_widget': True, 'greeting_enabled': True,
     'greeting_message': "Almost there! Let me know if you need any help completing your order or if you run into any issues with payment and shipping.",
     'behavior_prompt': ''},
    {'label': 'Cart', 'match_type': 'contains', 'pattern': '/cart', 'page_type': 'cart', 'priority': 55,
     'enabled_widget': True, 'greeting_enabled': True,
     'greeting_message': "Looks like you have some great items in your cart! Need any help with delivery details or payment options before you check out?",
     'behavior_prompt': ''},
    {'label': 'Product Listing / Category', 'match_type': 'contains', 'pattern': '/collections/', 'page_type': 'collection', 'priority': 50,
     'enabled_widget': True, 'greeting_enabled': True,
     'greeting_message': "Need help choosing the right item? Tell me what you're looking for, and I'll suggest some great options for you.",
     'behavior_prompt': ''},
    {'label': 'Order Tracking', 'match_type': 'contains', 'pattern': '/track', 'page_type': 'track', 'priority': 50,
     'enabled_widget': True, 'greeting_enabled': True,
     'greeting_message': "Want to check your order status? Just share your order details, and I'll track it down for you.",
     'behavior_prompt': ''},
    {'label': 'Pricing / Offers', 'match_type': 'contains', 'pattern': '/offers', 'page_type': 'offers', 'priority': 48,
     'enabled_widget': True, 'greeting_enabled': True,
     'greeting_message': "Looking for the best deal? I can walk you through our current discounts and special packages.",
     'behavior_prompt': ''},
    {'label': 'Contact', 'match_type': 'contains', 'pattern': '/contact', 'page_type': 'contact', 'priority': 45,
     'enabled_widget': True, 'greeting_enabled': True,
     'greeting_message': "Need to get in touch? Ask your question right here, and I'll assist you or connect you directly to our support team.",
     'behavior_prompt': ''},
    {'label': 'FAQ / Help', 'match_type': 'contains', 'pattern': '/faq', 'page_type': 'faq', 'priority': 42,
     'enabled_widget': True, 'greeting_enabled': True,
     'greeting_message': "Have a question? Let me know what you need help with—whether it's returns, payments, or order tracking.",
     'behavior_prompt': ''},
    {'label': 'About', 'match_type': 'contains', 'pattern': '/about', 'page_type': 'about', 'priority': 40,
     'enabled_widget': True, 'greeting_enabled': True,
     'greeting_message': "Want to know more about us? I'm here to answer any questions about our brand, products, and services.",
     'behavior_prompt': ''},
    {'label': 'Home', 'match_type': 'exact', 'pattern': '/', 'page_type': 'home', 'priority': 10,
     'enabled_widget': True, 'greeting_enabled': True,
     'greeting_message': "Looking for something special today? I can help you find specific products, current offers, or our best-selling items.",
     'behavior_prompt': ''},
    {'label': 'Fallback', 'match_type': 'contains', 'pattern': '', 'page_type': 'fallback', 'priority': 0,
     'enabled_widget': True, 'greeting_enabled': True,
     'greeting_message': "How can I help you with your shopping today?",
     'behavior_prompt': ''},
]

# Public-safe rule keys shipped to the widget (NEVER expose behavior_prompt).
_PUBLIC_KEYS = ('id', 'label', 'match_type', 'pattern', 'page_type', 'priority',
                'enabled_widget', 'greeting_enabled', 'greeting_message')


def _path_of(url):
    """Extract the path portion from a full URL or a bare path."""
    if not url:
        return '/'
    s = str(url)
    # strip scheme + host
    m = re.match(r'^[a-zA-Z][a-zA-Z0-9+.\-]*://[^/]+(/.*)?$', s)
    if m:
        s = m.group(1) or '/'
    s = s.split('?', 1)[0].split('#', 1)[0]
    return s or '/'


def _pattern_matches(rule, path):
    mt = rule.get('match_type') or 'contains'
    pat = rule.get('pattern') or ''
    if not pat:
        return False
    try:
        if mt == 'exact':
            return path == pat
        if mt == 'prefix':
            return path.startswith(pat)
        if mt == 'regex':
            return re.search(pat, path) is not None
        return pat.lower() in path.lower()  # contains
    except re.error:
        return False


def _rule_matches(rule, path):
    if (rule.get('page_type') or '') == 'fallback':
        return True  # catch-all
    if _pattern_matches(rule, path):
        return True
    # Robust fallback: classify the path and match by canonical page_type so
    # Shopify/Woo variants (/category/, /contact-us/, /help/, …) still hit.
    pt = rule.get('page_type')
    return bool(pt) and classify_path(path) == pt


def get_rules(client):
    """Return the effective rule list for a client (custom or defaults)."""
    rules = getattr(client, 'page_rules', None) if client else None
    if isinstance(rules, list) and rules:
        return rules
    return DEFAULT_PAGE_RULES


def match_rule(rules, url):
    """Return the highest-priority rule matching the URL/path, or None."""
    path = _path_of(url)
    ranked = sorted(rules or [], key=lambda r: r.get('priority', 0), reverse=True)
    for r in ranked:
        if _rule_matches(r, path):
            return r
    return None


def resolve_greeting_text(rule, product_name=None):
    """Fill {product_name} in a rule's greeting message, degrading gracefully."""
    msg = (rule.get('greeting_message') or '').strip()
    if '{product_name}' in msg:
        name = (product_name or '').strip()
        if name:
            msg = msg.replace('{product_name}', name)
        else:
            # No name available — soften "the {product_name}" → "this product".
            msg = msg.replace('the {product_name}', 'this product').replace('{product_name}', 'this product')
    return msg


def public_rules(client):
    """Rules for the widget — strips behavior_prompt (server-only)."""
    out = []
    for r in get_rules(client):
        out.append({k: r.get(k) for k in _PUBLIC_KEYS if k in r or k in ('enabled_widget', 'greeting_enabled')})
    return out
