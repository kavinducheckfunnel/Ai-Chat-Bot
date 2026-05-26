"""
Tests for the image-upload chat path.

Covers:
  • _parse_image_data_uri — MIME sniffing and fallbacks
  • generate_ai_response in image mode — prose reply parsing, JSON not required,
    image marker persisted to chat_history
  • _invoke_with_fallback — vision_required selects the vision fallback chain
  • REST chat endpoint forwards image_data; respects image_input_enabled flag
"""
import json
from unittest.mock import MagicMock, patch

import pytest

from chat.ai_service import (
    _parse_image_data_uri,
    _PLATFORM_FALLBACK_MODELS,
    _PLATFORM_VISION_FALLBACK_MODELS,
)
from chat.models import ChatSession


# Tiny valid base64 of an 8-byte PNG header — enough for shape tests; the
# LLM is mocked everywhere so the actual bytes never get decoded by Pillow.
_PNG_BASE64 = 'iVBORw0KGgo='
_JPEG_BASE64 = '/9j/4AAQ'
_WEBP_BASE64 = 'UklGRg=='

CHAT_URL = '/api/chat/message/'


# ─── _parse_image_data_uri ───────────────────────────────────────────────────

class TestParseImageDataUri:
    def test_png_data_uri(self):
        mime, payload = _parse_image_data_uri(f'data:image/png;base64,{_PNG_BASE64}')
        assert mime == 'image/png'
        assert payload == _PNG_BASE64

    def test_jpeg_data_uri(self):
        mime, payload = _parse_image_data_uri(f'data:image/jpeg;base64,{_JPEG_BASE64}')
        assert mime == 'image/jpeg'
        assert payload == _JPEG_BASE64

    def test_webp_data_uri(self):
        mime, payload = _parse_image_data_uri(f'data:image/webp;base64,{_WEBP_BASE64}')
        assert mime == 'image/webp'

    def test_gif_data_uri(self):
        mime, payload = _parse_image_data_uri('data:image/gif;base64,R0lGOD==')
        assert mime == 'image/gif'

    def test_unknown_mime_falls_back_to_jpeg(self):
        # Crafted "image/bmp" — not in the allowlist; we don't pass bogus
        # MIMEs to the model.
        mime, _ = _parse_image_data_uri('data:image/bmp;base64,Qk0=')
        assert mime == 'image/jpeg'

    def test_raw_base64_without_prefix(self):
        mime, payload = _parse_image_data_uri(_PNG_BASE64)
        assert mime == 'image/jpeg'
        assert payload == _PNG_BASE64

    def test_empty_input(self):
        mime, payload = _parse_image_data_uri('')
        assert mime == 'image/jpeg'
        assert payload == ''

    def test_malformed_data_uri_no_comma(self):
        mime, payload = _parse_image_data_uri('data:image/png;base64NoComma')
        assert mime == 'image/jpeg'  # falls through to default


# ─── Vision fallback chain shape ─────────────────────────────────────────────

class TestVisionFallbackChain:
    def test_vision_chain_excludes_text_only_llama(self):
        assert 'meta-llama/llama-3.3-70b-instruct:free' not in _PLATFORM_VISION_FALLBACK_MODELS

    def test_text_chain_unchanged(self):
        # Sanity: regression test in case someone copy-pastes the vision
        # chain over the text one by accident.
        assert 'meta-llama/llama-3.3-70b-instruct:free' in _PLATFORM_FALLBACK_MODELS


# ─── generate_ai_response in image mode ──────────────────────────────────────

@pytest.mark.django_db
class TestGenerateAiResponseImageMode:
    def _mock_invocation(self, content):
        """Patch the LLM call layer + embedding model with stubs."""
        fake_result = MagicMock(content=content)
        embedder = MagicMock()
        embedder.embed_query.return_value = [0.0] * 1024
        return fake_result, embedder

    def test_image_mode_accepts_prose_reply(self, chat_session):
        from chat.ai_service import generate_ai_response
        fake_result, embedder = self._mock_invocation(
            'I see a red T-shirt — size M is available in our store.'
        )
        with patch('chat.ai_service._invoke_with_fallback', return_value=fake_result), \
             patch('chat.ai_service.get_embeddings_model', return_value=embedder):
            result = generate_ai_response(
                chat_session, 'what color is this?',
                behavior_matrix={},
                image_data=f'data:image/png;base64,{_PNG_BASE64}',
            )
        assert 'red T-shirt' in result['reply_text']
        # Fallback "trouble right now" must NOT fire on a prose reply.
        assert 'trouble right now' not in result['reply_text'].lower()
        # Schema is still populated so downstream code doesn't KeyError.
        assert 'intent_score' in result
        assert 'budget_score' in result
        assert 'urgency_score' in result

    def test_image_mode_strips_accidental_code_fence(self, chat_session):
        from chat.ai_service import generate_ai_response
        fake_result, embedder = self._mock_invocation(
            '```\nIt looks like a sneaker, size 10.\n```'
        )
        with patch('chat.ai_service._invoke_with_fallback', return_value=fake_result), \
             patch('chat.ai_service.get_embeddings_model', return_value=embedder):
            result = generate_ai_response(
                chat_session, '',
                behavior_matrix={},
                image_data=f'data:image/jpeg;base64,{_JPEG_BASE64}',
            )
        assert 'sneaker' in result['reply_text']
        assert '```' not in result['reply_text']

    def test_image_mode_routes_vision_required(self, chat_session):
        """The LLM call must be made with vision_required=True."""
        from chat.ai_service import generate_ai_response
        fake_result, embedder = self._mock_invocation('It is a kettle.')
        with patch('chat.ai_service._invoke_with_fallback', return_value=fake_result) as mock_inv, \
             patch('chat.ai_service.get_embeddings_model', return_value=embedder):
            generate_ai_response(
                chat_session, 'what is this?',
                behavior_matrix={},
                image_data=f'data:image/png;base64,{_PNG_BASE64}',
            )
        # _invoke_with_fallback called once with vision_required=True
        assert mock_inv.call_count == 1
        kwargs = mock_inv.call_args.kwargs
        assert kwargs.get('vision_required') is True

    def test_text_mode_routes_vision_required_false(self, chat_session):
        from chat.ai_service import generate_ai_response
        json_reply = json.dumps({
            'reply_text': 'Hi!', 'intent_score': 0.5,
            'budget_score': 0.5, 'urgency_score': 0.5,
        })
        fake_result, embedder = self._mock_invocation(json_reply)
        with patch('chat.ai_service._invoke_with_fallback', return_value=fake_result) as mock_inv, \
             patch('chat.ai_service.get_embeddings_model', return_value=embedder):
            generate_ai_response(chat_session, 'hello', behavior_matrix={})
        kwargs = mock_inv.call_args.kwargs
        assert kwargs.get('vision_required', False) is False

    def test_image_marker_persisted_to_history(self, chat_session):
        from chat.ai_service import generate_ai_response
        fake_result, embedder = self._mock_invocation('Got it.')
        with patch('chat.ai_service._invoke_with_fallback', return_value=fake_result), \
             patch('chat.ai_service.get_embeddings_model', return_value=embedder):
            generate_ai_response(
                chat_session, 'what color?',
                behavior_matrix={},
                image_data=f'data:image/png;base64,{_PNG_BASE64}',
            )
        chat_session.refresh_from_db()
        user_msgs = [m for m in chat_session.chat_history if m['role'] == 'user']
        assert any('[image attached]' in m['message'] for m in user_msgs)

    def test_image_with_no_text_still_records_marker(self, chat_session):
        from chat.ai_service import generate_ai_response
        fake_result, embedder = self._mock_invocation('That is a wallet.')
        with patch('chat.ai_service._invoke_with_fallback', return_value=fake_result), \
             patch('chat.ai_service.get_embeddings_model', return_value=embedder):
            generate_ai_response(
                chat_session, '',
                behavior_matrix={},
                image_data=f'data:image/png;base64,{_PNG_BASE64}',
            )
        chat_session.refresh_from_db()
        last_user = [m for m in chat_session.chat_history if m['role'] == 'user'][-1]
        assert last_user['message'] == '[image attached]'

    def test_base64_payload_not_stored_in_history(self, chat_session):
        """Payload would balloon the row size — we keep only the marker."""
        from chat.ai_service import generate_ai_response
        huge_b64 = 'A' * 1000
        fake_result, embedder = self._mock_invocation('Replied.')
        with patch('chat.ai_service._invoke_with_fallback', return_value=fake_result), \
             patch('chat.ai_service.get_embeddings_model', return_value=embedder):
            generate_ai_response(
                chat_session, 'what?',
                behavior_matrix={},
                image_data=f'data:image/png;base64,{huge_b64}',
            )
        chat_session.refresh_from_db()
        serialised = json.dumps(chat_session.chat_history)
        assert huge_b64 not in serialised


# ─── REST endpoint /api/chat/message/ ────────────────────────────────────────

@pytest.mark.django_db
class TestRestChatImage:
    def _mock(self, *, reply='Ok.'):
        fake_result = MagicMock(content=reply)
        embedder = MagicMock()
        embedder.embed_query.return_value = [0.0] * 1024
        return fake_result, embedder

    def test_image_data_forwarded(self, anon_client, chat_session, client_obj):
        # Image input must be enabled or it gets stripped.
        client_obj.image_input_enabled = True
        client_obj.save()
        chat_session.client = client_obj
        chat_session.save()

        fake_result, embedder = self._mock()
        with patch('chat.ai_service._invoke_with_fallback', return_value=fake_result) as mock_inv, \
             patch('chat.ai_service.get_embeddings_model', return_value=embedder):
            resp = anon_client.post(CHAT_URL, {
                'session_id': str(chat_session.session_id),
                'message': 'what is this?',
                'image_data': f'data:image/png;base64,{_PNG_BASE64}',
            }, format='json')
        assert resp.status_code == 200
        # LLM call was made — and with vision_required=True because image was forwarded.
        assert mock_inv.called
        assert mock_inv.call_args.kwargs.get('vision_required') is True

    def test_image_only_message_accepted(self, anon_client, chat_session, client_obj):
        client_obj.image_input_enabled = True
        client_obj.save()
        chat_session.client = client_obj
        chat_session.save()

        fake_result, embedder = self._mock(reply='Looks like a backpack.')
        with patch('chat.ai_service._invoke_with_fallback', return_value=fake_result), \
             patch('chat.ai_service.get_embeddings_model', return_value=embedder):
            resp = anon_client.post(CHAT_URL, {
                'session_id': str(chat_session.session_id),
                # No message at all — image is the message
                'image_data': f'data:image/png;base64,{_PNG_BASE64}',
            }, format='json')
        assert resp.status_code == 200
        assert 'backpack' in resp.json()['reply_text']

    def test_image_stripped_when_feature_disabled(self, anon_client, chat_session, client_obj):
        client_obj.image_input_enabled = False
        client_obj.save()
        chat_session.client = client_obj
        chat_session.save()

        json_reply = json.dumps({
            'reply_text': 'Hi!', 'intent_score': 0.5,
            'budget_score': 0.5, 'urgency_score': 0.5,
        })
        fake_result, embedder = self._mock(reply=json_reply)
        with patch('chat.ai_service._invoke_with_fallback', return_value=fake_result) as mock_inv, \
             patch('chat.ai_service.get_embeddings_model', return_value=embedder):
            anon_client.post(CHAT_URL, {
                'session_id': str(chat_session.session_id),
                'message': 'look at this',
                'image_data': f'data:image/png;base64,{_PNG_BASE64}',
            }, format='json')
        # When stripped, vision_required must be False — we're back in text mode.
        assert mock_inv.call_args.kwargs.get('vision_required') is False

    def test_no_session_id_rejected(self, anon_client):
        resp = anon_client.post(CHAT_URL, {
            'message': 'hi',
        }, format='json')
        assert resp.status_code == 400
