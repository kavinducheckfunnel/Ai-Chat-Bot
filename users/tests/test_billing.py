"""
Tests for billing endpoints and Stripe webhook handling:
  GET  /api/admin/billing/subscription/
  POST /api/admin/billing/checkout/
  POST /api/admin/billing/portal/
  POST /api/admin/billing/webhook/
  GET  /api/admin/billing/plans/
"""
import json
import pytest
from unittest.mock import patch, MagicMock
from rest_framework.test import APIClient

from users.models import Plan, TenantProfile


SUBSCRIPTION_URL = '/api/admin/billing/subscription/'
CHECKOUT_URL = '/api/admin/billing/checkout/'
PORTAL_URL = '/api/admin/billing/portal/'
WEBHOOK_URL = '/api/admin/billing/webhook/'
PLANS_URL = '/api/admin/billing/plans/'


# ─── Public plan list ─────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestPublicPlans:
    def test_plans_public_no_auth(self, anon_client, free_plan, growth_plan):
        resp = anon_client.get(PLANS_URL)
        assert resp.status_code == 200
        names = [p['name'] for p in resp.json()]
        assert 'Free' in names
        assert 'Growth' in names

    def test_plans_include_features(self, anon_client, growth_plan):
        resp = anon_client.get(PLANS_URL)
        assert resp.status_code == 200
        plan = next(p for p in resp.json() if p['name'] == 'Growth')
        assert 'allow_whatsapp' in plan
        assert plan['allow_whatsapp'] is True


# ─── Subscription status ──────────────────────────────────────────────────────

@pytest.mark.django_db
class TestGetSubscription:
    def test_subscription_unauthenticated(self, anon_client):
        resp = anon_client.get(SUBSCRIPTION_URL)
        assert resp.status_code == 401

    def test_subscription_no_plan(self, tenant_client, tenant_user):
        tenant_user.tenant_profile.plan = None
        tenant_user.tenant_profile.save()
        resp = tenant_client.get(SUBSCRIPTION_URL)
        assert resp.status_code == 200
        assert resp.json()['plan'] is None

    def test_subscription_with_plan(self, tenant_client, tenant_user, free_plan):
        resp = tenant_client.get(SUBSCRIPTION_URL)
        assert resp.status_code == 200
        data = resp.json()
        assert data['plan']['name'] == 'Free'
        assert 'usage' in data

    def test_subscription_with_stripe_id(self, tenant_client, tenant_user):
        tp = tenant_user.tenant_profile
        tp.stripe_customer_id = 'cus_abc123'
        tp.stripe_subscription_id = 'sub_xyz789'
        tp.stripe_subscription_status = 'active'
        tp.save()
        resp = tenant_client.get(SUBSCRIPTION_URL)
        assert resp.status_code == 200
        data = resp.json()
        assert data['stripe_subscription_status'] == 'active'


# ─── Checkout session ─────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestCreateCheckout:
    @patch('users.billing_views._stripe')
    def test_checkout_valid(self, mock_stripe_fn, tenant_client, tenant_user, growth_plan):
        mock_s = MagicMock()
        mock_stripe_fn.return_value = mock_s
        mock_s.Customer.create.return_value = {'id': 'cus_newtest'}
        mock_s.checkout.Session.create.return_value = {'url': 'https://checkout.stripe.com/pay/test'}

        resp = tenant_client.post(CHECKOUT_URL, {'plan_id': growth_plan.id}, format='json')
        assert resp.status_code == 200
        assert 'url' in resp.json()

    def test_checkout_missing_plan_id(self, tenant_client):
        resp = tenant_client.post(CHECKOUT_URL, {}, format='json')
        assert resp.status_code == 400

    def test_checkout_invalid_plan_id(self, tenant_client):
        resp = tenant_client.post(CHECKOUT_URL, {'plan_id': 999999}, format='json')
        assert resp.status_code == 404

    def test_checkout_plan_no_stripe_price(self, tenant_client, tenant_user, free_plan):
        # free_plan has no stripe_price_id
        resp = tenant_client.post(CHECKOUT_URL, {'plan_id': free_plan.id}, format='json')
        assert resp.status_code == 400

    def test_checkout_unauthenticated(self, anon_client, growth_plan):
        resp = anon_client.post(CHECKOUT_URL, {'plan_id': growth_plan.id}, format='json')
        assert resp.status_code == 401


# ─── Billing portal ───────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestCreatePortal:
    @patch('users.billing_views._stripe')
    def test_portal_valid(self, mock_stripe_fn, tenant_client, tenant_user):
        mock_s = MagicMock()
        mock_stripe_fn.return_value = mock_s
        mock_s.billing_portal.Session.create.return_value = {'url': 'https://billing.stripe.com/portal/test'}

        tp = tenant_user.tenant_profile
        tp.stripe_customer_id = 'cus_abc123'
        tp.save()

        resp = tenant_client.post(PORTAL_URL)
        assert resp.status_code == 200
        assert 'url' in resp.json()

    def test_portal_no_stripe_customer(self, tenant_client, tenant_user):
        # No stripe_customer_id set
        tenant_user.tenant_profile.stripe_customer_id = None
        tenant_user.tenant_profile.save()
        resp = tenant_client.post(PORTAL_URL)
        assert resp.status_code == 400

    def test_portal_unauthenticated(self, anon_client):
        resp = anon_client.post(PORTAL_URL)
        assert resp.status_code == 401


# ─── Stripe Webhook ───────────────────────────────────────────────────────────

def _make_stripe_event(event_type, data_object):
    return {
        'type': event_type,
        'data': {'object': data_object},
    }


@pytest.mark.django_db
class TestStripeWebhook:
    @patch('users.billing_views._stripe')
    def test_webhook_invalid_signature(self, mock_stripe_fn, anon_client):
        import stripe as real_stripe
        mock_s = MagicMock()
        mock_stripe_fn.return_value = mock_s
        # Wire the real exception class so the `except s.error.SignatureVerificationError`
        # clause in billing_views can match the real exception being raised.
        mock_s.error.SignatureVerificationError = real_stripe.error.SignatureVerificationError
        mock_s.Webhook.construct_event.side_effect = real_stripe.error.SignatureVerificationError(
            'bad sig', 'sig_header'
        )
        resp = anon_client.post(
            WEBHOOK_URL,
            data=b'{}',
            content_type='application/json',
            HTTP_STRIPE_SIGNATURE='bad',
        )
        assert resp.status_code == 400

    @patch('users.billing_views._stripe')
    def test_webhook_checkout_completed(self, mock_stripe_fn, anon_client, tenant_user, growth_plan):
        mock_s = MagicMock()
        mock_stripe_fn.return_value = mock_s
        tp = tenant_user.tenant_profile
        event_obj = {
            'metadata': {
                'tenant_id': str(tp.pk),
                'plan_id': str(growth_plan.pk),
            },
            'subscription': 'sub_abc123',
        }
        mock_s.Webhook.construct_event.return_value = _make_stripe_event(
            'checkout.session.completed', event_obj
        )

        resp = anon_client.post(
            WEBHOOK_URL,
            data=json.dumps(event_obj).encode(),
            content_type='application/json',
            HTTP_STRIPE_SIGNATURE='valid_sig',
        )
        assert resp.status_code == 200
        tp.refresh_from_db()
        assert tp.plan == growth_plan
        assert tp.stripe_subscription_id == 'sub_abc123'
        assert tp.stripe_subscription_status == 'active'

    @patch('users.billing_views._stripe')
    def test_webhook_subscription_updated(self, mock_stripe_fn, anon_client, tenant_user, growth_plan):
        mock_s = MagicMock()
        mock_stripe_fn.return_value = mock_s
        tp = tenant_user.tenant_profile
        tp.stripe_subscription_id = 'sub_update_test'
        tp.save()

        event_obj = {
            'id': 'sub_update_test',
            'status': 'past_due',
            'items': {'data': []},
        }
        mock_s.Webhook.construct_event.return_value = _make_stripe_event(
            'customer.subscription.updated', event_obj
        )

        resp = anon_client.post(
            WEBHOOK_URL,
            data=json.dumps(event_obj).encode(),
            content_type='application/json',
            HTTP_STRIPE_SIGNATURE='valid_sig',
        )
        assert resp.status_code == 200
        tp.refresh_from_db()
        assert tp.stripe_subscription_status == 'past_due'

    @patch('users.billing_views._stripe')
    def test_webhook_subscription_deleted(self, mock_stripe_fn, anon_client, tenant_user, free_plan):
        mock_s = MagicMock()
        mock_stripe_fn.return_value = mock_s
        tp = tenant_user.tenant_profile
        tp.stripe_subscription_id = 'sub_cancel_test'
        tp.save()

        event_obj = {'id': 'sub_cancel_test'}
        mock_s.Webhook.construct_event.return_value = _make_stripe_event(
            'customer.subscription.deleted', event_obj
        )

        resp = anon_client.post(
            WEBHOOK_URL,
            data=json.dumps(event_obj).encode(),
            content_type='application/json',
            HTTP_STRIPE_SIGNATURE='valid_sig',
        )
        assert resp.status_code == 200
        tp.refresh_from_db()
        assert tp.stripe_subscription_status == 'canceled'
        assert tp.stripe_subscription_id is None

    @patch('users.billing_views._stripe')
    def test_webhook_payment_failed(self, mock_stripe_fn, anon_client, tenant_user):
        mock_s = MagicMock()
        mock_stripe_fn.return_value = mock_s
        tp = tenant_user.tenant_profile
        tp.stripe_subscription_id = 'sub_fail_test'
        tp.save()

        event_obj = {'subscription': 'sub_fail_test'}
        mock_s.Webhook.construct_event.return_value = _make_stripe_event(
            'invoice.payment_failed', event_obj
        )

        resp = anon_client.post(
            WEBHOOK_URL,
            data=json.dumps(event_obj).encode(),
            content_type='application/json',
            HTTP_STRIPE_SIGNATURE='valid_sig',
        )
        assert resp.status_code == 200
        tp.refresh_from_db()
        assert tp.stripe_subscription_status == 'past_due'
