"""
Tests for omnichannel webhook endpoints:
  GET/POST /api/chat/webhooks/whatsapp/{uuid}/
  GET/POST /api/chat/webhooks/messenger/{uuid}/
  POST     /api/chat/webhooks/telegram/{uuid}/
"""
import uuid
import pytest
from unittest.mock import patch
from rest_framework.test import APIClient

from chat.models import ChatSession


AI_MOCK = {'reply_text': 'Hi from AI!', 'action': None}


def wa_url(client_id):
    return f'/api/chat/webhooks/whatsapp/{client_id}/'


def msg_url(client_id):
    return f'/api/chat/webhooks/messenger/{client_id}/'


def tg_url(client_id):
    return f'/api/chat/webhooks/telegram/{client_id}/'


# ─── WhatsApp ─────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestWhatsAppWebhook:
    def test_verification_valid(self, anon_client, whatsapp_client):
        resp = anon_client.get(wa_url(whatsapp_client.id), {
            'hub.mode': 'subscribe',
            'hub.verify_token': whatsapp_client.whatsapp_verify_token,
            'hub.challenge': 'CHALLENGE_CODE',
        })
        assert resp.status_code == 200
        assert b'CHALLENGE_CODE' in resp.content

    def test_verification_wrong_token(self, anon_client, whatsapp_client):
        resp = anon_client.get(wa_url(whatsapp_client.id), {
            'hub.mode': 'subscribe',
            'hub.verify_token': 'wrong_token',
            'hub.challenge': 'CHALLENGE_CODE',
        })
        assert resp.status_code == 403

    def test_verification_unknown_client(self, anon_client):
        resp = anon_client.get(wa_url(uuid.uuid4()), {
            'hub.mode': 'subscribe',
            'hub.verify_token': 'any',
            'hub.challenge': 'CHALLENGE_CODE',
        })
        assert resp.status_code == 404

    @patch('chat.views._send_whatsapp_reply')
    @patch('chat.views.generate_ai_response', return_value=AI_MOCK)
    def test_incoming_text_message(self, mock_ai, mock_send, anon_client, whatsapp_client):
        payload = {
            'entry': [{
                'changes': [{
                    'value': {
                        'messages': [{
                            'type': 'text',
                            'from': '+1234567890',
                            'text': {'body': 'Hello from WhatsApp'},
                        }]
                    }
                }]
            }]
        }
        resp = anon_client.post(wa_url(whatsapp_client.id), payload, format='json')
        assert resp.status_code == 200
        mock_ai.assert_called_once()
        mock_send.assert_called_once()

        # Verify session created with correct channel
        session = ChatSession.objects.filter(
            client=whatsapp_client, visitor_id='+1234567890', channel='whatsapp'
        ).first()
        assert session is not None

    @patch('chat.views.generate_ai_response', return_value=AI_MOCK)
    def test_non_text_message_ignored(self, mock_ai, anon_client, whatsapp_client):
        payload = {
            'entry': [{
                'changes': [{
                    'value': {
                        'messages': [{
                            'type': 'image',
                            'from': '+1234567890',
                        }]
                    }
                }]
            }]
        }
        resp = anon_client.post(wa_url(whatsapp_client.id), payload, format='json')
        assert resp.status_code == 200
        mock_ai.assert_not_called()

    def test_delivery_receipt_ignored(self, anon_client, whatsapp_client):
        payload = {'entry': [{'changes': [{'value': {'messages': []}}]}]}
        resp = anon_client.post(wa_url(whatsapp_client.id), payload, format='json')
        assert resp.status_code == 200

    @patch('chat.views._send_whatsapp_reply')
    @patch('chat.views.generate_ai_response', return_value=AI_MOCK)
    def test_quota_exceeded_silently_skips(self, mock_ai, mock_send, anon_client, whatsapp_client, tenant_user, free_plan):
        tp = tenant_user.tenant_profile
        tp.messages_this_month = free_plan.max_messages_per_month
        tp.save()

        payload = {
            'entry': [{
                'changes': [{
                    'value': {
                        'messages': [{
                            'type': 'text',
                            'from': '+9999999999',
                            'text': {'body': 'Quota test'},
                        }]
                    }
                }]
            }]
        }
        resp = anon_client.post(wa_url(whatsapp_client.id), payload, format='json')
        assert resp.status_code == 200
        mock_ai.assert_not_called()


# ─── Messenger ────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestMessengerWebhook:
    def test_verification_valid(self, anon_client, messenger_client):
        resp = anon_client.get(msg_url(messenger_client.id), {
            'hub.mode': 'subscribe',
            'hub.verify_token': messenger_client.messenger_verify_token,
            'hub.challenge': 'MESSENGER_CHALLENGE',
        })
        assert resp.status_code == 200
        assert b'MESSENGER_CHALLENGE' in resp.content

    def test_verification_wrong_token(self, anon_client, messenger_client):
        resp = anon_client.get(msg_url(messenger_client.id), {
            'hub.mode': 'subscribe',
            'hub.verify_token': 'wrong',
            'hub.challenge': 'CHALLENGE',
        })
        assert resp.status_code == 403

    @patch('chat.views._send_messenger_reply')
    @patch('chat.views.generate_ai_response', return_value=AI_MOCK)
    def test_incoming_text(self, mock_ai, mock_send, anon_client, messenger_client):
        payload = {
            'entry': [{
                'messaging': [{
                    'sender': {'id': 'psid_abc123'},
                    'message': {'text': 'Hello Messenger!'},
                }]
            }]
        }
        resp = anon_client.post(msg_url(messenger_client.id), payload, format='json')
        assert resp.status_code == 200
        mock_ai.assert_called_once()
        mock_send.assert_called_once()

        session = ChatSession.objects.filter(
            client=messenger_client, visitor_id='psid_abc123', channel='messenger'
        ).first()
        assert session is not None

    def test_attachment_message_ignored(self, anon_client, messenger_client):
        payload = {
            'entry': [{
                'messaging': [{
                    'sender': {'id': 'psid_sticker'},
                    'message': {},  # no 'text' key
                }]
            }]
        }
        resp = anon_client.post(msg_url(messenger_client.id), payload, format='json')
        assert resp.status_code == 200


# ─── Telegram ─────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestTelegramWebhook:
    @patch('chat.views._send_telegram_reply')
    @patch('chat.views.generate_ai_response', return_value=AI_MOCK)
    def test_incoming_text(self, mock_ai, mock_send, anon_client, telegram_client):
        payload = {
            'message': {
                'chat': {'id': 112233},
                'text': 'Hello from Telegram',
            }
        }
        resp = anon_client.post(tg_url(telegram_client.id), payload, format='json')
        assert resp.status_code == 200
        mock_ai.assert_called_once()
        mock_send.assert_called_once()

        session = ChatSession.objects.filter(
            client=telegram_client, visitor_id='112233', channel='telegram'
        ).first()
        assert session is not None

    def test_non_text_update_ignored(self, anon_client, telegram_client):
        payload = {
            'message': {
                'chat': {'id': 112233},
                # no 'text'
                'sticker': {'file_id': 'abc'},
            }
        }
        resp = anon_client.post(tg_url(telegram_client.id), payload, format='json')
        assert resp.status_code == 200

    def test_telegram_disabled(self, anon_client, telegram_client):
        telegram_client.telegram_enabled = False
        telegram_client.save()
        resp = anon_client.post(tg_url(telegram_client.id), {}, format='json')
        assert resp.status_code == 400

    def test_unknown_client(self, anon_client):
        resp = anon_client.post(tg_url(uuid.uuid4()), {}, format='json')
        assert resp.status_code == 404

    @patch('chat.views._send_telegram_reply')
    @patch('chat.views.generate_ai_response', return_value=AI_MOCK)
    def test_session_reuse_within_24h(self, mock_ai, mock_send, anon_client, telegram_client):
        """A second message from same chat_id reuses the existing session."""
        payload = {
            'message': {
                'chat': {'id': 999888},
                'text': 'First message',
            }
        }
        anon_client.post(tg_url(telegram_client.id), payload, format='json')
        anon_client.post(tg_url(telegram_client.id), payload, format='json')

        session_count = ChatSession.objects.filter(
            client=telegram_client, visitor_id='999888'
        ).count()
        assert session_count == 1
