"""
Tests for God View / session management endpoints:
  GET/PATCH  /api/admin/sessions/{uuid}/
  POST /api/admin/sessions/{uuid}/takeover/
  POST /api/admin/sessions/{uuid}/release/
  POST /api/admin/sessions/{uuid}/send/
  GET  /api/admin/sessions/{uuid}/history/
  POST /api/admin/sessions/{uuid}/tags/
"""
import uuid
import pytest
from unittest.mock import patch

from chat.models import ChatSession
from users.models import TenantFeatureOverride


def session_url(session_id):
    return f'/api/admin/sessions/{session_id}/'


def takeover_url(session_id):
    return f'/api/admin/sessions/{session_id}/takeover/'


def release_url(session_id):
    return f'/api/admin/sessions/{session_id}/release/'


def send_url(session_id):
    return f'/api/admin/sessions/{session_id}/send/'


def history_url(session_id):
    return f'/api/admin/sessions/{session_id}/history/'


def tags_url(session_id):
    return f'/api/admin/sessions/{session_id}/tags/'


# ─── Session Detail ───────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestSessionDetail:
    def test_get_own_session(self, tenant_client, chat_session):
        resp = tenant_client.get(session_url(chat_session.session_id))
        assert resp.status_code == 200
        data = resp.json()
        assert str(data['session_id']) == str(chat_session.session_id)
        assert 'heat_score' in data
        assert 'visitor_ip' in data
        assert 'channel' in data

    def test_get_unauthenticated(self, anon_client, chat_session):
        resp = anon_client.get(session_url(chat_session.session_id))
        assert resp.status_code == 401

    def test_get_other_tenants_session(self, tenant_client2, chat_session):
        # chat_session belongs to tenant_user, not tenant_user2
        resp = tenant_client2.get(session_url(chat_session.session_id))
        assert resp.status_code == 404

    def test_get_nonexistent_session(self, tenant_client):
        resp = tenant_client.get(session_url(uuid.uuid4()))
        assert resp.status_code == 404

    def test_patch_kanban_state(self, tenant_client, chat_session):
        resp = tenant_client.patch(session_url(chat_session.session_id), {
            'kanban_state': 'CONVERTED',
        }, format='json')
        assert resp.status_code == 200
        chat_session.refresh_from_db()
        assert chat_session.kanban_state == 'CONVERTED'

    def test_patch_lead_email(self, tenant_client, chat_session):
        resp = tenant_client.patch(session_url(chat_session.session_id), {
            'lead_email': 'updated@example.com',
        }, format='json')
        assert resp.status_code == 200
        chat_session.refresh_from_db()
        assert chat_session.lead_email == 'updated@example.com'

    def test_superadmin_can_get_any_session(self, superadmin_client, chat_session):
        resp = superadmin_client.get(session_url(chat_session.session_id))
        assert resp.status_code == 200


# ─── God View Takeover ────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestSessionTakeover:
    def test_takeover_with_permission(self, tenant_client, tenant_user, chat_session, free_plan):
        resp = tenant_client.post(takeover_url(chat_session.session_id))
        assert resp.status_code == 200
        assert 'Takeover active' in resp.json().get('detail', '')
        chat_session.refresh_from_db()
        assert chat_session.takeover_active is True
        assert chat_session.taken_over_by == tenant_user

    def test_takeover_without_god_view_feature(self, tenant_client, tenant_user, chat_session, free_plan):
        free_plan.allow_god_view = False
        free_plan.save()
        resp = tenant_client.post(takeover_url(chat_session.session_id))
        assert resp.status_code == 402

    def test_takeover_nonexistent_session(self, tenant_client):
        resp = tenant_client.post(takeover_url(uuid.uuid4()))
        assert resp.status_code == 404

    def test_takeover_unauthenticated(self, anon_client, chat_session):
        resp = anon_client.post(takeover_url(chat_session.session_id))
        assert resp.status_code == 401


# ─── Release ──────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestSessionRelease:
    def test_release_active_takeover(self, tenant_client, tenant_user, chat_session):
        chat_session.takeover_active = True
        chat_session.taken_over_by = tenant_user
        chat_session.save()

        resp = tenant_client.post(release_url(chat_session.session_id))
        assert resp.status_code == 200
        assert 'released' in resp.json().get('detail', '').lower()
        chat_session.refresh_from_db()
        assert chat_session.takeover_active is False
        assert chat_session.taken_over_by is None

    def test_release_nonexistent_session(self, tenant_client):
        resp = tenant_client.post(release_url(uuid.uuid4()))
        assert resp.status_code == 404


# ─── Admin Send Message ───────────────────────────────────────────────────────

@pytest.mark.django_db
class TestSessionSendMessage:
    @patch('asgiref.sync.async_to_sync')
    def test_send_message(self, mock_async, tenant_client, chat_session):
        resp = tenant_client.post(send_url(chat_session.session_id), {
            'message': 'Hello from admin!',
        }, format='json')
        assert resp.status_code == 200
        chat_session.refresh_from_db()
        history = chat_session.chat_history
        assert any(
            m.get('message') == 'Hello from admin!' and m.get('source') == 'admin'
            for m in history
        )

    def test_send_empty_message(self, tenant_client, chat_session):
        resp = tenant_client.post(send_url(chat_session.session_id), {
            'message': '',
        }, format='json')
        assert resp.status_code == 400

    def test_send_missing_message(self, tenant_client, chat_session):
        resp = tenant_client.post(send_url(chat_session.session_id), {}, format='json')
        assert resp.status_code == 400

    def test_send_nonexistent_session(self, tenant_client):
        resp = tenant_client.post(send_url(uuid.uuid4()), {
            'message': 'Into the void',
        }, format='json')
        assert resp.status_code == 404

    def test_send_unauthenticated(self, anon_client, chat_session):
        resp = anon_client.post(send_url(chat_session.session_id), {
            'message': 'Unauthorized',
        }, format='json')
        assert resp.status_code == 401


# ─── Session Tags ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestSessionTags:
    def test_set_tags_with_permission(self, tenant_client, tenant_user, chat_session, growth_plan):
        tenant_user.tenant_profile.plan = growth_plan
        tenant_user.tenant_profile.save()

        resp = tenant_client.patch(tags_url(chat_session.session_id), {
            'tags': ['VIP', 'Hot Lead'],
        }, format='json')
        assert resp.status_code == 200
        chat_session.refresh_from_db()
        assert 'VIP' in chat_session.tags
        assert 'Hot Lead' in chat_session.tags

    def test_set_tags_without_permission(self, tenant_client, chat_session, free_plan):
        resp = tenant_client.patch(tags_url(chat_session.session_id), {
            'tags': ['VIP'],
        }, format='json')
        assert resp.status_code == 402

    def test_set_tags_nonexistent_session(self, tenant_client, growth_plan, tenant_user):
        tenant_user.tenant_profile.plan = growth_plan
        tenant_user.tenant_profile.save()
        resp = tenant_client.patch(tags_url(uuid.uuid4()), {'tags': ['Test']}, format='json')
        assert resp.status_code == 404


# ─── Session History ──────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestSessionHistory:
    def test_get_history(self, tenant_client, chat_session):
        chat_session.chat_history = [
            {'role': 'user', 'message': 'Hi'},
            {'role': 'ai', 'message': 'Hello!'},
        ]
        chat_session.save()

        resp = tenant_client.get(history_url(chat_session.session_id))
        assert resp.status_code == 200
        data = resp.json()
        assert 'chat_history' in data or isinstance(data, list)
