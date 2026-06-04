"""
Tests for product-link click attribution (Issue 4):
  • POST /api/chat/link-click/        — record a click
  • GET  /api/admin/clients/<id>/link-clicks/  — tenant aggregation
  • GET  /api/admin/link-clicks/      — superadmin global aggregation
"""
import pytest

from chat.models import ProductLinkClick


LINK_CLICK_URL = '/api/chat/link-click/'


@pytest.mark.django_db
class TestTrackLinkClick:
    def test_records_click(self, anon_client, chat_session, client_obj):
        resp = anon_client.post(LINK_CLICK_URL, {
            'session_id': str(chat_session.session_id),
            'client_id': str(client_obj.id),
            'url': 'https://shop.test/product/cap/',
            'link_text': 'Cap',
        }, format='json')
        assert resp.status_code == 202
        assert resp.json()['status'] == 'recorded'
        plc = ProductLinkClick.objects.get()
        assert plc.url == 'https://shop.test/product/cap/'
        assert plc.link_text == 'Cap'
        assert plc.client_id == client_obj.id

    def test_ignores_missing_url(self, anon_client, chat_session):
        resp = anon_client.post(LINK_CLICK_URL, {
            'session_id': str(chat_session.session_id),
        }, format='json')
        assert resp.status_code == 202
        assert resp.json()['status'] == 'ignored'
        assert ProductLinkClick.objects.count() == 0

    def test_ignores_non_http_url(self, anon_client, chat_session):
        resp = anon_client.post(LINK_CLICK_URL, {
            'session_id': str(chat_session.session_id),
            'url': 'javascript:alert(1)',
        }, format='json')
        assert resp.status_code == 202
        assert ProductLinkClick.objects.count() == 0

    def test_unknown_client_still_records(self, anon_client, chat_session):
        # client_id absent → row stored with client=None (still useful global data)
        resp = anon_client.post(LINK_CLICK_URL, {
            'session_id': str(chat_session.session_id),
            'url': 'https://shop.test/p/1',
        }, format='json')
        assert resp.status_code == 202
        assert ProductLinkClick.objects.filter(client__isnull=True).count() == 1


@pytest.mark.django_db
class TestClientLinkClicksAggregation:
    def _url(self, cid):
        return f'/api/admin/clients/{cid}/link-clicks/'

    def _seed(self, client_obj):
        # cap: 3 clicks across 2 sessions; hoodie: 1 click
        ProductLinkClick.objects.create(client=client_obj, session_id='s1', url='https://x/cap', link_text='Cap')
        ProductLinkClick.objects.create(client=client_obj, session_id='s1', url='https://x/cap', link_text='Cap')
        ProductLinkClick.objects.create(client=client_obj, session_id='s2', url='https://x/cap', link_text='Cap')
        ProductLinkClick.objects.create(client=client_obj, session_id='s3', url='https://x/hoodie', link_text='Hoodie')

    def test_groups_by_url_with_counts(self, tenant_client, client_obj):
        self._seed(client_obj)
        resp = tenant_client.get(self._url(client_obj.id) + '?period=all')
        assert resp.status_code == 200
        body = resp.json()
        assert body['total_clicks'] == 4
        assert body['total_links'] == 2
        cap = next(l for l in body['links'] if l['url'] == 'https://x/cap')
        assert cap['clicks'] == 3
        assert cap['unique_sessions'] == 2
        assert cap['link_text'] == 'Cap'
        # Sorted by clicks desc — cap first.
        assert body['links'][0]['url'] == 'https://x/cap'

    def test_tenant_isolation(self, tenant_client2, client_obj):
        # client_obj belongs to tenant_user, not tenant_user2.
        self._seed(client_obj)
        resp = tenant_client2.get(self._url(client_obj.id) + '?period=all')
        assert resp.status_code == 404

    def test_anonymous_denied(self, anon_client, client_obj):
        resp = anon_client.get(self._url(client_obj.id))
        assert resp.status_code == 401


@pytest.mark.django_db
class TestPlatformLinkClicks:
    URL = '/api/admin/link-clicks/'

    def test_superadmin_global_view(self, superadmin_client, client_obj):
        ProductLinkClick.objects.create(client=client_obj, session_id='s1', url='https://x/cap', link_text='Cap')
        ProductLinkClick.objects.create(client=client_obj, session_id='s2', url='https://x/cap', link_text='Cap')
        resp = superadmin_client.get(self.URL + '?period=all')
        assert resp.status_code == 200
        body = resp.json()
        assert body['total_clicks'] == 2
        assert body['top_links'][0]['url'] == 'https://x/cap'
        assert body['top_links'][0]['clicks'] == 2
        assert any(c['client_name'] == client_obj.name for c in body['by_client'])

    def test_tenant_forbidden(self, tenant_client):
        resp = tenant_client.get(self.URL)
        assert resp.status_code == 403
