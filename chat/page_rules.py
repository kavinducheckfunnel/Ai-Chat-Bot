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
                'enabled_widget', 'greeting_enabled', 'greeting_message',
                # Per-page overrides for widget behavior (blank → use global).
                'notification_timeout', 'auto_close', 'notification_delay')


# Dynamic tags available per page type. Surfaced in the portal so tenants know
# which {placeholders} they can drop into a greeting / behavior prompt. The
# widget fills them client-side from the live page (no LLM); the server
# re-derives from the request + client for persistence. Unknown values degrade
# gracefully — a tag never leaks literally as "{product_name}".
PAGE_TAGS = {
    'home':       [{'tag': '{store_name}', 'label': 'Store name'}],
    'collection': [{'tag': '{category_name}', 'label': 'Category name'}, {'tag': '{store_name}', 'label': 'Store name'}],
    'product':    [{'tag': '{product_name}', 'label': 'Product name'}, {'tag': '{store_name}', 'label': 'Store name'}],
    'cart':       [{'tag': '{cart_item_count}', 'label': 'Items in cart'}, {'tag': '{cart_total}', 'label': 'Cart total'}, {'tag': '{store_name}', 'label': 'Store name'}],
    'checkout':   [{'tag': '{checkout_step}', 'label': 'Checkout step'}, {'tag': '{store_name}', 'label': 'Store name'}],
    'contact':    [{'tag': '{store_name}', 'label': 'Store name'}],
    'about':      [{'tag': '{store_name}', 'label': 'Store name'}],
    'track':      [{'tag': '{store_name}', 'label': 'Store name'}],
    'offers':     [{'tag': '{store_name}', 'label': 'Store name'}],
    'faq':        [{'tag': '{store_name}', 'label': 'Store name'}],
    'fallback':   [{'tag': '{store_name}', 'label': 'Store name'}],
}

# Generic word substituted when a tag's value is unknown at render time.
_TAG_FALLBACKS = {
    'product_name': 'this product',
    'category_name': 'this collection',
    'store_name': 'our store',
    'cart_item_count': 'some',
    'cart_total': '',
    'checkout_step': 'this',
}
# "the {tag}" reads wrong with a generic noun ("the this product"), so soften
# the article away when the value is missing.
_TAG_SOFTEN = {
    'product_name': 'this product',
    'category_name': 'this collection',
    'store_name': 'our store',
}

_TAG_RE = re.compile(r'\{([a-z_]+)\}')


def page_tags(page_type):
    """Public list of {tag,label} dynamic placeholders valid for a page type."""
    return PAGE_TAGS.get(page_type or 'fallback', PAGE_TAGS['fallback'])


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
            # trailing-slash insensitive (/about == /about/)
            return path.rstrip('/') == pat.rstrip('/') or path == pat
        if mt == 'prefix':
            return path.startswith(pat)
        if mt == 'regex':
            return re.search(pat, path) is not None
        return pat.lower() in path.lower()  # contains
    except re.error:
        return False


def _rule_matches(rule, path):
    pt = (rule.get('page_type') or '')
    pat = rule.get('pattern') or ''
    # The designated fallback (NO pattern) is the ONLY true catch-all. A page
    # that merely CLASSIFIES as 'fallback' (e.g. /hello-world, /sample-page on
    # WordPress) must match its own pattern only — otherwise it acts as a
    # catch-all and hijacks every other page, incl. home. (This was the
    # "home page not working" bug.)
    if pt == 'fallback' and not pat:
        return True
    if _pattern_matches(rule, path):
        return True
    # Robust classify fallback for Shopify/Woo variants (/category/, /contact-us/,
    # /help/, …) — but NEVER for 'fallback': every unmatched path classifies as
    # fallback, so allowing it here would re-introduce the catch-all hijack.
    return bool(pt) and pt != 'fallback' and classify_path(path) == pt


def get_rules(client):
    """Return the effective rule list for a client (custom or defaults)."""
    rules = getattr(client, 'page_rules', None) if client else None
    if isinstance(rules, list) and rules:
        return rules
    return DEFAULT_PAGE_RULES


def match_rule(rules, url):
    """Return the best rule matching the URL/path, or None.

    Ranked by (priority desc, pattern-length desc) so a MORE SPECIFIC rule wins
    over a generic one at the same priority. This is what lets a sub-page
    inherit its nearest ancestor: a custom rule for ``/products/tshirts`` beats
    the generic ``/products/`` template on ``/products/tshirts/polo`` because
    its pattern is longer.
    """
    path = _path_of(url)
    ranked = sorted(
        rules or [],
        key=lambda r: ((r.get('priority', 0) or 0), len(r.get('pattern') or '')),
        reverse=True,
    )
    for r in ranked:
        if _rule_matches(r, path):
            return r
    return None


def resolve_greeting_text(rule, product_name=None, values=None, keep_unknown=False):
    """Fill dynamic {tags} in a rule's greeting message, degrading gracefully.

    ``values`` is a dict of tag → value (e.g. {'product_name': 'Blue Hoodie',
    'store_name': 'Acme'}). For backward compatibility the 2nd positional arg
    may be a bare product_name string OR a values dict.

    ``keep_unknown`` — when True, ONLY tags we have a value for are substituted;
    every other ``{placeholder}`` (a known tag with no value, or any word the
    tenant happened to wrap in braces) is left untouched. Use this for free-form
    AI behaviour prompts so incidental ``{...}`` prose isn't silently deleted.
    The default (False) is the customer-facing greeting mode: missing tags fall
    back to a generic word so a literal "{product_name}" never reaches a visitor.
    """
    msg = (rule.get('greeting_message') or '').strip()
    if not msg:
        return msg

    vals = {}
    if isinstance(product_name, dict):
        vals.update(product_name)
    elif product_name:
        vals['product_name'] = product_name
    if isinstance(values, dict):
        vals.update(values)
    # Normalise everything to trimmed strings.
    vals = {k: ('' if v is None else str(v).strip()) for k, v in vals.items()}

    # Soften "the {tag}" first when the value is missing (avoids "the this …").
    # Greeting mode only — in keep_unknown mode we never substitute a fallback.
    if not keep_unknown:
        for key, soft in _TAG_SOFTEN.items():
            if not vals.get(key):
                msg = msg.replace('the {' + key + '}', soft)

    def _repl(m):
        key = m.group(1)
        v = vals.get(key)
        if v:
            return v
        if keep_unknown:
            return m.group(0)  # leave the literal placeholder intact
        return _TAG_FALLBACKS.get(key, '')

    msg = _TAG_RE.sub(_repl, msg)
    if keep_unknown:
        return msg
    # Tidy any double space a dropped tag left behind.
    return re.sub(r'\s{2,}', ' ', msg).strip()


def public_rules(client):
    """Rules for the widget — strips behavior_prompt (server-only)."""
    out = []
    for r in get_rules(client):
        out.append({k: r.get(k) for k in _PUBLIC_KEYS if k in r or k in ('enabled_widget', 'greeting_enabled')})
    return out
