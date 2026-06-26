"""
Tenant-declared promotions / offers.

A tenant lists active offers on Client.active_offers (JSON, same pattern as
canned_responses / page_rules). Each offer:
    {
      "id": "uuid",
      "type": "sale" | "discount" | "bundle" | "free_shipping" | "new_arrival" | "seasonal" | "other",
      "title": "Summer Sale",          # short headline (optional)
      "description": "20% off everything",
      "link": "https://shop.com/sale", # offer page to redirect to (optional)
      "starts_at": "2026-06-01",       # ISO date (optional → open start)
      "ends_at": "2026-06-30",         # ISO date inclusive (optional → open end)
      "enabled": true
    }

The chatbot is *told* about currently-live offers via a dynamic prompt block
(same mechanism as order-status / page-context). Offers auto-expire purely by
date — once `ends_at` has passed they simply stop being injected; nothing to
purge. This stays fully separate from the reactive FOMO/discount_code/cta_*
fields (those are unchanged).
"""
from datetime import date
from django.utils import timezone

OFFER_TYPES = ['sale', 'discount', 'bundle', 'free_shipping', 'new_arrival', 'seasonal', 'other']
MAX_ACTIVE = 3


def _today():
    return timezone.now().date()


def _parse_date(d):
    """'YYYY-MM-DD' (or ISO datetime) → date, or None."""
    if not d:
        return None
    try:
        p = str(d)[:10].split('-')
        return date(int(p[0]), int(p[1]), int(p[2]))
    except (ValueError, IndexError, TypeError):
        return None


def is_active(offer, today=None):
    """True if the offer is enabled, within its date window, and has content."""
    if not isinstance(offer, dict):
        return False
    if offer.get('enabled') is False:
        return False
    today = today or _today()
    start = _parse_date(offer.get('starts_at'))
    end = _parse_date(offer.get('ends_at'))
    if start and today < start:
        return False
    if end and today > end:
        return False
    return bool(str(offer.get('description') or offer.get('title') or '').strip())


def active_offers(client, limit=MAX_ACTIVE, today=None):
    """Currently-live offers for a client (date-gated, capped)."""
    offers = getattr(client, 'active_offers', None) or []
    out = [o for o in offers if is_active(o, today=today)]
    return out[:limit]


def format_offers_block(offers):
    """Build the ACTIVE OFFERS prompt block. Returns '' when there are none."""
    if not offers:
        return ''

    def _s(v):  # coerce arbitrary JSON values to a clean string (defensive)
        return str(v).strip() if v else ''

    lines = []
    for o in offers:
        head = _s(o.get('title')) or _s(o.get('type')).replace('_', ' ').title() or 'Offer'
        desc = _s(o.get('description'))
        link = _s(o.get('link'))
        end = o.get('ends_at')
        parts = [head]
        if desc:
            parts.append(f'— {desc}')
        if end:
            parts.append(f'(ends {str(end)[:10]})')
        line = '• ' + ' '.join(parts)
        if link:
            line += f' | Link: {link}'
        lines.append(line)
    body = '\n'.join(lines)
    return (
        "\n\nACTIVE OFFERS — the store currently has these live promotions:\n" + body +
        "\n\nWhen the visitor shows buying intent, asks about deals/prices/offers, or it is "
        "naturally relevant, mention the MOST relevant offer in ONE friendly sentence and, if a "
        "link is given, share it as a markdown link like [See the offer](url). Mention an offer "
        "at most once unless the visitor asks again — do not repeat it in every reply. NEVER "
        "invent offers, discounts, or dates beyond this list."
    )
