"""
QA Phase 04 regression tests — pagination, channel filter, kanban states,
page-view analytics, visitor totals, inline lead capture, and takeover media.
"""
import io
import pytest
from datetime import timedelta
from django.utils import timezone

from chat.models import ChatSession, ChatAttachment
from analytics.models import AnalyticEvent


def sessions_url(cid):
    return f'/api/admin/clients/{cid}/sessions/'


def analytics_url(cid):
    return f'/api/admin/clients/{cid}/analytics/'


def visitors_url(cid):
    return f'/api/admin/clients/{cid}/visitors/'


# ─── Pagination (#4, #6) ──────────────────────────────────────────────────────

@pytest.mark.django_db
class TestSessionPagination:
    def _seed(self, client_obj, n):
        for i in range(n):
            ChatSession.objects.create(client=client_obj, visitor_id=f'v-{i}', channel='website', message_count=1)

    def test_paginated_shape(self, tenant_client, client_obj):
        self._seed(client_obj, 3)
        data = tenant_client.get(sessions_url(client_obj.id)).json()
        assert set(['results', 'count', 'next', 'offset', 'limit']).issubset(data.keys())
        assert data['count'] == 3

    def test_limit_and_next_offset(self, tenant_client, client_obj):
        self._seed(client_obj, 5)
        data = tenant_client.get(sessions_url(client_obj.id) + '?limit=2').json()
        assert len(data['results']) == 2
        assert data['count'] == 5
        assert data['next'] == 2

    def test_offset_no_duplicates(self, tenant_client, client_obj):
        self._seed(client_obj, 5)
        p1 = tenant_client.get(sessions_url(client_obj.id) + '?limit=2&offset=0').json()['results']
        p2 = tenant_client.get(sessions_url(client_obj.id) + '?limit=2&offset=2').json()['results']
        ids1 = {s['session_id'] for s in p1}
        ids2 = {s['session_id'] for s in p2}
        assert not (ids1 & ids2)  # no overlap


# ─── Channel filter (#1) ──────────────────────────────────────────────────────

@pytest.mark.django_db
class TestChannelFilter:
    def test_filter_by_channel(self, tenant_client, client_obj):
        ChatSession.objects.create(client=client_obj, visitor_id='web1', channel='website', message_count=1)
        ChatSession.objects.create(client=client_obj, visitor_id='wa1', channel='whatsapp', message_count=1)
        ChatSession.objects.create(client=client_obj, visitor_id='ig1', channel='instagram', message_count=1)

        wa = tenant_client.get(sessions_url(client_obj.id) + '?channel=whatsapp').json()
        assert wa['count'] == 1
        assert wa['results'][0]['channel'] == 'whatsapp'

        ig = tenant_client.get(sessions_url(client_obj.id) + '?channel=instagram').json()
        assert ig['count'] == 1

        all_c = tenant_client.get(sessions_url(client_obj.id) + '?channel=all').json()
        assert all_c['count'] == 3


# ─── Heat filter composes with pagination (SQL, not post-slice) ───────────────

@pytest.mark.django_db
class TestHeatFilter:
    def test_min_heat_in_sql(self, tenant_client, client_obj):
        hot = ChatSession.objects.create(client=client_obj, visitor_id='hot', channel='website', message_count=1)
        ChatSession.objects.filter(pk=hot.pk).update(current_intent_ema=0.9, current_budget_ema=0.9, current_urgency_ema=0.9)
        ChatSession.objects.create(client=client_obj, visitor_id='cold', channel='website', message_count=1)

        data = tenant_client.get(sessions_url(client_obj.id) + '?min_heat=70').json()
        assert data['count'] == 1
        assert data['results'][0]['visitor_id'] == 'hot'


# ─── Page views from AnalyticEvent (#11) ──────────────────────────────────────

@pytest.mark.django_db
class TestPageViewAnalytics:
    def test_page_views_counted_from_events(self, tenant_client, client_obj):
        for i in range(4):
            AnalyticEvent.objects.create(client=client_obj, session_id=f's{i}', event_type='page_view', page_url='https://x.com/p')
        AnalyticEvent.objects.create(client=client_obj, session_id='s9', event_type='pricing_visit')
        AnalyticEvent.objects.create(client=client_obj, session_id='s9', event_type='exit_intent')

        data = tenant_client.get(analytics_url(client_obj.id) + '?period=all').json()
        ev = data['analytics_events']
        assert ev['page_views'] == 4
        assert ev['pricing_page_visits'] == 1
        assert ev['exit_intent_count'] == 1

    def test_top_pages(self, tenant_client, client_obj):
        for _ in range(3):
            AnalyticEvent.objects.create(client=client_obj, session_id='s', event_type='page_view', page_url='https://x.com/popular')
        AnalyticEvent.objects.create(client=client_obj, session_id='s', event_type='page_view', page_url='https://x.com/rare')
        data = tenant_client.get(analytics_url(client_obj.id) + '?period=all').json()
        assert data['top_pages'][0]['page'].endswith('/popular')
        assert data['top_pages'][0]['views'] == 3


# ─── Lead-stage metrics (#9) ──────────────────────────────────────────────────

@pytest.mark.django_db
class TestLeadMetrics:
    def test_lead_stage_breakdown(self, tenant_client, client_obj):
        ChatSession.objects.create(client=client_obj, visitor_id='c1', channel='website', message_count=2,
                                   lead_email='a@b.com', lead_phone='+94771234567', kanban_state='CONVERTED')
        ChatSession.objects.create(client=client_obj, visitor_id='q1', channel='website', message_count=2,
                                   kanban_state='QUALIFIED')
        data = tenant_client.get(analytics_url(client_obj.id) + '?period=all').json()
        leads = data['leads']
        assert leads['converted']['value'] == 1
        assert leads['captured']['value'] == 1
        assert 'lead_funnel' in data


# ─── Visitor total count (#7) ─────────────────────────────────────────────────

@pytest.mark.django_db
class TestVisitorCount:
    def test_total_count_present(self, tenant_client, client_obj):
        data = tenant_client.get(visitors_url(client_obj.id)).json()
        assert 'total_count' in data
        assert 'next' in data


# ─── All-time / custom date params ────────────────────────────────────────────

@pytest.mark.django_db
class TestDateParams:
    def test_all_time_returns_everything(self, tenant_client, client_obj):
        old = ChatSession.objects.create(client=client_obj, visitor_id='old', channel='website', message_count=1)
        ChatSession.objects.filter(pk=old.pk).update(created_at=timezone.now() - timedelta(days=400))
        data = tenant_client.get(analytics_url(client_obj.id) + '?period=all').json()
        assert data['total_sessions']['value'] >= 1


# ─── Takeover media upload (#3) ───────────────────────────────────────────────

@pytest.mark.django_db
class TestTakeoverMedia:
    def test_upload_image_attachment(self, tenant_client, client_obj, chat_session):
        from django.core.files.uploadedfile import SimpleUploadedFile
        img = SimpleUploadedFile('pic.png', b'\x89PNG\r\n\x1a\n' + b'0' * 50, content_type='image/png')
        url = f'/api/admin/sessions/{chat_session.session_id}/upload/'
        resp = tenant_client.post(url, {'file': img}, format='multipart')
        assert resp.status_code == 201, resp.content
        body = resp.json()
        assert body['kind'] == 'image'
        assert body['url']
        assert ChatAttachment.objects.filter(session_id=str(chat_session.session_id)).count() == 1

    def test_send_message_with_attachment(self, tenant_client, client_obj, chat_session):
        url = f'/api/admin/sessions/{chat_session.session_id}/send/'
        atts = [{'url': '/media/chat_attachments/x/pic.png', 'kind': 'image', 'name': 'pic.png', 'mime': 'image/png', 'size': 10}]
        resp = tenant_client.post(url, {'message': '', 'attachments': atts}, format='json')
        assert resp.status_code == 200, resp.content
        chat_session.refresh_from_db()
        last = chat_session.chat_history[-1]
        assert last['attachments'][0]['kind'] == 'image'

    def test_widget_history_restore_includes_attachments(self, anon_client, chat_session):
        """The visitor widget restores history via /api/chat/session/<id>/messages/.
        Attachment-only and attachment-bearing messages must survive restore (QA #3)."""
        chat_session.chat_history = [
            {'role': 'user', 'message': 'hi'},
            {'role': 'ai', 'message': 'pic for you', 'source': 'admin',
             'attachments': [{'url': 'https://growmiq.io/media/x.png', 'kind': 'image', 'name': 'x.png'}]},
            {'role': 'ai', 'message': '', 'source': 'admin',
             'attachments': [{'url': 'https://growmiq.io/media/v.webm', 'kind': 'audio', 'name': 'v.webm'}]},
        ]
        chat_session.save(update_fields=['chat_history'])
        resp = anon_client.get(f'/api/chat/session/{chat_session.session_id}/messages/')
        assert resp.status_code == 200
        msgs = resp.json()['messages']
        # All three survive (incl. the empty-text voice note), with attachments intact.
        assert len(msgs) == 3
        assert msgs[1]['attachments'][0]['kind'] == 'image'
        assert msgs[2]['attachments'][0]['kind'] == 'audio'
        assert msgs[2]['message'] == ''


# ─── Inline contact capture (#13) ─────────────────────────────────────────────

class TestInlineExtraction:
    def test_extract_email(self):
        from chat.phone_utils import extract_email
        assert extract_email('reach me at Jo.Doe@Example.com please') == 'jo.doe@example.com'
        assert extract_email('no email here') is None
        assert extract_email('version v1.0 released') is None

    def test_extract_phone_lk(self):
        from chat.phone_utils import extract_phone
        assert extract_phone('call me on 077 123 4567', 'LK') == '+94771234567'

    def test_extract_phone_international(self):
        from chat.phone_utils import extract_phone
        # 8–15 digit international fallback for non-LK tenants.
        assert extract_phone('reach me at +1 415 555 1234', 'US') is not None

    def test_no_false_positive_on_short_numbers(self):
        from chat.phone_utils import extract_phone
        assert extract_phone('I want 5 units by 2024', 'LK') is None
