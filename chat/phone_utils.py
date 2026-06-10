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
    Country-dispatching entry point. Today only 'LK' is enforced; any other
    country falls through to a permissive pass (kept as-is, marked valid if
    it has a plausible length) so non-LK tenants aren't blocked.
    """
    country = (country or DEFAULT_COUNTRY).upper()
    if country == 'LK':
        norm, ok = normalize_lk_phone(raw)
        if ok:
            return norm, ok
        # Keep +94 as the DEFAULT (bare local numbers normalise above), but
        # don't reject an international visitor who typed a non-LK number into
        # the lead form — fall through to the permissive path below so the
        # lead is still captured. (Free-text extraction stays strict via
        # extract_lk_phone, so this leniency only applies to explicit form
        # input.)

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
