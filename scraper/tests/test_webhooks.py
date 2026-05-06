"""
Tests for scraper webhook endpoints:
  POST /api/scraper/webhooks/shopify/{uuid}/
  POST /api/scraper/webhooks/woocommerce/{uuid}/
  POST /api/scraper/webhooks/wordpress/{uuid}/
"""
import uuid
import pytest
from unittest.mock import patch
from rest_framework.test import APIClient


def shopify_url(client_id):
    return f'/api/scraper/webhooks/shopify/{client_id}/'


def woo_url(client_id):
    return f'/api/scraper/webhooks/woocommerce/{client_id}/'


def wp_url(client_id):
    return f'/api/scraper/webhooks/wordpress/{client_id}/'


SHOPIFY_PAYLOAD = {
    'id': 12345,
    'title': 'Blue Widget',
    'body_html': '<p>A beautiful blue widget.</p>',
    'handle': 'blue-widget',
    'variants': [{'price': '29.99'}],
}

WOOCOMMERCE_PAYLOAD = {
    'id': 67890,
    'name': 'Red Gadget',
    'description': 'A red gadget.',
    'price': '49.99',
    'permalink': 'https://shop.com/product/red-gadget',
}

WORDPRESS_PAYLOAD = {
    'id': 111,
    'title': {'rendered': 'My Blog Post'},
    'content': {'rendered': '<p>Post body here.</p>'},
    'link': 'https://wp.com/my-blog-post',
}


# ─── Shopify Webhook ──────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestShopifyWebhook:
    @patch('scraper.tasks.re_embed_product.delay')
    def test_shopify_valid_payload(self, mock_task, anon_client, client_obj):
        client_obj.domain_url = 'https://teststore.myshopify.com'
        client_obj.save()
        resp = anon_client.post(shopify_url(client_obj.id), SHOPIFY_PAYLOAD, format='json')
        assert resp.status_code == 202
        assert resp.json()['status'] == 'queued'
        mock_task.assert_called_once()

    @patch('scraper.tasks.re_embed_product.delay')
    def test_shopify_missing_title(self, mock_task, anon_client, client_obj):
        payload = {**SHOPIFY_PAYLOAD, 'title': ''}
        resp = anon_client.post(shopify_url(client_obj.id), payload, format='json')
        assert resp.status_code == 400
        mock_task.assert_not_called()

    @patch('scraper.tasks.re_embed_product.delay')
    def test_shopify_missing_id(self, mock_task, anon_client, client_obj):
        payload = {k: v for k, v in SHOPIFY_PAYLOAD.items() if k != 'id'}
        resp = anon_client.post(shopify_url(client_obj.id), payload, format='json')
        assert resp.status_code == 400

    def test_shopify_unknown_client(self, anon_client):
        resp = anon_client.post(shopify_url(uuid.uuid4()), SHOPIFY_PAYLOAD, format='json')
        assert resp.status_code == 404

    @patch('scraper.tasks.re_embed_product.delay')
    def test_shopify_hmac_verification_pass(self, mock_task, anon_client, client_obj):
        import hmac as hmac_lib
        import hashlib
        import json
        client_obj.webhook_secret = 'shpss_secret'
        client_obj.domain_url = 'https://teststore.myshopify.com'
        client_obj.save()

        body = json.dumps(SHOPIFY_PAYLOAD).encode()
        sig = hmac_lib.new(
            'shpss_secret'.encode(), body, hashlib.sha256
        ).hexdigest()

        resp = anon_client.post(
            shopify_url(client_obj.id),
            data=body,
            content_type='application/json',
            HTTP_X_SHOPIFY_HMAC_SHA256=sig,
        )
        assert resp.status_code == 202

    @patch('scraper.tasks.re_embed_product.delay')
    def test_shopify_hmac_verification_fail(self, mock_task, anon_client, client_obj):
        client_obj.webhook_secret = 'shpss_secret'
        client_obj.save()

        resp = anon_client.post(
            shopify_url(client_obj.id),
            data=SHOPIFY_PAYLOAD,
            format='json',
            HTTP_X_SHOPIFY_HMAC_SHA256='badsig',
        )
        assert resp.status_code == 401
        mock_task.assert_not_called()


# ─── WooCommerce Webhook ──────────────────────────────────────────────────────

@pytest.mark.django_db
class TestWooCommerceWebhook:
    @patch('scraper.tasks.re_embed_product.delay')
    def test_woo_valid_payload(self, mock_task, anon_client, client_obj):
        resp = anon_client.post(woo_url(client_obj.id), WOOCOMMERCE_PAYLOAD, format='json')
        assert resp.status_code == 202
        assert resp.json()['status'] == 'queued'
        mock_task.assert_called_once()

    @patch('scraper.tasks.re_embed_product.delay')
    def test_woo_missing_name(self, mock_task, anon_client, client_obj):
        payload = {k: v for k, v in WOOCOMMERCE_PAYLOAD.items() if k != 'name'}
        resp = anon_client.post(woo_url(client_obj.id), payload, format='json')
        assert resp.status_code == 400
        mock_task.assert_not_called()

    def test_woo_unknown_client(self, anon_client):
        resp = anon_client.post(woo_url(uuid.uuid4()), WOOCOMMERCE_PAYLOAD, format='json')
        assert resp.status_code == 404


# ─── WordPress Webhook ────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestWordPressWebhook:
    @patch('scraper.tasks.re_embed_wordpress_post.delay')
    def test_wp_valid_payload(self, mock_task, anon_client, client_obj):
        resp = anon_client.post(wp_url(client_obj.id), WORDPRESS_PAYLOAD, format='json')
        assert resp.status_code == 202
        assert resp.json()['status'] == 'queued'
        mock_task.assert_called_once()

    @patch('scraper.tasks.re_embed_wordpress_post.delay')
    def test_wp_no_post_id(self, mock_task, anon_client, client_obj):
        payload = {k: v for k, v in WORDPRESS_PAYLOAD.items() if k != 'id'}
        resp = anon_client.post(wp_url(client_obj.id), payload, format='json')
        assert resp.status_code == 400
        mock_task.assert_not_called()

    @patch('scraper.tasks.re_embed_wordpress_post.delay')
    def test_wp_no_title(self, mock_task, anon_client, client_obj):
        payload = {**WORDPRESS_PAYLOAD, 'title': {'rendered': ''}}
        resp = anon_client.post(wp_url(client_obj.id), payload, format='json')
        assert resp.status_code == 400

    def test_wp_unknown_client(self, anon_client):
        resp = anon_client.post(wp_url(uuid.uuid4()), WORDPRESS_PAYLOAD, format='json')
        assert resp.status_code == 404

    @patch('scraper.tasks.re_embed_wordpress_post.delay')
    def test_wp_flat_payload_format(self, mock_task, anon_client, client_obj):
        """Supports flat payload format used by some WP webhook plugins."""
        payload = {
            'id': 222,
            'post_title': 'Flat Title',
            'post_content': '<p>Flat content</p>',
            'guid': 'https://wp.com/flat-post',
        }
        resp = anon_client.post(wp_url(client_obj.id), payload, format='json')
        assert resp.status_code == 202
