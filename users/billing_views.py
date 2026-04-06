"""
Stripe billing endpoints.

Flow:
1. Tenant clicks "Upgrade" → POST /billing/checkout/ { plan_id } → returns { url }
   → redirect to Stripe Checkout
2. Stripe redirects back to /portal/billing?session_id=...
3. Stripe fires webhook → /billing/webhook/ → updates TenantProfile fields
4. Tenant clicks "Manage billing" → POST /billing/portal/ → returns { url }
   → redirect to Stripe Customer Portal
"""

import logging

import stripe
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import Plan, TenantProfile

logger = logging.getLogger(__name__)


def _stripe():
    """Initialise stripe with the secret key and return the module."""
    stripe.api_key = settings.STRIPE_SECRET_KEY
    return stripe


# ── Public plan list (used on billing page before login too) ─────────────────

@api_view(['GET'])
@permission_classes([AllowAny])
def public_plans(request):
    """Return all plans that have a stripe_price_id (i.e. purchasable)."""
    plans = Plan.objects.all().order_by('price_monthly')
    data = []
    for p in plans:
        data.append({
            'id': p.id,
            'name': p.name,
            'price_monthly': str(p.price_monthly),
            'max_sessions_per_month': p.max_sessions_per_month,
            'max_clients': p.max_clients,
            'stripe_price_id': p.stripe_price_id or '',
        })
    return Response(data)


# ── Current subscription status ──────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_subscription(request):
    """Return the tenant's current plan + Stripe subscription status."""
    try:
        tenant = request.user.tenant_profile
    except TenantProfile.DoesNotExist:
        return Response({'plan': None, 'status': None})

    plan = tenant.plan
    return Response({
        'plan': {
            'id': plan.id,
            'name': plan.name,
            'price_monthly': str(plan.price_monthly),
            'max_sessions_per_month': plan.max_sessions_per_month,
            'max_clients': plan.max_clients,
        } if plan else None,
        'stripe_customer_id': tenant.stripe_customer_id,
        'stripe_subscription_id': tenant.stripe_subscription_id,
        'stripe_subscription_status': tenant.stripe_subscription_status,
        'trial_ends_at': tenant.trial_ends_at.isoformat() if tenant.trial_ends_at else None,
        'sessions_this_month': tenant.sessions_this_month,
    })


# ── Create Stripe Checkout session ───────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_checkout_session(request):
    """
    Creates a Stripe Checkout session for a plan upgrade.
    Body: { plan_id: int }
    Returns: { url: str }
    """
    s = _stripe()

    plan_id = request.data.get('plan_id')
    if not plan_id:
        return Response({'detail': 'plan_id is required.'}, status=400)

    try:
        plan = Plan.objects.get(pk=plan_id)
    except Plan.DoesNotExist:
        return Response({'detail': 'Plan not found.'}, status=404)

    if not plan.stripe_price_id:
        return Response({'detail': 'This plan is not available for purchase yet.'}, status=400)

    try:
        tenant = request.user.tenant_profile
    except TenantProfile.DoesNotExist:
        return Response({'detail': 'No tenant profile found.'}, status=400)

    # Ensure Stripe customer exists
    customer_id = tenant.stripe_customer_id
    if not customer_id:
        try:
            customer = s.Customer.create(
                email=request.user.email,
                name=tenant.company_name or request.user.username,
                metadata={'tenant_id': str(tenant.pk), 'user_id': str(request.user.pk)},
            )
            tenant.stripe_customer_id = customer['id']
            tenant.save(update_fields=['stripe_customer_id'])
            customer_id = customer['id']
        except s.error.StripeError as e:
            logger.error(f'[billing] Stripe customer create failed: {e}')
            return Response({'detail': 'Could not create billing account.'}, status=500)

    base_url = settings.STRIPE_PORTAL_RETURN_URL.replace('/billing', '')
    try:
        session = s.checkout.Session.create(
            customer=customer_id,
            payment_method_types=['card'],
            line_items=[{'price': plan.stripe_price_id, 'quantity': 1}],
            mode='subscription',
            success_url=f'{base_url}/portal/billing?session_id={{CHECKOUT_SESSION_ID}}',
            cancel_url=f'{base_url}/portal/billing',
            metadata={
                'tenant_id': str(tenant.pk),
                'plan_id': str(plan.pk),
            },
            subscription_data={
                'metadata': {
                    'tenant_id': str(tenant.pk),
                    'plan_id': str(plan.pk),
                }
            },
        )
    except s.error.StripeError as e:
        logger.error(f'[billing] Checkout session create failed: {e}')
        return Response({'detail': 'Could not start checkout. Please try again.'}, status=500)

    return Response({'url': session['url']})


# ── Stripe Customer Portal ────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_portal_session(request):
    """
    Opens Stripe Customer Portal so the tenant can manage/cancel their subscription.
    Returns: { url: str }
    """
    s = _stripe()

    try:
        tenant = request.user.tenant_profile
    except TenantProfile.DoesNotExist:
        return Response({'detail': 'No tenant profile found.'}, status=400)

    if not tenant.stripe_customer_id:
        return Response({'detail': 'No billing account found. Please subscribe to a plan first.'}, status=400)

    try:
        session = s.billing_portal.Session.create(
            customer=tenant.stripe_customer_id,
            return_url=settings.STRIPE_PORTAL_RETURN_URL,
        )
    except s.error.StripeError as e:
        logger.error(f'[billing] Portal session create failed: {e}')
        return Response({'detail': 'Could not open billing portal.'}, status=500)

    return Response({'url': session['url']})


# ── Stripe Webhook ────────────────────────────────────────────────────────────

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def stripe_webhook(request):
    """
    Handles Stripe webhook events. Verify signature, then update TenantProfile.
    Events handled:
    - checkout.session.completed → assign plan, save subscription ID
    - customer.subscription.updated → update status
    - customer.subscription.deleted → clear subscription, revert plan
    - invoice.payment_failed → mark past_due
    """
    s = _stripe()
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')

    try:
        event = s.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except (ValueError, s.error.SignatureVerificationError) as e:
        logger.warning(f'[billing] Webhook signature verification failed: {e}')
        return Response({'detail': 'Invalid signature.'}, status=400)

    event_type = event['type']
    data = event['data']['object']

    try:
        if event_type == 'checkout.session.completed':
            _handle_checkout_completed(data)

        elif event_type == 'customer.subscription.updated':
            _handle_subscription_updated(data)

        elif event_type == 'customer.subscription.deleted':
            _handle_subscription_deleted(data)

        elif event_type == 'invoice.payment_failed':
            _handle_payment_failed(data)

    except Exception as e:
        logger.error(f'[billing] Webhook handler error ({event_type}): {e}')
        # Return 200 so Stripe doesn't retry — we log the error
        return Response({'detail': 'Handled with error.'})

    return Response({'detail': 'ok'})


def _handle_checkout_completed(session):
    tenant_id = session.get('metadata', {}).get('tenant_id')
    plan_id = session.get('metadata', {}).get('plan_id')
    subscription_id = session.get('subscription')

    if not tenant_id or not plan_id:
        return

    try:
        tenant = TenantProfile.objects.get(pk=int(tenant_id))
        plan = Plan.objects.get(pk=int(plan_id))
    except (TenantProfile.DoesNotExist, Plan.DoesNotExist, ValueError):
        logger.warning(f'[billing] checkout.completed — tenant {tenant_id} or plan {plan_id} not found')
        return

    tenant.plan = plan
    tenant.stripe_subscription_id = subscription_id
    tenant.stripe_subscription_status = 'active'
    tenant.save(update_fields=['plan', 'stripe_subscription_id', 'stripe_subscription_status'])
    logger.info(f'[billing] Tenant {tenant_id} subscribed to plan {plan.name}')


def _handle_subscription_updated(subscription):
    sub_id = subscription.get('id')
    status = subscription.get('status', '')

    try:
        tenant = TenantProfile.objects.get(stripe_subscription_id=sub_id)
    except TenantProfile.DoesNotExist:
        return

    tenant.stripe_subscription_status = status
    # If subscription was reactivated and plan changed, re-resolve via price
    items = subscription.get('items', {}).get('data', [])
    if items:
        price_id = items[0].get('price', {}).get('id')
        try:
            new_plan = Plan.objects.get(stripe_price_id=price_id)
            tenant.plan = new_plan
        except Plan.DoesNotExist:
            pass

    tenant.save(update_fields=['stripe_subscription_status', 'plan'])
    logger.info(f'[billing] Subscription {sub_id} updated → status={status}')


def _handle_subscription_deleted(subscription):
    sub_id = subscription.get('id')
    try:
        tenant = TenantProfile.objects.get(stripe_subscription_id=sub_id)
    except TenantProfile.DoesNotExist:
        return

    tenant.stripe_subscription_status = 'canceled'
    tenant.stripe_subscription_id = None
    # Revert to free plan if one exists
    try:
        free_plan = Plan.objects.get(price_monthly=0)
        tenant.plan = free_plan
    except Plan.DoesNotExist:
        tenant.plan = None

    tenant.save(update_fields=['stripe_subscription_status', 'stripe_subscription_id', 'plan'])
    logger.info(f'[billing] Subscription {sub_id} canceled for tenant {tenant.pk}')


def _handle_payment_failed(invoice):
    sub_id = invoice.get('subscription')
    if not sub_id:
        return
    try:
        tenant = TenantProfile.objects.get(stripe_subscription_id=sub_id)
        tenant.stripe_subscription_status = 'past_due'
        tenant.save(update_fields=['stripe_subscription_status'])
        logger.info(f'[billing] Payment failed for subscription {sub_id}')
    except TenantProfile.DoesNotExist:
        pass
