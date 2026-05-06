"""
Tests for client management endpoints:
  GET/POST /api/admin/clients/
  GET/PATCH/DELETE /api/admin/clients/{uuid}/
  GET  /api/admin/clients/{uuid}/sessions/
  POST /api/admin/clients/{uuid}/scrape/
  GET  /api/admin/clients/{uuid}/scrape-progress/
  POST /api/admin/clients/{uuid}/rotate-secret/
"""
import pytest
from unittest.mock import patch
from rest_framework.test import APIClient

from users.models import Client, TenantProfile


CLIENTS_URL = '/api/admin/clients/'


def detail_url(client_id):
    return f'/api/admin/clients/{client_id}/'


def sessions_url(client_id):
    return f'/api/admin/clients/{client_id}/sessions/'


def scrape_url(client_id):
    return f'/api/admin/clients/{client_id}/scrape/'


def scrape_progress_url(client_id):
    return f'/api/admin/clients/{client_id}/scrape-progress/'


def rotate_url(client_id):
    return f'/api/admin/clients/{client_id}/rotate-secret/'


# ─── List & Create ────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestClientList:
    def test_list_unauthenticated(self, anon_client):
        resp = anon_client.get(CLIENTS_URL)
        assert resp.status_code == 401

    def test_list_tenant_sees_own_only(self, tenant_client, client_obj, client_obj2):
        resp = tenant_client.get(CLIENTS_URL)
        assert resp.status_code == 200
        ids = [item['id'] for item in resp.json()]
        assert str(client_obj.id) in ids
        assert str(client_obj2.id) not in ids

    def test_list_superadmin_sees_all(self, superadmin_client, client_obj, client_obj2):
        resp = superadmin_client.get(CLIENTS_URL)
        assert resp.status_code == 200
        ids = [item['id'] for item in resp.json()]
        assert str(client_obj.id) in ids
        assert str(client_obj2.id) in ids

    def test_create_valid(self, tenant_client, tenant_user):
        resp = tenant_client.post(CLIENTS_URL, {
            'name': 'New Store',
            'domain_url': 'https://newstore.com',
            'platform': 'SHOPIFY',
        }, format='json')
        assert resp.status_code == 201
        data = resp.json()
        assert data['name'] == 'New Store'
        # Auto-assigned to tenant
        assert tenant_user.tenant_profile.clients.filter(pk=data['id']).exists()

    def test_create_unauthenticated(self, anon_client):
        resp = anon_client.post(CLIENTS_URL, {
            'name': 'Ghost Store',
            'domain_url': 'https://ghost.com',
            'platform': 'CUSTOM',
        }, format='json')
        assert resp.status_code == 401


# ─── Retrieve, Update, Delete ────────────────────────────────────────────────

@pytest.mark.django_db
class TestClientDetail:
    def test_get_own_client(self, tenant_client, client_obj):
        resp = tenant_client.get(detail_url(client_obj.id))
        assert resp.status_code == 200
        assert resp.json()['name'] == client_obj.name

    def test_get_other_tenants_client(self, tenant_client, client_obj2):
        resp = tenant_client.get(detail_url(client_obj2.id))
        assert resp.status_code == 404

    def test_patch_branding(self, tenant_client, client_obj):
        resp = tenant_client.patch(detail_url(client_obj.id), {
            'chatbot_name': 'Updated Bot',
            'chatbot_color': '#00FF00',
        }, format='json')
        assert resp.status_code == 200
        assert resp.json()['chatbot_name'] == 'Updated Bot'
        client_obj.refresh_from_db()
        assert client_obj.chatbot_color == '#00FF00'

    def test_patch_notification_email(self, tenant_client, client_obj):
        resp = tenant_client.patch(detail_url(client_obj.id), {
            'notification_email': 'alerts@test.com',
        }, format='json')
        assert resp.status_code == 200
        client_obj.refresh_from_db()
        assert client_obj.notification_email == 'alerts@test.com'

    def test_patch_other_tenants_client(self, tenant_client, client_obj2):
        resp = tenant_client.patch(detail_url(client_obj2.id), {
            'chatbot_name': 'Hacked',
        }, format='json')
        assert resp.status_code == 404

    def test_delete_own_client(self, tenant_client, client_obj):
        client_id = client_obj.id
        resp = tenant_client.delete(detail_url(client_id))
        assert resp.status_code == 204
        assert not Client.objects.filter(pk=client_id).exists()

    def test_delete_other_tenants_client(self, tenant_client, client_obj2):
        resp = tenant_client.delete(detail_url(client_obj2.id))
        assert resp.status_code == 404
        assert Client.objects.filter(pk=client_obj2.id).exists()

    def test_superadmin_can_patch_any_client(self, superadmin_client, client_obj2):
        resp = superadmin_client.patch(detail_url(client_obj2.id), {
            'chatbot_name': 'Admin Renamed',
        }, format='json')
        assert resp.status_code == 200

    def test_get_nonexistent_client(self, tenant_client):
        import uuid
        resp = tenant_client.get(detail_url(uuid.uuid4()))
        assert resp.status_code == 404


# ─── Sessions list for a client ───────────────────────────────────────────────

@pytest.mark.django_db
class TestClientSessions:
    def test_list_sessions(self, tenant_client, client_obj, chat_session):
        resp = tenant_client.get(sessions_url(client_obj.id))
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert any(str(s['session_id']) == str(chat_session.session_id) for s in data)

    def test_sessions_filtered_by_state(self, tenant_client, client_obj, chat_session):
        from chat.models import ChatSession
        ChatSession.objects.filter(session_id=chat_session.session_id).update(
            conversation_state='EVALUATION'
        )
        resp = tenant_client.get(sessions_url(client_obj.id) + '?state=EVALUATION')
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

        resp2 = tenant_client.get(sessions_url(client_obj.id) + '?state=RESEARCH')
        assert resp2.status_code == 200
        assert len(resp2.json()) == 0

    def test_sessions_other_tenant_blocked(self, tenant_client, client_obj2):
        resp = tenant_client.get(sessions_url(client_obj2.id))
        assert resp.status_code == 404


# ─── Scrape trigger and progress ─────────────────────────────────────────────

@pytest.mark.django_db
class TestScrape:
    def test_trigger_scrape(self, tenant_client, client_obj):
        # Scrape runs in a background thread (not Celery); verify 200 and running status.
        resp = tenant_client.post(scrape_url(client_obj.id))
        assert resp.status_code == 200
        assert resp.json().get('status') == 'RUNNING'

    def test_scrape_progress(self, tenant_client, client_obj):
        resp = tenant_client.get(scrape_progress_url(client_obj.id))
        assert resp.status_code == 200
        data = resp.json()
        assert 'ingestion_status' in data or 'status' in data

    def test_trigger_scrape_other_tenant_blocked(self, tenant_client, client_obj2):
        resp = tenant_client.post(scrape_url(client_obj2.id))
        assert resp.status_code in (403, 404)


# ─── Rotate webhook secret ────────────────────────────────────────────────────

@pytest.mark.django_db
class TestRotateSecret:
    def test_rotate_secret(self, tenant_client, client_obj):
        old_secret = client_obj.webhook_secret
        resp = tenant_client.post(rotate_url(client_obj.id))
        assert resp.status_code == 200
        client_obj.refresh_from_db()
        new_secret = client_obj.webhook_secret
        assert new_secret is not None
        assert new_secret != old_secret

    def test_rotate_other_tenant_blocked(self, tenant_client, client_obj2):
        resp = tenant_client.post(rotate_url(client_obj2.id))
        assert resp.status_code in (403, 404)
