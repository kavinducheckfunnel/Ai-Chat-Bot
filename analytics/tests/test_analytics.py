"""
Tests for analytics endpoints:
  POST /api/analytics/beacon/
"""
import json
import pytest
from rest_framework.test import APIClient

from chat.models import ChatSession


BEACON_URL = '/api/analytics/beacon/'


@pytest.mark.django_db
class TestBeaconReceiver:
    def test_beacon_updates_session_context(self, chat_session):
        client = APIClient()
        payload = {
            'sessionId': str(chat_session.session_id),
            'behaviorMatrix': {
                'pagesViewed': ['/home', '/pricing', '/product'],
                'pricingPageVisits': 2,
                'exitIntentFired': True,
                'scrollDepth': 75,
                'timeOnSite': 120,
            },
        }
        resp = client.post(
            BEACON_URL,
            data=json.dumps(payload),
            content_type='application/json',
        )
        assert resp.status_code == 200
        assert resp.json()['status'] == 'ok'

        chat_session.refresh_from_db()
        ctx = chat_session.behavioral_context
        assert ctx['pages_viewed'] == 3
        assert ctx['pricing_page_visits'] == 2
        assert ctx['exit_intent_triggered'] is True
        assert ctx['scroll_depth'] == 75
        assert ctx['time_on_site'] == 120

    def test_beacon_unknown_session_still_200(self):
        import uuid
        client = APIClient()
        payload = {
            'sessionId': str(uuid.uuid4()),
            'behaviorMatrix': {'scrollDepth': 50},
        }
        resp = client.post(
            BEACON_URL,
            data=json.dumps(payload),
            content_type='application/json',
        )
        assert resp.status_code == 200

    def test_beacon_invalid_json_returns_400(self):
        client = APIClient()
        resp = client.post(
            BEACON_URL,
            data='not json',
            content_type='application/json',
        )
        assert resp.status_code == 400

    def test_beacon_get_method_not_allowed(self):
        client = APIClient()
        resp = client.get(BEACON_URL)
        assert resp.status_code == 405

    def test_beacon_no_session_id_still_ok(self):
        client = APIClient()
        payload = {'behaviorMatrix': {'scrollDepth': 30}}
        resp = client.post(
            BEACON_URL,
            data=json.dumps(payload),
            content_type='application/json',
        )
        assert resp.status_code == 200
