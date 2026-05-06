"""
Tests for chat API endpoints:
  POST /api/chat/message/
  GET  /api/chat/widget-config/{uuid}/
  POST /api/chat/trigger/
  POST /api/chat/lead/
  GET  /api/chat/product/{id}/
"""
import uuid
import pytest
from unittest.mock import patch, MagicMock
from rest_framework.test import APIClient

from chat.models import ChatSession
from users.models import Client


CHAT_URL = '/api/chat/message/'
TRIGGER_URL = '/api/chat/trigger/'
LEAD_URL = '/api/chat/lead/'


def widget_config_url(client_id):
    return f'/api/chat/widget-config/{client_id}/'


def product_url(product_id):
    return f'/api/chat/product/{product_id}/'


AI_MOCK_RESPONSE = {
    'reply_text': 'Hello! How can I help you today?',
    'action': None,
    'product_suggestions': [],
}


# ─── Chat Message ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestChatMessage:
    @patch('chat.views.generate_ai_response', return_value=AI_MOCK_RESPONSE)
    def test_message_creates_session(self, mock_ai, anon_client, client_obj):
        session_id = str(uuid.uuid4())
        resp = anon_client.post(CHAT_URL, {
            'session_id': session_id,
            'message': 'Hello there',
        }, format='json')
        assert resp.status_code == 200
        assert resp.json()['reply_text'] == AI_MOCK_RESPONSE['reply_text']
        assert ChatSession.objects.filter(session_id=session_id).exists()

    @patch('chat.views.generate_ai_response', return_value=AI_MOCK_RESPONSE)
    def test_message_continues_existing_session(self, mock_ai, anon_client, chat_session):
        resp = anon_client.post(CHAT_URL, {
            'session_id': str(chat_session.session_id),
            'message': 'Tell me more',
        }, format='json')
        assert resp.status_code == 200
        mock_ai.assert_called_once()

    def test_message_missing_session_id(self, anon_client):
        resp = anon_client.post(CHAT_URL, {'message': 'Hi'}, format='json')
        assert resp.status_code == 400
        assert 'session_id' in resp.json().get('error', '').lower()

    def test_message_missing_message_body(self, anon_client):
        resp = anon_client.post(CHAT_URL, {'session_id': str(uuid.uuid4())}, format='json')
        assert resp.status_code == 400

    @patch('chat.views.generate_ai_response', return_value=AI_MOCK_RESPONSE)
    def test_message_quota_exceeded_returns_200(self, mock_ai, anon_client, client_obj, tenant_user, free_plan):
        # Exhaust message quota
        tp = tenant_user.tenant_profile
        tp.messages_this_month = free_plan.max_messages_per_month
        tp.save()

        session = ChatSession.objects.create(
            client=client_obj,
            visitor_id='quota-test-visitor',
        )
        resp = anon_client.post(CHAT_URL, {
            'session_id': str(session.session_id),
            'message': 'Am I blocked?',
        }, format='json')
        # Widget still renders — returns 200 with quota message
        assert resp.status_code == 200
        assert 'quota_exceeded' in resp.json().get('error', '')
        mock_ai.assert_not_called()

    @patch('chat.views.generate_ai_response', return_value=AI_MOCK_RESPONSE)
    def test_message_increments_usage_counter(self, mock_ai, anon_client, chat_session, tenant_user):
        tp = tenant_user.tenant_profile
        initial = tp.messages_this_month
        anon_client.post(CHAT_URL, {
            'session_id': str(chat_session.session_id),
            'message': 'Hello',
        }, format='json')
        tp.refresh_from_db()
        assert tp.messages_this_month == initial + 1

    @patch('chat.views.generate_ai_response', return_value=AI_MOCK_RESPONSE)
    def test_message_no_client_no_quota(self, mock_ai, anon_client):
        """Session with no client attached has no tenant quota — should pass."""
        session_id = str(uuid.uuid4())
        resp = anon_client.post(CHAT_URL, {
            'session_id': session_id,
            'message': 'No client attached',
        }, format='json')
        assert resp.status_code == 200


# ─── Widget Config ────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestWidgetConfig:
    def test_widget_config_valid_client(self, anon_client, client_obj):
        resp = anon_client.get(widget_config_url(client_obj.id))
        assert resp.status_code == 200
        data = resp.json()
        assert data['chatbot_name'] == client_obj.chatbot_name
        assert data['chatbot_color'] == client_obj.chatbot_color
        assert 'voice_input_enabled' in data
        assert 'image_input_enabled' in data

    def test_widget_config_invalid_uuid(self, anon_client):
        resp = anon_client.get(widget_config_url(uuid.uuid4()))
        assert resp.status_code == 200
        # Returns sensible defaults (not 404) so widget still loads
        assert resp.json()['chatbot_name'] == 'AI Assistant'

    def test_widget_config_inactive_client(self, anon_client, client_obj):
        client_obj.is_active = False
        client_obj.save()
        resp = anon_client.get(widget_config_url(client_obj.id))
        assert resp.status_code == 200
        # Falls back to defaults for inactive clients
        assert resp.json()['chatbot_name'] == 'AI Assistant'


# ─── FOMO Trigger ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestTriggerEvent:
    @patch('chat.views.async_to_sync')
    def test_trigger_exit_intent(self, mock_async, anon_client, chat_session):
        chat_session.client.fomo_offer_text = 'Special offer!'
        chat_session.client.discount_code = 'SAVE20'
        chat_session.client.save()

        resp = anon_client.post(TRIGGER_URL, {
            'session_id': str(chat_session.session_id),
            'client_id': str(chat_session.client.id),
            'trigger_type': 'exit_intent',
        }, format='json')
        assert resp.status_code == 200
        assert resp.json()['status'] == 'sent'

        chat_session.refresh_from_db()
        assert chat_session.closing_triggered is True

    @patch('chat.views.async_to_sync')
    def test_trigger_already_fired_ignored(self, mock_async, anon_client, chat_session):
        chat_session.closing_triggered = True
        chat_session.save()
        resp = anon_client.post(TRIGGER_URL, {
            'session_id': str(chat_session.session_id),
            'trigger_type': 'exit_intent',
        }, format='json')
        assert resp.status_code == 200
        assert resp.json()['status'] == 'ignored'
        assert resp.json()['reason'] == 'already triggered'

    def test_trigger_missing_session_id(self, anon_client):
        resp = anon_client.post(TRIGGER_URL, {'trigger_type': 'exit_intent'}, format='json')
        assert resp.status_code == 400

    @patch('chat.views.async_to_sync')
    def test_trigger_takeover_active_ignored(self, mock_async, anon_client, chat_session):
        chat_session.takeover_active = True
        chat_session.save()
        resp = anon_client.post(TRIGGER_URL, {
            'session_id': str(chat_session.session_id),
            'trigger_type': 'exit_intent',
        }, format='json')
        assert resp.json()['status'] == 'ignored'
        assert resp.json()['reason'] == 'takeover active'


# ─── Lead Capture ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestCaptureLead:
    @patch('chat.utils.fire_slack_notification', return_value=None)
    @patch('chat.utils.fire_outbound_webhook', return_value=None)
    def test_capture_lead_valid(self, mock_wh, mock_slack, anon_client, chat_session):
        resp = anon_client.post(LEAD_URL, {
            'session_id': str(chat_session.session_id),
            'email': 'lead@example.com',
            'phone': '+1234567890',
        }, format='json')
        assert resp.status_code == 200
        assert resp.json()['status'] == 'saved'
        chat_session.refresh_from_db()
        assert chat_session.lead_email == 'lead@example.com'
        assert chat_session.lead_phone == '+1234567890'

    def test_capture_lead_missing_email(self, anon_client, chat_session):
        resp = anon_client.post(LEAD_URL, {
            'session_id': str(chat_session.session_id),
        }, format='json')
        assert resp.status_code == 400

    def test_capture_lead_missing_session(self, anon_client):
        resp = anon_client.post(LEAD_URL, {
            'session_id': str(uuid.uuid4()),
            'email': 'nobody@example.com',
        }, format='json')
        assert resp.status_code == 404

    def test_capture_lead_missing_session_id(self, anon_client):
        resp = anon_client.post(LEAD_URL, {'email': 'x@x.com'}, format='json')
        assert resp.status_code == 400


# ─── Product Detail ───────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestProductDetail:
    def test_product_not_found(self, anon_client):
        resp = anon_client.get(product_url('nonexistent_product'))
        assert resp.status_code == 404

    def test_product_found(self, anon_client, client_obj):
        from scraper.models import DocumentChunk
        DocumentChunk.objects.create(
            client=client_obj,
            product_id='prod_001',
            content='Blue Widget\nA beautiful blue widget.\n$29.99',
            source_url='https://teststore.com/products/blue-widget',
            metadata={'platform': 'shopify', 'price': '$29.99'},
            embedding=[0.0] * 1024,
        )
        resp = anon_client.get(product_url('prod_001'))
        assert resp.status_code == 200
        data = resp.json()
        assert data['product_id'] == 'prod_001'
        assert 'title' in data
        assert 'price' in data
