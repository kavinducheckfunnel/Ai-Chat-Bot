"""Tests for the public widget transcript-restore endpoint (Part A1)."""
import uuid
import pytest

from chat.models import ChatSession


def _url(sid):
    return f'/api/chat/session/{sid}/messages/'


@pytest.mark.django_db
class TestSessionMessages:
    def test_returns_transcript(self, anon_client, client_obj):
        s = ChatSession.objects.create(
            client=client_obj, visitor_id='v1', message_count=2,
            chat_history=[
                {'role': 'user', 'message': 'hi'},
                {'role': 'ai', 'message': 'Hello! How can I help?', 'source': 'ai'},
            ],
        )
        resp = anon_client.get(_url(s.session_id))
        assert resp.status_code == 200
        body = resp.json()
        assert body['message_count'] == 2
        assert len(body['messages']) == 2
        assert body['messages'][0] == {'role': 'user', 'message': 'hi', 'source': ''}
        assert body['messages'][1]['message'] == 'Hello! How can I help?'

    def test_unknown_session_returns_empty(self, anon_client):
        resp = anon_client.get(_url(uuid.uuid4()))
        assert resp.status_code == 200
        assert resp.json() == {'messages': [], 'message_count': 0}

    def test_malformed_id_returns_empty(self, anon_client):
        resp = anon_client.get(_url('not-a-uuid'))
        assert resp.status_code == 200
        assert resp.json()['messages'] == []

    def test_limit_caps_to_last_n(self, anon_client, client_obj):
        history = [{'role': 'ai', 'message': f'm{i}'} for i in range(80)]
        s = ChatSession.objects.create(client=client_obj, visitor_id='v', chat_history=history, message_count=80)
        resp = anon_client.get(_url(s.session_id) + '?limit=10')
        msgs = resp.json()['messages']
        assert len(msgs) == 10
        assert msgs[-1]['message'] == 'm79'
        assert msgs[0]['message'] == 'm70'

    def test_default_limit_is_50(self, anon_client, client_obj):
        history = [{'role': 'ai', 'message': f'm{i}'} for i in range(80)]
        s = ChatSession.objects.create(client=client_obj, visitor_id='v', chat_history=history)
        resp = anon_client.get(_url(s.session_id))
        assert len(resp.json()['messages']) == 50

    def test_skips_empty_messages(self, anon_client, client_obj):
        s = ChatSession.objects.create(
            client=client_obj, visitor_id='v',
            chat_history=[{'role': 'ai', 'message': ''}, {'role': 'ai', 'message': 'real'}],
        )
        msgs = resp = anon_client.get(_url(s.session_id)).json()['messages']
        assert len(msgs) == 1
        assert msgs[0]['message'] == 'real'
