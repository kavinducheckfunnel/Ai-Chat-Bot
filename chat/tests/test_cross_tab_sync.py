"""
Tests for cross-tab live sync (Part 1).

Two tabs connect to the SAME chat session. A message from tab 1 must be fanned
out so tab 2 receives BOTH the visitor's message (user_message relay) and the
AI reply (ai_message relay), each carrying a msg_id for dedupe.

Written as SYNC tests that drive the async WebSocket flow via async_to_sync,
so no pytest-asyncio dependency is required.
"""
import json
from unittest.mock import patch

import pytest
from asgiref.sync import async_to_sync
from channels.testing import WebsocketCommunicator

from checkfunnel.asgi import application
from chat.models import ChatSession


def _ws_url(client_id, session_id):
    return f'/ws/chat/{client_id}/{session_id}/'


async def _run_fanout(client_id, sid):
    fake_reply = {'reply_text': 'Hi there!', 'suggested_product_id': None, 'quick_replies': []}
    with patch('chat.consumers.generate_ai_response', return_value=fake_reply):
        tab1 = WebsocketCommunicator(application, _ws_url(client_id, sid))
        tab2 = WebsocketCommunicator(application, _ws_url(client_id, sid))
        c1, _ = await tab1.connect()
        c2, _ = await tab2.connect()
        assert c1 and c2

        await tab1.send_to(text_data=json.dumps({
            'message': 'hello', 'msg_id': 'u_abc', 'behavior_matrix': {}, 'page_visits': [],
        }))

        got_user = got_ai = False
        ai_id = ''
        for _ in range(8):
            try:
                d = json.loads(await tab2.receive_from(timeout=3))
            except Exception:
                break
            if d.get('type') == 'user_message' and d.get('message') == 'hello':
                got_user = True
                assert d.get('msg_id') == 'u_abc'
            if d.get('type') == 'ai_message' and d.get('message') == 'Hi there!':
                got_ai = True
                ai_id = d.get('msg_id', '')
            if got_user and got_ai:
                break

        await tab1.disconnect()
        await tab2.disconnect()
        return got_user, got_ai, ai_id


@pytest.mark.django_db(transaction=True)
def test_message_fans_out_to_other_tab(client_obj):
    sid = '11111111-1111-4111-8111-111111111111'
    ChatSession.objects.create(session_id=sid, client=client_obj, visitor_id='v')
    got_user, got_ai, ai_id = async_to_sync(_run_fanout)(str(client_obj.id), sid)
    assert got_user, 'tab 2 should receive the visitor message echo'
    assert got_ai, 'tab 2 should receive the AI reply'
    assert ai_id.startswith('ai_'), 'AI reply must carry a server msg_id for dedupe'
