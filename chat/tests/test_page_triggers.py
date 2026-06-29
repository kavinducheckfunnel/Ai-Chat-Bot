"""
Tests for page-aware proactive triggers:
  - chat.page_rules helpers (classify_path / match_rule / resolve_greeting_text)
  - POST /api/chat/page-message/  (first-touch intro, de-dupe, guards, fallback)
  - widget-config exposes page_rules + proactive settings
  - admin site-pages endpoint (tenant-scoped)
"""
import pytest

from chat.models import ChatSession
from chat import page_rules as pr


# ─── Helpers ──────────────────────────────────────────────────────────────────

class TestClassify:
    def test_known_types(self):
        assert pr.classify_path('/') == 'home'
        assert pr.classify_path('/home') == 'home'
        assert pr.classify_path('/products/blue-hoodie') == 'product'
        assert pr.classify_path('/collections/men') == 'collection'
        assert pr.classify_path('/category/shoes') == 'collection'
        assert pr.classify_path('/cart') == 'cart'
        assert pr.classify_path('/checkout/step1') == 'checkout'
        assert pr.classify_path('/contact-us') == 'contact'
        assert pr.classify_path('/about-us') == 'about'
        assert pr.classify_path('/help/returns') == 'faq'
        assert pr.classify_path('/pricing') == 'offers'
        assert pr.classify_path('/order-tracking') == 'track'
        assert pr.classify_path('/some/random/page') == 'fallback'

    def test_checkout_beats_cart(self):
        # A /checkout path must not be mis-tagged as cart.
        assert pr.classify_path('/checkout') == 'checkout'


class TestMatchRule:
    def test_default_product_match(self):
        rule = pr.match_rule(pr.DEFAULT_PAGE_RULES, 'https://shop.com/products/x')
        assert rule and rule['page_type'] == 'product'

    def test_fallback_when_unmapped(self):
        rule = pr.match_rule(pr.DEFAULT_PAGE_RULES, 'https://shop.com/blog/post-1')
        assert rule and rule['page_type'] == 'fallback'

    def test_classify_catches_variants(self):
        # /category/ has no explicit default pattern but classify maps it.
        rule = pr.match_rule(pr.DEFAULT_PAGE_RULES, 'https://shop.com/category/men')
        assert rule and rule['page_type'] == 'collection'

    def test_exact_trailing_slash_insensitive(self):
        rules = [{'page_type': 'about', 'match_type': 'exact', 'pattern': '/about', 'priority': 50,
                  'greeting_message': 'a', 'greeting_enabled': True, 'enabled_widget': True}]
        assert pr.match_rule(rules, 'https://s.com/about/') is not None
        assert pr.match_rule(rules, 'https://s.com/about') is not None

    def test_priority_specific_wins(self):
        rules = [
            {'page_type': 'fallback', 'match_type': 'contains', 'pattern': '', 'priority': 0,
             'greeting_message': 'fb', 'greeting_enabled': True, 'enabled_widget': True},
            {'page_type': 'product', 'match_type': 'contains', 'pattern': '/products/', 'priority': 60,
             'greeting_message': 'prod', 'greeting_enabled': True, 'enabled_widget': True},
        ]
        rule = pr.match_rule(rules, '/products/abc')
        assert rule['page_type'] == 'product'


class TestResolveGreeting:
    def test_product_name_interpolation(self):
        rule = {'greeting_message': 'Interested in the {product_name}?'}
        assert pr.resolve_greeting_text(rule, 'Blue Hoodie') == 'Interested in the Blue Hoodie?'

    def test_graceful_without_name(self):
        rule = {'greeting_message': 'Interested in the {product_name}?'}
        assert pr.resolve_greeting_text(rule, '') == 'Interested in this product?'


# ─── page-message endpoint ────────────────────────────────────────────────────

def pm_url():
    return '/api/chat/page-message/'


@pytest.mark.django_db
class TestPageMessageEndpoint:
    def _body(self, session, page_url, **extra):
        return {'session_id': str(session.session_id), 'client_id': str(session.client_id),
                'page_url': page_url, **extra}

    def test_first_touch_prepends_intro_once(self, anon_client, chat_session, client_obj):
        client_obj.assistant_intro = "Hi! I'm your AI Shopping Assistant."
        client_obj.save()
        # First greeting (home) → intro prepended
        r1 = anon_client.post(pm_url(), self._body(chat_session, 'https://s.com/'), format='json')
        assert r1.status_code in (200, 202)
        assert r1.json()['status'] == 'sent'
        assert r1.json()['message'].startswith("Hi! I'm your AI Shopping Assistant.")

        # Second greeting on a DIFFERENT page type (product) → NO intro repeat
        r2 = anon_client.post(pm_url(), self._body(chat_session, 'https://s.com/products/x'), format='json')
        assert r2.json()['status'] == 'sent'
        assert not r2.json()['message'].startswith("Hi! I'm your AI Shopping Assistant.")

        chat_session.refresh_from_db()
        assert chat_session.greeting_intro_sent is True
        greetings = [m for m in chat_session.chat_history if m.get('source') == 'page_greeting']
        assert len(greetings) == 2

    def test_dedupe_same_page_type(self, anon_client, chat_session):
        a = anon_client.post(pm_url(), self._body(chat_session, 'https://s.com/products/a'), format='json')
        assert a.json()['status'] == 'sent'
        b = anon_client.post(pm_url(), self._body(chat_session, 'https://s.com/products/b'), format='json')
        assert b.json()['status'] == 'duplicate'

    def test_product_name_used(self, anon_client, chat_session):
        r = anon_client.post(pm_url(), self._body(chat_session, 'https://s.com/products/x', product_name='Yamaha Cap'), format='json')
        assert 'Yamaha Cap' in r.json()['message']

    def test_disabled_when_proactive_off(self, anon_client, chat_session, client_obj):
        client_obj.proactive_notifications_enabled = False
        client_obj.save()
        r = anon_client.post(pm_url(), self._body(chat_session, 'https://s.com/'), format='json')
        assert r.json()['status'] == 'ignored'

    def test_takeover_blocks(self, anon_client, chat_session):
        ChatSession.objects.filter(pk=chat_session.pk).update(takeover_active=True)
        r = anon_client.post(pm_url(), self._body(chat_session, 'https://s.com/'), format='json')
        assert r.json()['status'] == 'ignored'

    def test_custom_rule_greeting_disabled(self, anon_client, chat_session, client_obj):
        client_obj.page_rules = [{
            'label': 'Home', 'match_type': 'exact', 'pattern': '/', 'page_type': 'home',
            'priority': 10, 'enabled_widget': True, 'greeting_enabled': False,
            'greeting_message': 'should not send', 'behavior_prompt': '',
        }]
        client_obj.save()
        r = anon_client.post(pm_url(), self._body(chat_session, 'https://s.com/'), format='json')
        assert r.json()['status'] == 'ignored'


# ─── widget-config exposure ───────────────────────────────────────────────────

@pytest.mark.django_db
class TestWidgetConfigProactive:
    def test_config_includes_page_rules(self, anon_client, client_obj):
        data = anon_client.get(f'/api/chat/widget-config/{client_obj.id}/').json()
        assert 'page_rules' in data and isinstance(data['page_rules'], list) and data['page_rules']
        assert 'assistant_intro' in data
        assert 'proactive_enabled' in data
        assert 'notification_timeout_seconds' in data
        assert 'auto_close_seconds' in data
        # behavior_prompt must NOT leak to the public widget config
        assert all('behavior_prompt' not in r for r in data['page_rules'])

    def test_per_page_timeout_and_autoclose_exposed(self, anon_client, client_obj):
        client_obj.page_rules = [{
            'label': 'Cart', 'match_type': 'contains', 'pattern': '/cart', 'page_type': 'cart',
            'priority': 55, 'enabled_widget': True, 'greeting_enabled': True,
            'greeting_message': 'Cart help', 'behavior_prompt': 'be helpful',
            'notification_timeout': 30, 'auto_close': 120,
        }]
        client_obj.save()
        data = anon_client.get(f'/api/chat/widget-config/{client_obj.id}/').json()
        cart = next(r for r in data['page_rules'] if r.get('pattern') == '/cart')
        assert cart['notification_timeout'] == 30
        assert cart['auto_close'] == 120
        assert 'behavior_prompt' not in cart  # still server-only


# ─── admin site-pages endpoint ────────────────────────────────────────────────

@pytest.mark.django_db
class TestSitePagesEndpoint:
    def test_returns_pages_and_defaults(self, tenant_client, client_obj):
        from scraper.models import SitePage
        SitePage.objects.create(client=client_obj, path='/products/x', url='https://s.com/products/x',
                                title='X', page_type='product')
        data = tenant_client.get(f'/api/admin/clients/{client_obj.id}/site-pages/').json()
        assert any(p['page_type'] == 'product' for p in data['pages'])
        assert data['default_rules']

    def test_other_tenant_blocked(self, tenant_client2, client_obj):
        resp = tenant_client2.get(f'/api/admin/clients/{client_obj.id}/site-pages/')
        assert resp.status_code in (403, 404)


# ─── Dynamic high-level page detection (sync_site_pages) ──────────────────────

@pytest.mark.django_db
class TestSyncSitePages:
    def _doc(self, client, url, title=''):
        from scraper.models import DocumentChunk
        DocumentChunk.objects.create(
            client=client, content='x', embedding=[0.0] * 1024,
            source_url=url, metadata={'title': title},
        )

    def test_detects_high_level_and_collapses_products(self, client_obj):
        from scraper.tasks import sync_site_pages
        from scraper.models import SitePage
        base = 'https://shop.com'
        self._doc(client_obj, base + '/', 'Home')
        self._doc(client_obj, base + '/about-us', 'About')
        self._doc(client_obj, base + '/collections/men', 'Men')
        self._doc(client_obj, base + '/products/blue-hoodie', 'Blue Hoodie')
        self._doc(client_obj, base + '/products/red-cap', 'Red Cap')
        self._doc(client_obj, base + '/blogs/news/deep/post', 'Deep')  # too deep → excluded

        sync_site_pages(client_obj)
        paths = set(SitePage.objects.filter(client=client_obj).values_list('path', flat=True))
        types = set(SitePage.objects.filter(client=client_obj).values_list('page_type', flat=True))

        assert '/' in paths and '/about-us' in paths and '/collections/men' in paths
        # individual products collapsed to ONE template row, not listed each
        assert '/products/blue-hoodie' not in paths and '/products/red-cap' not in paths
        assert '/products/' in paths
        assert 'product' in types
        # deep blog post excluded from high-level
        assert '/blogs/news/deep/post' not in paths

    def test_sync_endpoint(self, tenant_client, client_obj):
        self._doc(client_obj, 'https://shop.com/contact', 'Contact')
        resp = tenant_client.post(f'/api/admin/clients/{client_obj.id}/sync-pages/')
        assert resp.status_code == 200
        data = resp.json()
        assert any(p['path'] == '/contact' for p in data['pages'])
