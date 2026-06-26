"""
Tests for tenant-declared offers/promotions (chat/offers.py) — date-gating,
active filtering, prompt-block formatting, and serializer round-trip.
"""
import pytest
from datetime import date, timedelta

from chat import offers as of


def _d(days):
    return (date.today() + timedelta(days=days)).isoformat()


class TestIsActive:
    def test_live_within_window(self):
        assert of.is_active({'description': 'x', 'starts_at': _d(-1), 'ends_at': _d(1)}) is True

    def test_open_ended(self):
        assert of.is_active({'title': 'Sale'}) is True  # no dates → always live

    def test_not_started(self):
        assert of.is_active({'description': 'x', 'starts_at': _d(2)}) is False

    def test_expired(self):
        assert of.is_active({'description': 'x', 'ends_at': _d(-1)}) is False

    def test_disabled(self):
        assert of.is_active({'description': 'x', 'enabled': False}) is False

    def test_empty_content_inactive(self):
        assert of.is_active({'title': '', 'description': ''}) is False

    def test_end_date_inclusive(self):
        assert of.is_active({'description': 'x', 'ends_at': _d(0)}) is True  # ends today = still live


class TestActiveOffers:
    class _Client:
        def __init__(self, offers):
            self.active_offers = offers

    def test_filters_and_caps(self):
        c = self._Client([
            {'title': 'A', 'description': 'a'},                       # live
            {'title': 'B', 'description': 'b', 'ends_at': _d(-1)},     # expired
            {'title': 'C', 'description': 'c', 'enabled': False},      # off
            {'title': 'D', 'description': 'd'},                        # live
            {'title': 'E', 'description': 'e'},                        # live
            {'title': 'F', 'description': 'f'},                        # live (over cap of 3)
        ])
        live = of.active_offers(c)
        titles = [o['title'] for o in live]
        assert 'B' not in titles and 'C' not in titles
        assert len(live) == of.MAX_ACTIVE == 3

    def test_empty(self):
        assert of.active_offers(self._Client([])) == []
        assert of.active_offers(self._Client(None)) == []


class TestFormatBlock:
    def test_empty_returns_blank(self):
        assert of.format_offers_block([]) == ''

    def test_includes_title_desc_link_end(self):
        block = of.format_offers_block([{
            'type': 'sale', 'title': 'Summer Sale', 'description': '20% off',
            'link': 'https://s.com/sale', 'ends_at': '2026-06-30',
        }])
        assert 'ACTIVE OFFERS' in block
        assert 'Summer Sale' in block
        assert '20% off' in block
        assert 'https://s.com/sale' in block
        assert 'ends 2026-06-30' in block
        assert 'NEVER invent' in block

    def test_falls_back_to_type_when_no_title(self):
        block = of.format_offers_block([{'type': 'free_shipping', 'description': 'over $50'}])
        assert 'Free Shipping' in block

    def test_non_string_fields_do_not_crash(self):
        # Malformed JSON must never crash and silently kill all offers.
        bad = {'title': 123, 'description': ['a'], 'link': 5, 'type': 99, 'ends_at': 20260630}
        assert of.is_active(bad) is True  # title 123 -> '123' is truthy content
        block = of.format_offers_block([bad])
        assert 'ACTIVE OFFERS' in block


@pytest.mark.django_db
class TestSerializer:
    def test_round_trip(self, tenant_client, client_obj):
        payload = {'active_offers': [
            {'id': 'o1', 'type': 'sale', 'title': 'X', 'description': 'd', 'link': 'https://s.com', 'starts_at': '2026-06-01', 'ends_at': '2026-06-30', 'enabled': True},
        ]}
        resp = tenant_client.patch(f'/api/admin/clients/{client_obj.id}/', payload, format='json')
        assert resp.status_code == 200
        client_obj.refresh_from_db()
        assert len(client_obj.active_offers) == 1
        assert client_obj.active_offers[0]['title'] == 'X'
