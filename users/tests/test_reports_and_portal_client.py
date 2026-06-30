"""
Tests for the Reports-metrics fix (#1) and the portal-client pinning (#3).
"""
import pytest

from chat.models import ChatSession, Visitor


@pytest.mark.django_db
class TestUniqueVisitorsMetric:
    def _url(self, cid):
        return f'/api/admin/clients/{cid}/analytics/?period=90d'

    def test_counts_distinct_visitor_obj_not_legacy_id(self, tenant_client, client_obj):
        # Three sessions, two distinct Visitor identities — legacy visitor_id
        # left blank (as the WS path leaves it). Old code counted distinct
        # blank visitor_id → 1. New code counts visitor_obj → 2.
        v1 = Visitor.objects.create(visitor_uid='vuid-1', client=client_obj)
        v2 = Visitor.objects.create(visitor_uid='vuid-2', client=client_obj)
        ChatSession.objects.create(client=client_obj, visitor_id='', visitor_obj=v1, message_count=2)
        ChatSession.objects.create(client=client_obj, visitor_id='', visitor_obj=v1, message_count=1)
        ChatSession.objects.create(client=client_obj, visitor_id='', visitor_obj=v2, message_count=3)

        resp = tenant_client.get(self._url(client_obj.id))
        assert resp.status_code == 200
        body = resp.json()
        assert body['unique_visitors']['value'] == 2
        assert body['total_sessions']['value'] == 3

    def test_unlinked_sessions_not_counted(self, tenant_client, client_obj):
        # Anonymous sessions with no Visitor row are NOT counted as unique
        # visitors — the metric counts real Visitor identities only, so it
        # tallies exactly with the Audience page (which lists Visitor rows).
        ChatSession.objects.create(client=client_obj, visitor_id='', message_count=1)
        ChatSession.objects.create(client=client_obj, visitor_id='', message_count=1)
        resp = tenant_client.get(self._url(client_obj.id))
        assert resp.json()['unique_visitors']['value'] == 0

    def test_tallies_with_visitor_table(self, tenant_client, client_obj):
        # unique_visitors must equal the distinct Visitor count (the Audience
        # total), regardless of how many sessions or unlinked ghosts exist.
        v1 = Visitor.objects.create(visitor_uid='vt-1', client=client_obj)
        v2 = Visitor.objects.create(visitor_uid='vt-2', client=client_obj)
        ChatSession.objects.create(client=client_obj, visitor_obj=v1, message_count=2)
        ChatSession.objects.create(client=client_obj, visitor_obj=v2, message_count=1)
        ChatSession.objects.create(client=client_obj, visitor_id='', message_count=1)  # unlinked ghost
        resp = tenant_client.get(self._url(client_obj.id))
        assert resp.json()['unique_visitors']['value'] == Visitor.objects.filter(client=client_obj).count() == 2

    def test_opened_no_message_and_answered_exposed(self, tenant_client, client_obj):
        ChatSession.objects.create(client=client_obj, message_count=0)   # ghost
        ChatSession.objects.create(client=client_obj, message_count=2)   # answered
        resp = tenant_client.get(self._url(client_obj.id))
        body = resp.json()
        assert body['opened_no_message']['value'] == 1
        assert body['answered_chats']['value'] == 1


@pytest.mark.django_db
class TestPortalClientPinning:
    URL = '/api/admin/portal/client/'

    def test_returns_own_tenant_client(self, tenant_client, tenant_user, client_obj):
        resp = tenant_client.get(self.URL)
        assert resp.status_code == 200
        assert resp.json()['id'] == str(client_obj.id)

    def test_stable_oldest_first(self, tenant_client, tenant_user, client_obj):
        # Add a second, newer client to the same tenant. portal_client must
        # still return the OLDEST (stable primary), not the newest.
        from users.models import Client
        newer = Client.objects.create(name='Newer Co', platform='CUSTOM')
        tenant_user.tenant_profile.clients.add(newer)
        resp = tenant_client.get(self.URL)
        assert resp.json()['id'] == str(client_obj.id)

    def test_superadmin_not_global_newest(self, superadmin_client, superadmin_user, client_obj):
        # A super-admin must NOT be handed another tenant's client just
        # because it's the global-newest (the old bug). portal_client is
        # strictly scoped to the super-admin's OWN tenant_profile, so it
        # never returns client_obj (which belongs to tenant_user).
        resp = superadmin_client.get(self.URL)
        assert resp.status_code == 200
        body = resp.content.decode().strip()
        # Either null, or their own client — but never the other tenant's.
        assert str(client_obj.id) not in body

    def test_anonymous_denied(self, anon_client):
        resp = anon_client.get(self.URL)
        assert resp.status_code == 401
