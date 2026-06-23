"""Tests for Shopify order tracking — intent, lookup (email verification), OAuth helpers."""
import pytest
from unittest.mock import patch, MagicMock

from chat import shopify_orders as so
from chat import shopify_oauth as oauth


class TestIntent:
    def test_is_order_query(self):
        assert so.is_order_query("where is my order?")
        assert so.is_order_query("can you track my package")
        assert so.is_order_query("has it shipped yet")
        assert so.is_order_query("order status please")
        assert not so.is_order_query("do you have this in blue?")

    def test_extract_order_number(self):
        assert so.extract_order_number("my order #1042 please") == "1042"
        assert so.extract_order_number("order 100345") == "100345"
        assert so.extract_order_number("no number here") == ""


class TestNormalizeShop:
    def test_valid(self):
        assert oauth._normalize_shop("My-Store") == "my-store.myshopify.com"
        assert oauth._normalize_shop("https://abc.myshopify.com/") == "abc.myshopify.com"

    def test_invalid(self):
        assert oauth._normalize_shop("not a domain!!") == ""
        assert oauth._normalize_shop("") == ""


@pytest.mark.django_db
class TestLookup:
    def _client(self, connected=True):
        from users.models import Client
        return Client.objects.create(
            name="S", platform="SHOPIFY",
            shopify_shop_domain="abc.myshopify.com" if connected else "",
            shopify_access_token="tok" if connected else "",
        )

    def test_not_connected(self):
        c = self._client(connected=False)
        assert so.lookup_order(c, "1042", "a@b.com")["reason"] == "not_connected"

    def test_missing_args(self):
        c = self._client()
        assert so.lookup_order(c, "", "a@b.com")["reason"] == "missing"
        assert so.lookup_order(c, "1042", "")["reason"] == "missing"

    def test_email_match_success(self):
        c = self._client()
        fake = MagicMock(ok=True, status_code=200)
        fake.json.return_value = {'orders': [{
            'name': '#1042', 'order_number': 1042, 'email': 'Jo@Example.com',
            'financial_status': 'paid', 'fulfillment_status': 'fulfilled',
            'fulfillments': [{'tracking_company': 'DHL', 'tracking_number': 'X1',
                              'tracking_urls': ['http://t/X1'], 'shipment_status': 'in_transit'}],
            'line_items': [{'title': 'Belt', 'quantity': 1}],
            'created_at': '2026-06-20T10:00:00Z',
        }]}
        with patch('chat.shopify_orders.http_requests.get', return_value=fake):
            res = so.lookup_order(c, "1042", "jo@example.com")  # case-insensitive
        assert res['ok'] is True
        assert res['order']['number'] == '#1042'
        assert res['order']['fulfillments'][0]['tracking_number'] == 'X1'

    def test_email_mismatch_denied(self):
        c = self._client()
        fake = MagicMock(ok=True, status_code=200)
        fake.json.return_value = {'orders': [{'name': '#1042', 'email': 'someone@else.com'}]}
        with patch('chat.shopify_orders.http_requests.get', return_value=fake):
            res = so.lookup_order(c, "1042", "attacker@evil.com")
        assert res['ok'] is False
        assert res['reason'] == 'not_found'  # never reveal the order exists

    def test_format_order_context(self):
        ctx = so.format_order_context({
            'number': '#1042', 'fulfillment_status': 'fulfilled', 'financial_status': 'paid',
            'fulfillments': [{'shipment_status': 'in_transit', 'carrier': 'DHL', 'tracking_number': 'X1', 'tracking_url': 'http://t/X1'}],
            'items': [{'title': 'Belt', 'quantity': 1}], 'created_at': '2026-06-20T10:00:00Z',
        })
        assert '#1042' in ctx and 'in_transit' in ctx and 'X1' in ctx
