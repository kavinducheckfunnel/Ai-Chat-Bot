"""Tests for Sri Lankan phone normalisation (Issue 3)."""
import pytest

from chat.phone_utils import normalize_lk_phone, normalize_phone, extract_lk_phone


class TestNormalizeLkPhone:
    @pytest.mark.parametrize('raw,expected', [
        ('0771234567', '+94771234567'),
        ('771234567', '+94771234567'),
        ('+94771234567', '+94771234567'),
        ('94771234567', '+94771234567'),
        ('0094771234567', '+94771234567'),
        ('077 123 4567', '+94771234567'),
        ('077-123-4567', '+94771234567'),
        ('+94 77 123 4567', '+94771234567'),
        ('(077) 1234567', '+94771234567'),
    ])
    def test_valid_forms_normalise(self, raw, expected):
        norm, ok = normalize_lk_phone(raw)
        assert ok is True
        assert norm == expected

    @pytest.mark.parametrize('raw', [
        '',
        None,
        'not a phone',
        '12345',              # too short
        '0112345678',         # landline (starts 01, not 7) after trunk strip → 112345678
        '07712345',           # too short subscriber
        '07712345678',        # too long
        '+1 415 555 0100',    # US number
        '0987654321',         # starts 9 not 7 after trunk strip
    ])
    def test_invalid_forms_rejected(self, raw):
        norm, ok = normalize_lk_phone(raw)
        assert ok is False
        assert norm is None

    def test_all_valid_mobile_prefixes(self):
        for p in ['70', '71', '72', '74', '75', '76', '77', '78']:
            norm, ok = normalize_lk_phone(f'0{p}1234567')
            assert ok, f'prefix {p} should be valid'
            assert norm == f'+94{p}1234567'


class TestNormalizePhoneDispatch:
    def test_lk_default(self):
        assert normalize_phone('0771234567') == ('+94771234567', True)

    def test_other_country_permissive(self):
        norm, ok = normalize_phone('+1 415 555 0100', country='US')
        assert ok is True
        assert norm == '+14155550100'

    def test_other_country_too_short(self):
        assert normalize_phone('123', country='US') == (None, False)


class TestExtractLkPhone:
    def test_extracts_from_sentence(self):
        assert extract_lk_phone('call me on 077 123 4567 anytime') == '+94771234567'

    def test_extracts_e164(self):
        assert extract_lk_phone('my number is +94771234567') == '+94771234567'

    def test_none_when_absent(self):
        assert extract_lk_phone('no digits here') is None
        assert extract_lk_phone('order 12 of item 5') is None
