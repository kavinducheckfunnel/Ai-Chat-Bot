"""
Tests for the Shopify sprint plan implementation:

  • Phase B — fetch_shopify_data now pulls products + pages + blogs + collections
  • Phase C — `inventory_levels/update` webhook + update_inventory_for_variant task
  • Phase D — detect_platform helper + POST /api/admin/platform/detect/

Each test mocks the network so we never hit a real Shopify store.
"""
from unittest.mock import patch, MagicMock

import pytest


def _ok(json_body):
    """Helper: build a fake requests.Response-style object."""
    m = MagicMock()
    m.status_code = 200
    m.json.return_value = json_body
    m.text = ''
    return m


def _not_found():
    m = MagicMock()
    m.status_code = 404
    m.json.return_value = {}
    m.text = ''
    return m


# ─── Phase B — catalog coverage ─────────────────────────────────────────────

class TestFetchShopifyDataPhaseB:
    def _patched_get(self, mapping):
        """Return a mock that dispatches GET by substring match on URL.

        `mapping` is {path_substring: [list-of-page-responses]} so each
        endpoint can simulate multi-page pagination.
        """
        page_counters = {}

        def fake_get(url, params=None, headers=None, timeout=None):
            for key, pages in mapping.items():
                if key in url:
                    idx = page_counters.get(key, 0)
                    if idx >= len(pages):
                        return _ok({})  # past last page → empty
                    page_counters[key] = idx + 1
                    return pages[idx]
            return _not_found()
        return fake_get

    def test_fetches_products_pages_blogs_collections(self):
        from scraper.ingestion import fetch_shopify_data
        mapping = {
            '/products.json': [_ok({'products': [{
                'id': 1, 'title': 'Hoodie', 'handle': 'hoodie',
                'body_html': '<p>Cozy</p>',
                'variants': [{'id': 11, 'inventory_item_id': 111, 'price': '49', 'sku': 'H-1', 'available': True}],
            }]}), _ok({'products': []})],
            '/pages.json': [_ok({'pages': [{
                'id': 2, 'title': 'About', 'handle': 'about', 'body_html': 'Our story',
            }]}), _ok({'pages': []})],
            '/blogs.json': [_ok({'blogs': [{'id': 3, 'handle': 'news'}]}), _ok({'blogs': []})],
            '/blogs/news/articles.json': [_ok({'articles': [{
                'id': 4, 'title': 'Launch', 'handle': 'launch', 'body_html': '<p>We launched.</p>',
            }]}), _ok({'articles': []})],
            '/collections.json': [_ok({'collections': [{
                'id': 5, 'title': 'Summer', 'handle': 'summer', 'body_html': 'Bright',
            }]}), _ok({'collections': []})],
        }
        with patch('scraper.ingestion.requests.get', side_effect=self._patched_get(mapping)):
            docs = fetch_shopify_data('https://example.com')

        types = sorted((d.get('metadata') or {}).get('type', '') for d in docs)
        assert types == ['article', 'collection', 'page', 'product']

        # Each doc gets a stable shopify_resource key for inventory routing.
        keys = sorted((d.get('metadata') or {}).get('shopify_resource', '') for d in docs)
        assert 'product_1' in keys
        assert 'page_2' in keys
        assert 'article_4' in keys
        assert 'collection_5' in keys

    def test_product_captures_inventory_item_id(self):
        from scraper.ingestion import fetch_shopify_data
        mapping = {
            '/products.json': [_ok({'products': [{
                'id': 1, 'title': 'T', 'handle': 't',
                'body_html': '',
                'variants': [{
                    'id': 11, 'inventory_item_id': 999,
                    'price': '10', 'sku': 'T1', 'available': True,
                }],
            }]}), _ok({'products': []})],
        }
        with patch('scraper.ingestion.requests.get', side_effect=self._patched_get(mapping)):
            docs = fetch_shopify_data('https://example.com')

        product = next(d for d in docs if d['metadata']['type'] == 'product')
        variants = product['metadata']['variants']
        assert variants and variants[0]['inventory_item_id'] == 999
        assert product['metadata']['is_active'] is True

    def test_pages_endpoint_failure_does_not_drop_products(self):
        """A 404 on /pages.json must not abort the whole sync."""
        from scraper.ingestion import fetch_shopify_data

        def fake_get(url, params=None, headers=None, timeout=None):
            if '/products.json' in url:
                if params and params.get('page', 1) == 1:
                    return _ok({'products': [{
                        'id': 1, 'title': 'X', 'handle': 'x',
                        'body_html': '', 'variants': [],
                    }]})
                return _ok({'products': []})
            return _not_found()

        with patch('scraper.ingestion.requests.get', side_effect=fake_get):
            docs = fetch_shopify_data('https://example.com')

        assert any(d['metadata']['type'] == 'product' for d in docs)
        # Pages/blogs/collections returned nothing useful but we kept the product.
        assert not any(d['metadata']['type'] == 'page' for d in docs)

    def test_blogs_capped_at_max(self):
        """Pathological stores with many blogs are capped to avoid request storm."""
        from scraper.ingestion import _shopify_blogs_and_articles
        # 30 fake blogs, but each /articles.json returns empty so we only check the cap.
        mapping = {
            '/blogs.json': [_ok({'blogs': [{'id': i, 'handle': f'b{i}'} for i in range(30)]}), _ok({'blogs': []})],
        }
        # Empty articles endpoints — capture the call count to assert capping.
        article_calls = []

        def fake_get(url, params=None, headers=None, timeout=None):
            if '/blogs.json' in url and '/articles' not in url:
                idx = mapping['/blogs.json']
                # naive single-page emulation
                if not article_calls or not hasattr(fake_get, 'blogs_returned'):
                    fake_get.blogs_returned = True
                    return _ok({'blogs': [{'id': i, 'handle': f'b{i}'} for i in range(30)]})
                return _ok({'blogs': []})
            if '/articles.json' in url:
                article_calls.append(url)
                return _ok({'articles': []})
            return _not_found()

        with patch('scraper.ingestion.requests.get', side_effect=fake_get):
            _shopify_blogs_and_articles('https://example.com', max_blogs=5)

        # At most 5 distinct article endpoints should have been hit.
        assert len({u for u in article_calls if '/articles.json' in u}) <= 5


# ─── Phase C — inventory webhook + task ─────────────────────────────────────

@pytest.mark.django_db
class TestInventoryWebhookBranch:
    def _url(self, client_id):
        return f'/api/scraper/webhooks/shopify/{client_id}/'

    @patch('scraper.tasks.update_inventory_for_variant.delay')
    def test_inventory_topic_routes_to_inventory_task(self, mock_task, anon_client, client_obj):
        payload = {'inventory_item_id': 999, 'available': 5, 'location_id': 1}
        resp = anon_client.post(
            self._url(client_obj.id), payload,
            format='json',
            **{'HTTP_X_SHOPIFY_TOPIC': 'inventory_levels/update'},
        )
        assert resp.status_code == 202
        assert resp.json()['status'] == 'inventory queued'
        mock_task.assert_called_once()
        args = mock_task.call_args.args
        assert args[1] == '999'           # inventory_item_id
        assert args[2] == 5               # available

    def test_inventory_missing_fields_returns_400(self, anon_client, client_obj):
        resp = anon_client.post(
            self._url(client_obj.id), {'available': 5},
            format='json',
            **{'HTTP_X_SHOPIFY_TOPIC': 'inventory_levels/update'},
        )
        assert resp.status_code == 400


@pytest.mark.django_db
class TestUpdateInventoryForVariantTask:
    def _make_chunk(self, client_obj, inventory_item_id, available=10):
        from scraper.models import DocumentChunk
        return DocumentChunk.objects.create(
            client=client_obj,
            content=f'Product: Test\nURL: https://x.com/p',
            embedding=[0.0] * 1024,
            source_url='https://x.com/p',
            product_id='1',
            metadata={
                'title': 'Test', 'type': 'product',
                'shopify_resource': 'product_1',
                'variants': [{
                    'variant_id': 11, 'inventory_item_id': inventory_item_id,
                    'sku': 'T-1', 'price': '10', 'available': available,
                }],
                'is_active': True,
            },
        )

    def test_drops_stock_to_zero_marks_inactive(self, client_obj):
        from scraper.tasks import update_inventory_for_variant
        chunk = self._make_chunk(client_obj, inventory_item_id=999, available=10)
        with patch('scraper.embeddings.batch_embed_texts', return_value=[[0.1] * 1024]):
            update_inventory_for_variant(str(client_obj.id), '999', 0)
        chunk.refresh_from_db()
        assert chunk.metadata['variants'][0]['available'] == 0
        assert chunk.metadata['is_active'] is False
        assert 'Stock: SOLD OUT' in chunk.content

    def test_restock_marks_active_with_count(self, client_obj):
        from scraper.tasks import update_inventory_for_variant
        chunk = self._make_chunk(client_obj, inventory_item_id=999, available=0)
        chunk.metadata['variants'][0]['available'] = 0
        chunk.metadata['is_active'] = False
        chunk.save()
        with patch('scraper.embeddings.batch_embed_texts', return_value=[[0.1] * 1024]):
            update_inventory_for_variant(str(client_obj.id), '999', 12)
        chunk.refresh_from_db()
        assert chunk.metadata['variants'][0]['available'] == 12
        assert chunk.metadata['is_active'] is True
        assert 'Stock: 12 units' in chunk.content
        # Only one Stock: line — old line replaced, not duplicated.
        assert chunk.content.count('Stock:') == 1

    def test_no_matching_chunk_is_a_noop(self, client_obj):
        from scraper.tasks import update_inventory_for_variant
        with patch('scraper.embeddings.batch_embed_texts', return_value=[[0.1] * 1024]) as mock_embed:
            result = update_inventory_for_variant(str(client_obj.id), '4242', 5)
        assert result == 'no_chunk'
        mock_embed.assert_not_called()


# ─── Phase D — detect_platform ───────────────────────────────────────────────

class TestDetectPlatformHelper:
    def test_myshopify_domain_short_circuits(self):
        from scraper.ingestion import detect_platform
        # Should not need any network calls.
        with patch('scraper.ingestion.requests.get') as mock_get:
            assert detect_platform('https://demo.myshopify.com') == 'SHOPIFY'
            mock_get.assert_not_called()

    def test_products_json_returns_shopify(self):
        from scraper.ingestion import detect_platform

        def fake_get(url, params=None, headers=None, timeout=None):
            if '/products.json' in url:
                return _ok({'products': []})
            return _not_found()

        with patch('scraper.ingestion.requests.get', side_effect=fake_get):
            assert detect_platform('https://custom-domain.com') == 'SHOPIFY'

    def test_wp_json_returns_wordpress(self):
        from scraper.ingestion import detect_platform

        def fake_get(url, params=None, headers=None, timeout=None):
            if '/wp-json/' in url:
                return _ok({'namespaces': ['wp/v2']})
            return _not_found()

        with patch('scraper.ingestion.requests.get', side_effect=fake_get):
            assert detect_platform('https://blog.example') == 'WORDPRESS'

    def test_homepage_shopify_marker(self):
        from scraper.ingestion import detect_platform

        def fake_get(url, params=None, headers=None, timeout=None):
            r = MagicMock()
            r.status_code = 200
            if url.endswith('/products.json') or '/wp-json/' in url:
                r.status_code = 404
                r.json.return_value = {}
                return r
            r.text = '<html><script src="https://cdn.shopify.com/x.js"></script></html>'
            r.json.side_effect = ValueError()
            return r

        with patch('scraper.ingestion.requests.get', side_effect=fake_get):
            assert detect_platform('https://example.com') == 'SHOPIFY'

    def test_unknown_returns_custom(self):
        from scraper.ingestion import detect_platform
        with patch('scraper.ingestion.requests.get', return_value=_not_found()):
            assert detect_platform('https://random.example') == 'CUSTOM'

    def test_blank_url_returns_custom(self):
        from scraper.ingestion import detect_platform
        assert detect_platform('') == 'CUSTOM'


# ─── Phase D — POST /api/admin/platform/detect/ endpoint ────────────────────

@pytest.mark.django_db
class TestDetectPlatformEndpoint:
    URL = '/api/admin/platform/detect/'

    def test_authenticated_shopify_url_returns_detected(self, tenant_client):
        with patch('scraper.ingestion.detect_platform', return_value='SHOPIFY'):
            resp = tenant_client.post(self.URL, {'url': 'https://demo.myshopify.com'}, format='json')
        assert resp.status_code == 200
        body = resp.json()
        assert body['platform'] == 'SHOPIFY'
        assert body['detected'] is True

    def test_unknown_returns_custom_not_detected(self, tenant_client):
        with patch('scraper.ingestion.detect_platform', return_value='CUSTOM'):
            resp = tenant_client.post(self.URL, {'url': 'https://random.example'}, format='json')
        assert resp.status_code == 200
        body = resp.json()
        assert body['platform'] == 'CUSTOM'
        assert body['detected'] is False

    def test_blank_url_returns_400(self, tenant_client):
        resp = tenant_client.post(self.URL, {'url': ''}, format='json')
        assert resp.status_code == 400

    def test_anonymous_denied(self, anon_client):
        resp = anon_client.post(self.URL, {'url': 'https://x.com'}, format='json')
        assert resp.status_code == 401

    def test_helper_exception_falls_back_to_custom(self, tenant_client):
        """If detect_platform raises, the endpoint must still return 200."""
        with patch('scraper.ingestion.detect_platform', side_effect=RuntimeError('boom')):
            resp = tenant_client.post(self.URL, {'url': 'https://x.com'}, format='json')
        assert resp.status_code == 200
        assert resp.json()['platform'] == 'CUSTOM'
