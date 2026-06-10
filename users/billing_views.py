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
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import AddOnPurchase, Plan, TenantProfile

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
            'stripe_price_id': p.stripe_price_id or '',
            'stripe_price_id_annual': p.stripe_price_id_annual or '',
            'max_clients': p.max_clients,
            'max_sessions_per_month': p.max_sessions_per_month,
            'max_messages_per_month': p.max_messages_per_month,
            'max_images_per_month': p.max_images_per_month,
            'max_voice_per_month': p.max_voice_per_month,
            'max_dashboard_metrics': p.max_dashboard_metrics,
            'max_social_channels': p.max_social_channels,
            'data_retention_days': p.data_retention_days,
            'allow_whatsapp': p.allow_whatsapp,
            'allow_telegram': p.allow_telegram,
            'allow_messenger': p.allow_messenger,
            'allow_byok': p.allow_byok,
            'allow_hubspot': p.allow_hubspot,
            'allow_voice_input': p.allow_voice_input,
            'allow_image_input': p.allow_image_input,
            'allow_real_time_inventory': p.allow_real_time_inventory,
            'allow_custom_domain': p.allow_custom_domain,
            'allow_god_view': p.allow_god_view,
            'allow_csv_export': p.allow_csv_export,
            'remove_branding': p.remove_branding,
            'allow_advanced_reports': p.allow_advanced_reports,
            'priority_support': p.priority_support,
        })
    return Response(data)


# ── Current subscription status ──────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_subscription(request):
    """Return the tenant's current plan + Stripe subscription status.

    Self-heals if the local tenant.plan is NULL but a live Stripe
    subscription exists. This handles a known race condition: a user
    completes Stripe checkout, immediately navigates back to /portal/billing,
    but the checkout.session.completed webhook hasn't landed yet so
    tenant.plan is still NULL — the page would show "No plan".
    """
    try:
        tenant = request.user.tenant_profile
    except TenantProfile.DoesNotExist:
        return Response({'plan': None, 'status': None})

    from users.feature_flags import usage_summary
    plan = tenant.plan

    # ── Self-heal missing plan from Stripe ────────────────────────────
    if plan is None and tenant.stripe_subscription_id:
        try:
            s = _stripe()
            sub = s.Subscription.retrieve(tenant.stripe_subscription_id)
            price_id = sub['items']['data'][0]['price']['id']
            resolved = Plan.objects.filter(
                Q(stripe_price_id=price_id) | Q(stripe_price_id_annual=price_id)
            ).first()
            if resolved:
                tenant.plan = resolved
                tenant.stripe_subscription_status = sub.get('status') or 'active'
                tenant.save(update_fields=['plan', 'stripe_subscription_status'])
                plan = resolved
                logger.info(
                    f'[get_subscription] Self-healed plan for tenant {tenant.id} '
                    f'from Stripe price {price_id} → {resolved.name}'
                )
        except Exception as e:
            logger.warning(f'[get_subscription] Self-heal failed for tenant {tenant.id}: {e}')

    def _plan_data(p):
        if not p:
            return None
        return {
            'id': p.id,
            'name': p.name,
            'price_monthly': str(p.price_monthly),
            'max_sessions_per_month': p.max_sessions_per_month,
            'max_clients': p.max_clients,
            'max_messages_per_month': p.max_messages_per_month,
            'max_images_per_month': p.max_images_per_month,
            'max_voice_per_month': p.max_voice_per_month,
            'max_dashboard_metrics': p.max_dashboard_metrics,
            'data_retention_days': p.data_retention_days,
        }

    return Response({
        'plan': _plan_data(plan),
        'stripe_customer_id': tenant.stripe_customer_id,
        'stripe_subscription_id': tenant.stripe_subscription_id,
        'stripe_subscription_status': tenant.stripe_subscription_status,
        'billing_interval': tenant.billing_interval,
        'trial_ends_at': tenant.trial_ends_at.isoformat() if tenant.trial_ends_at else None,
        'sessions_this_month': tenant.sessions_this_month,
        'usage': usage_summary(request.user),
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
            # Route by purchase_type — subscription checkouts vs one-time addons
            ptype = (data.get('metadata') or {}).get('purchase_type', '')
            if ptype == 'addon':
                _handle_addon_checkout_completed(data)
            else:
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


# ──────────────────────────────────────────────────────────────────────────────
# F7 — Ad-hoc add-on top-ups (one-time purchases for extra
# messages / images / voice / video credits when plan quota is exhausted)
# ──────────────────────────────────────────────────────────────────────────────

ADDON_KIND_TO_PLAN_PRICE_FIELD = {
    'message': 'addon_price_per_message',
    'image':   'addon_price_per_image',
    'voice':   'addon_price_per_voice',
    'video':   'addon_price_per_video',
}

ADDON_BUNDLES = {
    # Suggested bundle sizes shown in the UI. Tenant picks one OR enters
    # a custom quantity. Backend validates against >0 and <=10000.
    'message': [100, 500, 2000],
    'image':   [25, 100, 500],
    'voice':   [25, 100, 500],
    'video':   [10, 50, 200],
}


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_addon_options(request):
    """Return per-unit prices + suggested bundle sizes for the UI."""
    try:
        tenant = request.user.tenant_profile
    except TenantProfile.DoesNotExist:
        return Response({'detail': 'No tenant profile.'}, status=400)
    plan = tenant.plan
    if not plan:
        return Response({'detail': 'No plan assigned. Choose a plan first.'}, status=400)
    return Response({
        'prices': {
            'message': str(plan.addon_price_per_message),
            'image':   str(plan.addon_price_per_image),
            'voice':   str(plan.addon_price_per_voice),
            'video':   str(plan.addon_price_per_video),
        },
        'bundles': ADDON_BUNDLES,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def purchase_addon(request):
    """Create a Stripe one-time Checkout session for an add-on top-up.

    Body: { kind: 'message'|'image'|'voice'|'video', quantity: int }
    Returns: { url: str, purchase_id: int }
    """
    s = _stripe()
    kind = (request.data.get('kind') or '').strip().lower()
    quantity = request.data.get('quantity')

    if kind not in ADDON_KIND_TO_PLAN_PRICE_FIELD:
        return Response({'detail': "kind must be one of: message, image, voice, video"}, status=400)
    try:
        quantity = int(quantity)
    except (TypeError, ValueError):
        return Response({'detail': 'quantity must be an integer'}, status=400)
    if quantity < 1 or quantity > 10000:
        return Response({'detail': 'quantity must be between 1 and 10000'}, status=400)

    try:
        tenant = request.user.tenant_profile
    except TenantProfile.DoesNotExist:
        return Response({'detail': 'No tenant profile.'}, status=400)
    plan = tenant.plan
    if not plan:
        return Response({'detail': 'No plan assigned. Choose a plan first.'}, status=400)

    # Hard pre-check: if Stripe isn't configured at all on this environment,
    # surface the real problem instead of "Could not create billing account."
    if not getattr(settings, 'STRIPE_SECRET_KEY', ''):
        logger.error('[billing] STRIPE_SECRET_KEY not configured — add-on purchase impossible')
        return Response({
            'detail': 'Stripe payments are not configured on this instance yet. Contact support to enable add-on purchases, or request a manual credit grant from your account manager.',
            'code': 'stripe_not_configured',
        }, status=503)

    unit_price = getattr(plan, ADDON_KIND_TO_PLAN_PRICE_FIELD[kind])
    total_cents = int(round(float(unit_price) * quantity * 100))
    if total_cents < 50:  # Stripe minimum $0.50
        return Response({'detail': 'Total below Stripe minimum charge ($0.50). Increase quantity.'}, status=400)

    # Ensure Stripe customer
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

    # Create audit row BEFORE Stripe Checkout so we can correlate via metadata
    purchase = AddOnPurchase.objects.create(
        tenant=tenant,
        kind=kind,
        quantity=quantity,
        unit_price_usd=unit_price,
        status='pending',
    )

    base_url = settings.STRIPE_PORTAL_RETURN_URL.replace('/billing', '')
    try:
        session = s.checkout.Session.create(
            customer=customer_id,
            payment_method_types=['card'],
            mode='payment',  # one-time, NOT subscription
            line_items=[{
                'quantity': 1,
                'price_data': {
                    'currency': 'usd',
                    'unit_amount': total_cents,
                    'product_data': {
                        'name': f'Checkfunnel — {quantity} {kind} credits',
                        'description': f'One-time top-up at ${unit_price}/{kind}',
                    },
                },
            }],
            success_url=f'{base_url}/portal/billing?addon_purchased={purchase.id}',
            cancel_url=f'{base_url}/portal/billing',
            metadata={
                'purchase_type': 'addon',
                'tenant_id': str(tenant.pk),
                'purchase_id': str(purchase.id),
                'kind': kind,
                'quantity': str(quantity),
            },
            payment_intent_data={
                'metadata': {
                    'purchase_type': 'addon',
                    'tenant_id': str(tenant.pk),
                    'purchase_id': str(purchase.id),
                    'kind': kind,
                    'quantity': str(quantity),
                }
            },
        )
        purchase.stripe_checkout_session_id = session['id']
        purchase.save(update_fields=['stripe_checkout_session_id'])
    except s.error.StripeError as e:
        purchase.status = 'failed'
        purchase.notes = str(e)[:255]
        purchase.save(update_fields=['status', 'notes'])
        logger.error(f'[billing] Add-on checkout create failed: {e}')
        return Response({'detail': 'Could not start checkout. Please try again.'}, status=500)

    return Response({'url': session['url'], 'purchase_id': purchase.id})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def grant_addon_credits(request):
    """SUPER-ADMIN ONLY — manually grant add-on credits to a tenant.

    Used when Stripe payments aren't configured yet, when a tenant needs
    a courtesy credit, or when an out-of-band payment was received. Creates
    a 'succeeded' AddOnPurchase row marked notes='manual grant by <admin>'
    for audit. Increments TenantProfile.addon_<kind> atomically.

    Body: { tenant_id: int, kind: str, quantity: int, reason: str (optional) }
    """
    if not request.user.is_superuser:
        return Response({'detail': 'Super-admin only.'}, status=403)

    from django.utils import timezone
    from django.db.models import F

    tenant_id = request.data.get('tenant_id')
    kind = (request.data.get('kind') or '').strip().lower()
    try:
        quantity = int(request.data.get('quantity') or 0)
    except (TypeError, ValueError):
        return Response({'detail': 'quantity must be an integer'}, status=400)
    reason = (request.data.get('reason') or 'manual grant').strip()[:240]

    if kind not in ADDON_KIND_TO_PLAN_PRICE_FIELD:
        return Response({'detail': 'kind must be one of: message, image, voice, video'}, status=400)
    if quantity < 1 or quantity > 100000:
        return Response({'detail': 'quantity must be between 1 and 100000'}, status=400)

    try:
        tenant = TenantProfile.objects.get(pk=int(tenant_id))
    except (TenantProfile.DoesNotExist, ValueError, TypeError):
        return Response({'detail': 'Tenant not found'}, status=404)

    unit_price = 0
    if tenant.plan:
        unit_price = getattr(tenant.plan, ADDON_KIND_TO_PLAN_PRICE_FIELD[kind], 0) or 0

    purchase = AddOnPurchase.objects.create(
        tenant=tenant,
        kind=kind,
        quantity=quantity,
        unit_price_usd=unit_price,
        total_paid_usd=0,                  # manual grant — no money changed hands
        status='succeeded',
        completed_at=timezone.now(),
        notes=f'Manual grant by {request.user.username}: {reason}'[:240],
    )
    field = f'addon_{kind}s'
    TenantProfile.objects.filter(pk=tenant.pk).update(**{field: F(field) + quantity})
    logger.info(f'[billing] Manual grant by {request.user.username}: tenant {tenant.id} +{quantity} {kind}')
    return Response({
        'ok': True,
        'purchase_id': purchase.id,
        'tenant_id': tenant.id,
        'kind': kind,
        'quantity': quantity,
    })


def _handle_addon_checkout_completed(session):
    """Stripe webhook handler — credit the tenant after Stripe confirms payment.

    Idempotent: if the purchase_id row is already 'succeeded', no-op. This is
    important because Stripe can re-deliver events.
    """
    from django.utils import timezone
    meta = session.get('metadata', {}) or {}
    if meta.get('purchase_type') != 'addon':
        return
    purchase_id = meta.get('purchase_id')
    if not purchase_id:
        return
    try:
        purchase = AddOnPurchase.objects.select_related('tenant').get(pk=int(purchase_id))
    except (AddOnPurchase.DoesNotExist, ValueError):
        logger.warning(f'[billing] addon webhook — purchase {purchase_id} not found')
        return
    if purchase.status == 'succeeded':
        return  # idempotent

    tenant = purchase.tenant
    field = f'addon_{purchase.kind}s'  # addon_messages, addon_images, addon_voice, addon_videos
    # Atomic increment via F() so concurrent webhook deliveries can't race.
    from django.db.models import F
    TenantProfile.objects.filter(pk=tenant.pk).update(**{field: F(field) + purchase.quantity})

    payment_intent_id = session.get('payment_intent') or ''
    total_paid = (session.get('amount_total') or 0) / 100.0
    purchase.status = 'succeeded'
    purchase.completed_at = timezone.now()
    purchase.stripe_payment_intent_id = payment_intent_id or None
    purchase.total_paid_usd = total_paid
    purchase.save(update_fields=['status', 'completed_at', 'stripe_payment_intent_id', 'total_paid_usd'])
    logger.info(
        f'[billing] Add-on succeeded: tenant {tenant.pk} +{purchase.quantity} {purchase.kind} '
        f'(${total_paid:.2f}) intent={payment_intent_id}'
    )




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


# ──────────────────────────────────────────────────────────────────────────────
# Invoices — list, view (HTML), download (HTML), send test email
# ──────────────────────────────────────────────────────────────────────────────

def _invoice_signer():
    """Time-bounded URL signer for the public view + PDF endpoints."""
    from django.core.signing import TimestampSigner
    return TimestampSigner(salt='invoice-view-v1')


def _public_origin() -> str:
    """Absolute origin used when building links the email needs to embed."""
    from django.conf import settings as dj_settings
    origin = getattr(dj_settings, 'BACKEND_PUBLIC_URL', '') or 'https://ai.checkfunnels.com'
    return origin.rstrip('/')


def _invoice_signed_url(invoice_id) -> str:
    """Signed relative URL for the HTML invoice view (1h TTL)."""
    token = _invoice_signer().sign(str(invoice_id))
    return f'/api/admin/billing/invoices/{invoice_id}/html/?token={token}'


def _invoice_signed_pdf_url(invoice_id) -> str:
    """Signed relative URL for the PDF invoice download (1h TTL)."""
    token = _invoice_signer().sign(str(invoice_id))
    return f'/api/admin/billing/invoices/{invoice_id}/pdf/?token={token}'


def _conversations_dashboard_url(period_start, period_end, client_id=None) -> str:
    """Deep-link into the portal inbox filtered to the invoice's month.

    Auth happens through the portal's normal JWT flow — the tenant clicks
    the link, lands at /portal/inbox?from=YYYY-MM-DD&to=YYYY-MM-DD, the
    portal reads the query params and asks the API for those sessions.
    No signing here because anyone with the link still has to log in.
    """
    qs = f'from={period_start.isoformat()}&to={period_end.isoformat()}'
    if client_id:
        qs += f'&client={client_id}'
    return f'/portal/inbox?{qs}'


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_invoices(request):
    """Tenant-facing list of their past invoices."""
    from users.models import Invoice
    try:
        tenant = request.user.tenant_profile
    except TenantProfile.DoesNotExist:
        return Response([])

    invoices = Invoice.objects.filter(tenant=tenant)[:24]  # 2 years of monthly
    return Response([
        {
            'id':              str(inv.id),
            'invoice_number':  inv.invoice_number,
            'period_start':    inv.period_start.isoformat(),
            'period_end':      inv.period_end.isoformat(),
            'subtotal_usd':    str(inv.subtotal_usd),
            'total_usd':       str(inv.total_usd),
            'status':          inv.status,
            'created_at':      inv.created_at.isoformat(),
            'sent_at':         inv.sent_at.isoformat() if inv.sent_at else None,
            # Signed URLs (valid 1h) — open in a new tab / direct download
            # without needing the JWT Authorization header that browser-tab
            # navigations can't carry. Frontend uses these directly as href.
            'download_url':    _invoice_signed_url(inv.id),     # HTML view
            'pdf_url':         _invoice_signed_pdf_url(inv.id),  # PDF download
        }
        for inv in invoices
    ])


@api_view(['GET'])
@permission_classes([AllowAny])  # auth happens via signed token below
def view_invoice_html(request, invoice_id):
    """Return the rendered invoice HTML.

    Auth model: requires either
      (a) a valid signed `?token=…` (issued by list_invoices, 1h TTL), OR
      (b) an authenticated tenant who owns the invoice (Authorization header)

    Why both: option (a) makes the URL openable in a new tab / from an
    email link without the browser carrying an Authorization header.
    Option (b) lets internal/API consumers fetch via the normal session.
    """
    from django.core.signing import BadSignature, SignatureExpired
    from django.http import HttpResponse
    from users.models import Invoice
    from users.invoice_service import render_invoice_html

    invoice = Invoice.objects.filter(pk=invoice_id).select_related('tenant').first()
    if not invoice:
        return Response({'detail': 'Invoice not found.'}, status=404)

    # Path (a): signed token in the URL — 1h TTL.
    token = request.query_params.get('token')
    if token:
        try:
            verified_id = _invoice_signer().unsign(token, max_age=3600)
            if verified_id != str(invoice_id):
                return Response({'detail': 'Token mismatch.'}, status=403)
        except SignatureExpired:
            return Response({'detail': 'Invoice link has expired. Open it from /portal/billing again.'}, status=403)
        except BadSignature:
            return Response({'detail': 'Invalid token.'}, status=403)
    else:
        # Path (b): JWT-authenticated tenant who owns this invoice
        if not request.user.is_authenticated:
            return Response({'detail': 'Authentication required (or use a signed link).'}, status=401)
        try:
            tenant = request.user.tenant_profile
        except TenantProfile.DoesNotExist:
            return Response({'detail': 'No tenant profile.'}, status=403)
        if invoice.tenant_id != tenant.id and not request.user.is_superuser:
            return Response({'detail': 'Not your invoice.'}, status=403)

    html = render_invoice_html(invoice)
    response = HttpResponse(html, content_type='text/html; charset=utf-8')
    response['Content-Disposition'] = f'inline; filename="{invoice.invoice_number}.html"'
    response['X-Content-Type-Options'] = 'nosniff'
    return response


@api_view(['GET'])
@permission_classes([AllowAny])  # auth via signed token below (mirrors HTML view)
def view_invoice_pdf(request, invoice_id):
    """Return the invoice as a downloadable PDF.

    Same dual-auth model as `view_invoice_html`:
      (a) signed `?token=…` (1h TTL) — used by the email "Download PDF"
          button so customers don't need to be logged in their email client
      (b) authenticated tenant who owns this invoice
    """
    from django.core.signing import BadSignature, SignatureExpired
    from django.http import HttpResponse
    from users.models import Invoice
    from users.invoice_service import render_invoice_pdf

    invoice = Invoice.objects.filter(pk=invoice_id).select_related('tenant').first()
    if not invoice:
        return Response({'detail': 'Invoice not found.'}, status=404)

    token = request.query_params.get('token')
    if token:
        try:
            verified_id = _invoice_signer().unsign(token, max_age=3600)
            if verified_id != str(invoice_id):
                return Response({'detail': 'Token mismatch.'}, status=403)
        except SignatureExpired:
            return Response(
                {'detail': 'Invoice link has expired. Open it from /portal/billing again.'},
                status=403,
            )
        except BadSignature:
            return Response({'detail': 'Invalid token.'}, status=403)
    else:
        if not request.user.is_authenticated:
            return Response({'detail': 'Authentication required (or use a signed link).'}, status=401)
        try:
            tenant = request.user.tenant_profile
        except TenantProfile.DoesNotExist:
            return Response({'detail': 'No tenant profile.'}, status=403)
        if invoice.tenant_id != tenant.id and not request.user.is_superuser:
            return Response({'detail': 'Not your invoice.'}, status=403)

    try:
        pdf_bytes = render_invoice_pdf(invoice)
    except Exception as e:
        logger.exception(f'[invoice] PDF render failed for {invoice.invoice_number}: {e}')
        return Response(
            {'detail': 'PDF generation is not available right now. '
                       'Open the HTML invoice and print to PDF as a workaround.'},
            status=503,
        )

    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    # `attachment` triggers a download; the email button gets the file
    # named `Invoice-CF-0001-202605-01.pdf` in their downloads folder.
    response['Content-Disposition'] = (
        f'attachment; filename="Invoice-{invoice.invoice_number}.pdf"'
    )
    response['X-Content-Type-Options'] = 'nosniff'
    return response


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_test_invoice(request):
    """Generate (or fetch) the current month's invoice for this tenant and email it.

    Used by the tenant to preview what their monthly invoice email looks like
    without waiting for the cron. Optional body: { to: '<override email>' }
    """
    from users.models import Invoice
    from users.invoice_service import generate_invoice, email_invoice
    from datetime import date

    try:
        tenant = request.user.tenant_profile
    except TenantProfile.DoesNotExist:
        return Response({'detail': 'No tenant profile.'}, status=403)

    today = date.today()
    invoice = generate_invoice(tenant, today.year, today.month, force=True, status='sent')

    override_to = (request.data.get('to') or '').strip() or None

    # Build the three CTA links the email shell needs. Use the tenant's
    # first client for the conversations deep-link so the visitor lands
    # on the right inbox if they manage multiple sites.
    from users.invoice_service import _primary_client
    primary = _primary_client(tenant)
    origin = _public_origin()
    ok = email_invoice(
        invoice,
        to_email=override_to,
        pdf_url=f'{origin}{_invoice_signed_pdf_url(invoice.id)}',
        view_html_url=f'{origin}{_invoice_signed_url(invoice.id)}',
        conversations_url=f'{origin}{_conversations_dashboard_url(invoice.period_start, invoice.period_end, primary.id if primary else None)}',
    )
    if not ok:
        return Response({
            'detail': 'Email send failed — check SMTP configuration. Invoice was still generated.',
            'invoice_id': str(invoice.id),
        }, status=502)

    return Response({
        'ok': True,
        'invoice_id': str(invoice.id),
        'invoice_number': invoice.invoice_number,
        'sent_to': override_to or invoice.recipient_email_at_issue,
    })
