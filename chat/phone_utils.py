"""
Phone-number normalisation + validation.

Currently enforces the Sri Lankan (LK) standard, since that's the live
market. The country is a parameter (default 'LK') so this generalises
later without a rewrite — add a branch + rule table per country.

Sri Lankan mobile numbering:
  • E.164: +94 7X XXX XXXX  → country code 94, then a 9-digit subscriber
    number beginning with 7.
  • Mobile prefixes in use: 70, 71, 72, 74, 75, 76, 77, 78 (the digit after
    the leading 7). 73 and 79 are not allocated to mobile at time of writing,
    but we accept any 7X to stay forward-compatible — the hard rules are
    "starts with 7" and "exactly 9 subscriber digits".

Accepted inputs (all normalise to +94771234567):
  0771234567        (local trunk-prefixed)
  771234567         (bare subscriber)
  +94771234567      (already E.164)
  94771234567       (country code, no plus)
  0094771234567     (international access code)
  with spaces / dashes / parens anywhere
"""

import re

DEFAULT_COUNTRY = 'LK'


def normalize_lk_phone(raw):
    """
    Normalise a Sri Lankan phone number to E.164 (+94XXXXXXXXX).

    Returns (normalized_or_none, is_valid):
      • ('+94771234567', True)  on success
      • (None, False)           when the input can't be a valid LK mobile

    Never raises.
    """
    if not raw or not isinstance(raw, str):
        return None, False

    # Keep digits only; remember if the user typed a leading '+'.
    digits = re.sub(r'\D', '', raw)
    if not digits:
        return None, False

    # Strip international access codes / country code down to the 9-digit
    # subscriber number that must start with 7.
    #   0094771234567 → 94771234567 → 771234567
    if digits.startswith('0094'):
        digits = digits[4:]
    if digits.startswith('94'):
        digits = digits[2:]
    # Local trunk prefix: 0771234567 → 771234567
    if len(digits) == 10 and digits.startswith('0'):
        digits = digits[1:]

    # After stripping, a valid LK mobile subscriber number is exactly 9
    # digits and starts with 7.
    if len(digits) != 9 or not digits.startswith('7'):
        return None, False

    return f'+94{digits}', True


def normalize_phone(raw, country=DEFAULT_COUNTRY):
    """
    Country-dispatching entry point.

    For 'LK' this is STRICT — only a valid Sri Lankan mobile is accepted
    (+94 followed by a 9-digit subscriber starting with 7, i.e. 0XXXXXXXXX /
    +94XXXXXXXXX / 0094... forms). We deliberately do NOT fall back to the
    permissive international path: LK tenants asked for clean LK-only numbers
    so the CRM never fills with malformed junk.

    Any other country uses a light-touch permissive pass (plausible length)
    so non-LK tenants aren't blocked.
    """
    country = (country or DEFAULT_COUNTRY).upper()
    if country == 'LK':
        return normalize_lk_phone(raw)

    # Generic fallback for other markets / international numbers — light
    # touch, don't over-reject.
    digits = re.sub(r'\D', '', raw or '')
    if 7 <= len(digits) <= 15:
        plus = '+' if (raw or '').strip().startswith('+') else ''
        return f'{plus}{digits}', True
    return None, False


def extract_lk_phone(text):
    """
    Find and normalise the first LK mobile number embedded in free text
    (e.g. a chat message "you can call me on 077 123 4567"). Returns the
    normalized E.164 string or None.
    """
    if not text:
        return None
    # Candidate runs of digits/spaces/dashes/plus that could be a number.
    for m in re.finditer(r'(?:\+?\d[\d\s\-()]{6,}\d)', text):
        norm, ok = normalize_lk_phone(m.group(0))
        if ok:
            return norm
    return None


# Reasonably strict email matcher — good enough to auto-capture from chat text
# without false-positives on things like "v1.0" or "8am-5pm".
_EMAIL_RE = re.compile(r'\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b')


def is_valid_email(email):
    """True if `email` is a structurally valid address.

    Uses Django's EmailValidator (the same one model fields use) on top of a
    cheap double-dot guard, so junk like ``a@@b``, ``a@b``, ``a@b..com`` or
    ``foo@bar`` is rejected before it ever reaches the CRM.
    """
    if not email or not isinstance(email, str):
        return False
    email = email.strip()
    if not email or '..' in email or email.startswith('.') or '@' not in email:
        return False
    from django.core.validators import validate_email as _dj_validate
    from django.core.exceptions import ValidationError as _DjValidationError
    try:
        _dj_validate(email)
        return True
    except _DjValidationError:
        return False


def extract_email(text):
    """Return the first VALID email address in free text, or None."""
    if not text:
        return None
    m = _EMAIL_RE.search(text)
    if not m:
        return None
    email = m.group(0).strip('.').lower()
    return email if is_valid_email(email) else None


def extract_phone(text, country=DEFAULT_COUNTRY):
    """
    Find and normalise the first phone number in free text (QA #13 inline
    capture).

    For 'LK' this is STRICT — only a valid Sri Lankan mobile is returned, so a
    random run of digits (an order number, a price, a year) is never
    mis-captured as a phone lead. Other countries use a permissive international
    match so non-LK tenants still capture numbers.
    """
    if not text:
        return None
    country = (country or DEFAULT_COUNTRY).upper()
    if country == 'LK':
        return extract_lk_phone(text)
    # International fallback: a run of 8–15 digits (optionally +-prefixed) that
    # isn't obviously something else. Require at least 8 digits to avoid years,
    # prices, order numbers, etc.
    for m in re.finditer(r'(?:\+?\d[\d\s\-()]{6,}\d)', text):
        digits = re.sub(r'\D', '', m.group(0))
        if 8 <= len(digits) <= 15:
            norm, ok = normalize_phone(m.group(0), country)
            if ok:
                return norm
    return None
