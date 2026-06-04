"""
Tests for WooCommerce Store-API price ingestion (Issue 1).

Covers:
  • _format_wc_price — minor-unit math, sale vs regular, price ranges,
    currency symbol/prefix placement, empty/external products
  • fetch_woocommerce_data — builds price-bearing chunks, pagination,
    out-of-stock flag, graceful empty on missing endpoint
"""
from unittest.mock import patch, MagicMock

import pytest

from scraper.ingestion import _format_wc_price, fetch_woocommerce_data


def _ok(json_body):
    m = MagicMock()
    m.status_code = 200
    m.json.return_value = json_body
    return m


def _miss():
    m = MagicMock()
    m.status_code = 404
    m.json.return_value = []
    return m


# ─── _format_wc_price ────────────────────────────────────────────────────────

class TestFormatWcPrice:
    LKR = {
        'currency_minor_unit': 2,
        'currency_symbol': 'රු',
        'currency_prefix': 'රු',
        'currency_suffix': '',
    }

    def test_simple_price_minor_unit_math(self):
        out = _format_wc_price({**self.LKR, 'price': '1600', 'regular_price': '1600', 'sale_price': ''})
        assert out == 'රු16.00'

    def test_on_sale_shows_regular(self):
        out = _format_wc_price({**self.LKR, 'price': '1600', 'regular_price': '1800', 'sale_price': '1600'})
        assert out == 'රු16.00 (on sale, was රු18.00)'

    def test_price_range_variable_product(self):
        out = _format_wc_price({
            **self.LKR, 'price': '4200',
            'price_range': {'min_amount': '4200', 'max_amount': '4500'},
        })
        assert out == 'රු42.00 – රු45.00'

    def test_zero_minor_unit_currency(self):
        # e.g. JPY — minor unit 0, no decimals
        out = _format_wc_price({
            'currency_minor_unit': 0, 'currency_symbol': '¥',
            'currency_prefix': '¥', 'currency_suffix': '',
            'price': '1500', 'regular_price': '1500',
        })
        assert out == '¥1,500'

    def test_suffix_currency(self):
        out = _format_wc_price({
            'currency_minor_unit': 2, 'currency_symbol': 'kr',
            'currency_prefix': '', 'currency_suffix': ' kr',
            'price': '9900', 'regular_price': '9900',
        })
        assert out == '99.00 kr'

    def test_empty_price_returns_blank(self):
        assert _format_wc_price({**self.LKR, 'price': '', 'regular_price': ''}) == ''
        assert _format_wc_price({}) == ''
        assert _format_wc_price(None) == ''


# ─── fetch_woocommerce_data ──────────────────────────────────────────────────

@pytest.mark.django_db
class TestFetchWooCommerceData:
    def _cap_product(self):
        return {
            'id': 12, 'name': 'Cap', 'permalink': 'https://shop.test/product/cap/',
            'sku': 'CAP-1',
            'short_description': '<p>A nice cap.</p>',
            'description': '<p>Full desc.</p>',
            'is_in_stock': True,
            'categories': [{'name': 'Headwear'}],
            'prices': {
                'price': '1600', 'regular_price': '1800', 'sale_price': '1600',
                'currency_code': 'LKR', 'currency_minor_unit': 2,
                'currency_symbol': 'රු', 'currency_prefix': 'රු', 'currency_suffix': '',
            },
        }

    def test_builds_price_chunk(self):
        def fake_get(url, params=None, headers=None, timeout=None):
            if params and params.get('page', 1) == 1:
                return _ok([self._cap_product()])
            return _ok([])
        with patch('scraper.ingestion.requests.get', side_effect=fake_get):
            docs = fetch_woocommerce_data('https://shop.test')

        assert len(docs) == 1
        d = docs[0]
        assert d['title'] == 'Cap'
        assert d['url'] == 'https://shop.test/product/cap/'
        assert 'Price: රු16.00 (on sale, was රු18.00)' in d['content']
        assert d['metadata']['type'] == 'product'
        assert d['metadata']['price_display'] == 'රු16.00 (on sale, was රු18.00)'
        assert d['metadata']['currency'] == 'LKR'
        assert d['metadata']['is_active'] is True
        assert d['product_id'] == '12'

    def test_out_of_stock_flagged(self):
        p = self._cap_product()
        p['is_in_stock'] = False
        def fake_get(url, params=None, headers=None, timeout=None):
            if params and params.get('page', 1) == 1:
                return _ok([p])
            return _ok([])
        with patch('scraper.ingestion.requests.get', side_effect=fake_get):
            docs = fetch_woocommerce_data('https://shop.test')
        assert docs[0]['metadata']['is_active'] is False
        assert 'Stock: OUT OF STOCK' in docs[0]['content']

    def test_missing_endpoint_returns_empty(self):
        with patch('scraper.ingestion.requests.get', return_value=_miss()):
            assert fetch_woocommerce_data('https://no-woo.test') == []

    def test_paginates(self):
        page1 = [{'id': i, 'name': f'P{i}', 'permalink': f'https://s.test/p/{i}',
                  'prices': {'price': '1000', 'regular_price': '1000',
                             'currency_minor_unit': 2, 'currency_symbol': '$',
                             'currency_prefix': '$', 'currency_suffix': ''}}
                 for i in range(100)]
        page2 = [{'id': 200, 'name': 'Last', 'permalink': 'https://s.test/p/200',
                  'prices': {'price': '2000', 'regular_price': '2000',
                             'currency_minor_unit': 2, 'currency_symbol': '$',
                             'currency_prefix': '$', 'currency_suffix': ''}}]

        def fake_get(url, params=None, headers=None, timeout=None):
            pg = params.get('page', 1)
            return _ok(page1 if pg == 1 else page2 if pg == 2 else [])
        with patch('scraper.ingestion.requests.get', side_effect=fake_get):
            docs = fetch_woocommerce_data('https://s.test')
        assert len(docs) == 101
        assert docs[-1]['title'] == 'Last'
