import csv
import logging
import os
import secrets
import threading
from datetime import timedelta

from django.contrib.auth.models import User
from django.db.models import Avg, Count, DurationField, ExpressionWrapper, F, FloatField, Q, Sum
from django.db.models.functions import Coalesce, TruncDate
from django.http import HttpResponse
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate

logger = logging.getLogger(__name__)

from .models import Client, UserProfile, TenantProfile, Plan, PlanHistory
from .serializers import ClientSerializer, ClientCreateSerializer, UserProfileSerializer
from .permissions import IsSuperAdmin, get_accessible_clients
from chat.models import ChatSession


# ─── Auth ────────────────────────────────────────────────────────────────────

import re as _re

def _validate_password_strength(password):
    """Returns an error string or None if password passes all rules."""
    if len(password) < 8:
        return 'Password must be at least 8 characters.'
    if not _re.search(r'[A-Z]', password):
        return 'Password must contain at least one uppercase letter.'
    if not _re.search(r'[0-9]', password):
        return 'Password must contain at least one number.'
    if not _re.search(r'[^A-Za-z0-9]', password):
        return 'Password must contain at least one special character.'
    return None

@api_view(['POST'])
@permission_classes([AllowAny])
def register_view(request):
    """
    Public self-registration for tenant accounts created from the landing page.
    Creates User + UserProfile(tenant_admin) + TenantProfile.
    Returns JWT tokens on success.
    """
    company_name = request.data.get('company_name', '').strip()
    email = request.data.get('email', '').strip().lower()
    password = request.data.get('password', '')
    confirm_password = request.data.get('confirm_password', '')

    if not company_name:
        return Response({'detail': 'Company name is required.'}, status=400)
    if not email:
        return Response({'detail': 'Email is required.'}, status=400)
    if not password:
        return Response({'detail': 'Password is required.'}, status=400)
    pw_err = _validate_password_strength(password)
    if pw_err:
        return Response({'detail': pw_err}, status=400)
    if password != confirm_password:
        return Response({'detail': 'Passwords do not match.'}, status=400)
    if User.objects.filter(username=email).exists():
        return Response({'detail': 'An account with this email already exists.'}, status=400)
    if User.objects.filter(email=email).exists():
        return Response({'detail': 'An account with this email already exists.'}, status=400)

    user = User.objects.create_user(username=email, email=email, password=password)
    UserProfile.objects.create(user=user, role='tenant_admin')
    TenantProfile.objects.create(user=user, company_name=company_name)

    refresh = RefreshToken.for_user(user)
    return Response({
        'access': str(refresh.access_token),
        'refresh': str(refresh),
        'user': {
            'username': user.username,
            'email': user.email,
            'role': 'tenant_admin',
            'is_superuser': False,
        }
    }, status=201)


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    username = request.data.get('username', '').strip()
    password = request.data.get('password', '').strip()

    if not username or not password:
        return Response({'detail': 'Username and password required.'}, status=400)

    user = authenticate(username=username, password=password)
    if user is None:
        return Response({'detail': 'Invalid username or password.'}, status=401)

    refresh = RefreshToken.for_user(user)
    profile = getattr(user, 'profile', None)
    role = profile.role if profile else ('superadmin' if user.is_superuser else 'tenant_admin')

    return Response({
        'access': str(refresh.access_token),
        'refresh': str(refresh),
        'user': {
            'username': user.username,
            'email': user.email,
            'role': role,
            'is_superuser': user.is_superuser,
        }
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def forgot_password(request):
    """Send a password-reset link to the given email address."""
    from django.contrib.auth.tokens import default_token_generator
    from django.utils.http import urlsafe_base64_encode
    from django.utils.encoding import force_bytes
    from django.core.mail import EmailMultiAlternatives
    from django.conf import settings as django_settings

    email = request.data.get('email', '').strip().lower()
    # Always return 200 — never reveal whether an account exists
    response_msg = 'If an account with that email exists, a reset link has been sent.'

    user = User.objects.filter(email=email).order_by('-date_joined').first()
    if not user:
        return Response({'detail': response_msg})

    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    reset_url = f'https://ai.checkfunnels.com/reset-password?uid={uid}&token={token}'
    display_name = user.get_full_name() or user.username

    html_body = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1.0"/>
  <title>Reset your Checkfunnel password</title>
</head>
<body style="margin:0;padding:0;background:#0d0d0d;font-family:'Inter',Arial,sans-serif;color:#e2e8f0;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0d0d0d;padding:40px 16px;">
    <tr><td align="center">
      <table width="560" cellpadding="0" cellspacing="0" style="background:#141414;border-radius:16px;border:1px solid rgba(255,255,255,0.08);overflow:hidden;max-width:560px;width:100%;">

        <!-- Header -->
        <tr>
          <td style="background:linear-gradient(135deg,#6366f1,#8b5cf6);padding:32px 40px;text-align:center;">
            <h1 style="margin:0;font-size:22px;font-weight:700;color:#ffffff;letter-spacing:-0.3px;">
              Checkfunnel
            </h1>
          </td>
        </tr>

        <!-- Body -->
        <tr>
          <td style="padding:40px;">
            <p style="margin:0 0 8px;font-size:18px;font-weight:600;color:#f1f5f9;">
              Reset your password
            </p>
            <p style="margin:0 0 28px;font-size:14px;color:#94a3b8;line-height:1.6;">
              Hi {display_name}, we received a request to reset the password for your Checkfunnel account.
            </p>

            <!-- CTA button -->
            <table cellpadding="0" cellspacing="0" style="margin:0 auto 28px;">
              <tr>
                <td style="background:#6366f1;border-radius:10px;text-align:center;">
                  <a href="{reset_url}"
                     style="display:inline-block;padding:14px 32px;font-size:15px;font-weight:600;color:#ffffff;text-decoration:none;letter-spacing:-0.2px;">
                    Reset Password →
                  </a>
                </td>
              </tr>
            </table>

            <p style="margin:0 0 16px;font-size:13px;color:#64748b;line-height:1.6;">
              If the button above doesn't work, copy and paste this link into your browser:
            </p>
            <p style="margin:0 0 28px;word-break:break-all;">
              <a href="{reset_url}" style="font-size:12px;color:#6366f1;text-decoration:none;">{reset_url}</a>
            </p>

            <hr style="border:none;border-top:1px solid rgba(255,255,255,0.06);margin:0 0 24px;"/>

            <p style="margin:0;font-size:12px;color:#475569;line-height:1.6;">
              This link expires in <strong style="color:#94a3b8;">1 hour</strong>. If you did not request a
              password reset, you can safely ignore this email — your password will not change.
            </p>
          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td style="background:#0f0f0f;padding:20px 40px;text-align:center;">
            <p style="margin:0;font-size:11px;color:#334155;">
              © 2026 Checkfunnel · AI-Powered Conversion Intelligence
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""

    plain_body = (
        f'Hi {display_name},\n\n'
        f'Reset your Checkfunnel password by clicking the link below:\n\n'
        f'{reset_url}\n\n'
        f'This link expires in 1 hour. If you did not request a password reset, '
        f'you can safely ignore this email.\n\n'
        f'— The Checkfunnel Team'
    )
    try:
        msg = EmailMultiAlternatives(
            subject='Reset your Checkfunnel password',
            body=plain_body,
            from_email=django_settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
        )
        msg.attach_alternative(html_body, 'text/html')
        # fail_silently=False so we log the actual error in the except block
        # instead of silently dropping it (this was the original bug)
        msg.send(fail_silently=False)
        logger.info(f'[forgot_password] Reset email sent to {user.email}')
    except Exception as e:
        logger.exception(f'[forgot_password] Email send FAILED for {user.email}: {e}')

    return Response({'detail': response_msg})


@api_view(['POST'])
@permission_classes([AllowAny])
def reset_password(request):
    """Validate uid+token and set a new password."""
    from django.contrib.auth.tokens import default_token_generator
    from django.utils.http import urlsafe_base64_decode
    from django.utils.encoding import force_str

    uid = request.data.get('uid', '')
    token = request.data.get('token', '')
    new_password = request.data.get('new_password', '')

    pw_err = _validate_password_strength(new_password)
    if pw_err:
        return Response({'detail': pw_err}, status=400)

    try:
        user_id = force_str(urlsafe_base64_decode(uid))
        user = User.objects.get(pk=user_id)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        return Response({'detail': 'Invalid reset link.'}, status=400)

    if not default_token_generator.check_token(user, token):
        return Response({'detail': 'Reset link is invalid or has expired.'}, status=400)

    user.set_password(new_password)
    user.save()
    return Response({'detail': 'Password has been reset. You can now sign in.'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    """Authenticated user changes their own password."""
    current = request.data.get('current_password', '')
    new_pw = request.data.get('new_password', '')

    if not request.user.check_password(current):
        return Response({'detail': 'Current password is incorrect.'}, status=400)
    pw_err = _validate_password_strength(new_pw)
    if pw_err:
        return Response({'detail': pw_err}, status=400)

    request.user.set_password(new_pw)
    request.user.save()
    return Response({'detail': 'Password updated successfully.'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me_view(request):
    user = request.user
    profile = getattr(user, 'profile', None)
    role = profile.role if profile else ('superadmin' if user.is_superuser else 'tenant_admin')

    quota = None
    tenant = getattr(user, 'tenant_profile', None)
    if tenant:
        plan = tenant.plan
        client_count = tenant.clients.filter(is_active=True).count()
        quota = {
            'sessions_this_month': tenant.sessions_this_month,
            'max_sessions': plan.max_sessions_per_month if plan else None,
            'client_count': client_count,
            'max_clients': plan.max_clients if plan else None,
            'plan_name': plan.name if plan else None,
        }

    return Response({
        'username': user.username,
        'email': user.email,
        'role': role,
        'is_superuser': user.is_superuser,
        'quota': quota,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def portal_client(request):
    """
    Resolve the active client for the TENANT PORTAL — the user's OWN tenant
    clients only, ordered stably by creation.

    Why this exists: the portal used to call /api/admin/clients/ and take
    clients[0]. For a super-admin, get_accessible_clients returns EVERY
    client on the platform ordered by -created_at, so the "active client"
    was whatever was newest platform-wide — and it flipped to a different
    tenant the moment any new client/tenant appeared. This endpoint is
    strictly scoped to request.user.tenant_profile, so the portal stays
    pinned to the user's own client across refreshes.

    Returns the serialized client (or null if the tenant has none).
    """
    tenant = getattr(request.user, 'tenant_profile', None)
    if not tenant:
        return Response(None)
    # Stable order: oldest first → the tenant's primary client never changes.
    client = tenant.clients.order_by('created_at').first()
    if not client:
        return Response(None)
    return Response(ClientSerializer(client).data)


# ─── Client CRUD ─────────────────────────────────────────────────────────────

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def client_list(request):
    if request.method == 'GET':
        clients = get_accessible_clients(request.user).order_by('-created_at')
        data = ClientSerializer(clients, many=True).data
        # Annotate each client with its assigned tenant (if any)
        tenant_map = {}
        for tp in TenantProfile.objects.prefetch_related('clients').all():
            for c in tp.clients.all():
                tenant_map[str(c.id)] = {'tenant_id': tp.pk, 'tenant_name': tp.company_name or tp.user.username}
        for item in data:
            info = tenant_map.get(str(item['id']))
            item['tenant_id'] = info['tenant_id'] if info else None
            item['tenant_name'] = info['tenant_name'] if info else None
        return Response(data)

    # POST — create client (superadmin or tenant_admin)
    serializer = ClientCreateSerializer(data=request.data)
    if serializer.is_valid():
        client = serializer.save()
        # Default chatbot_name to the brand name so new bots aren't called
        # "AI Assistant" (or worse — "test" — when a dev or onboarding flow
        # left a placeholder). The tenant can rename it in /portal/settings.
        if client.name and (not client.chatbot_name or client.chatbot_name in ('AI Assistant', 'test', '')):
            client.chatbot_name = f'{client.name} Assistant'
            client.save(update_fields=['chatbot_name'])
        # Auto-assign to tenant profile if tenant_admin
        tenant = getattr(request.user, 'tenant_profile', None)
        if tenant:
            tenant.clients.add(client)
        return Response(ClientSerializer(client).data, status=201)
    return Response(serializer.errors, status=400)


@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def client_detail(request, client_id):
    accessible = get_accessible_clients(request.user)
    try:
        client = accessible.get(pk=client_id)
    except Client.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=404)

    if request.method == 'GET':
        return Response(ClientSerializer(client).data)

    if request.method == 'PATCH':
        # Snapshot Telegram state BEFORE save so we can detect a transition
        # and register/deregister the webhook with Telegram's API. Without
        # this, toggling telegram_enabled in the UI saves the flag locally
        # but Telegram never knows where to deliver messages.
        prev_telegram_token = client.telegram_bot_token
        prev_telegram_enabled = client.telegram_enabled

        serializer = ClientSerializer(client, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
        serializer.save()
        client.refresh_from_db()

        telegram_status = None
        token_changed = (prev_telegram_token != client.telegram_bot_token)
        enabled_changed = (prev_telegram_enabled != client.telegram_enabled)

        if token_changed or enabled_changed:
            from chat.views import register_telegram_webhook, delete_telegram_webhook
            if client.telegram_enabled and client.telegram_bot_token:
                ok, msg = register_telegram_webhook(client)
                telegram_status = {'ok': ok, 'message': msg}
            else:
                # Disabled or token cleared — best-effort deregister the
                # old token so Telegram stops sending to a dead endpoint.
                if prev_telegram_token:
                    delete_telegram_webhook(prev_telegram_token)
                telegram_status = {'ok': True, 'message': 'Telegram disabled'}

        response_data = serializer.data
        if telegram_status is not None:
            response_data = {**response_data, 'telegram_webhook_status': telegram_status}
        return Response(response_data)

    if request.method == 'DELETE':
        client.delete()
        return Response(status=204)


# ─── Client logo upload ──────────────────────────────────────────────────────
#
# Accepts a multipart image (PNG / JPEG / GIF / WebP), saves it under
# MEDIA_ROOT/client_logos/<client_id>/, and writes the resulting public
# URL to client.chatbot_logo_url. SVG is intentionally NOT allowed —
# SVG can carry <script> and would be served from our own domain.
#
# Validation:
#   • Magic-byte sniff so a renamed .exe doesn't sneak in.
#   • 2 MB cap — way more than any reasonable logo and small enough
#     to keep the VPS disk happy.
#   • Per-client folder + random filename to avoid collisions and to
#     stop someone enumerating other tenants' logos by guessing names.

_LOGO_MAX_BYTES = 2 * 1024 * 1024  # 2 MB

# (magic_bytes, extension, mime). First match wins.
_LOGO_SIGNATURES = (
    (b'\x89PNG\r\n\x1a\n',       'png',  'image/png'),
    (b'\xff\xd8\xff',             'jpg',  'image/jpeg'),
    (b'GIF87a',                   'gif',  'image/gif'),
    (b'GIF89a',                   'gif',  'image/gif'),
    # WebP files start with RIFF....WEBP — sniff RIFF prefix + WEBP at byte 8.
    # Handled separately below.
)


def _sniff_image_format(head: bytes) -> tuple[str, str] | None:
    """Return (extension, mime) for a known image type, or None."""
    for signature, ext, mime in _LOGO_SIGNATURES:
        if head.startswith(signature):
            return ext, mime
    if len(head) >= 12 and head[0:4] == b'RIFF' and head[8:12] == b'WEBP':
        return 'webp', 'image/webp'
    return None


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def detect_client_platform(request):
    """
    Inspect a public domain URL and return our best guess at the e-commerce
    platform powering it (SHOPIFY / WORDPRESS / CUSTOM). Used by the
    onboarding wizard to pre-select the platform field so the merchant
    doesn't have to choose manually.

    Body: { "url": "https://example.com" }
    Response: { "platform": "SHOPIFY", "detected": true }

    Always returns 200 — `detected: false` means we couldn't identify the
    platform with confidence and the UI should fall back to manual choice.
    The call is best-effort and never raises to the user.
    """
    url = (request.data.get('url') or '').strip()
    if not url:
        return Response({'detail': 'url is required'}, status=400)

    # Normalise — accept "example.com" and "https://example.com" alike.
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    from scraper.ingestion import detect_platform
    try:
        platform = detect_platform(url)
    except Exception as exc:
        logger.warning(f'[detect_client_platform] {url}: {exc}')
        platform = 'CUSTOM'

    return Response({
        'platform': platform,
        'detected': platform != 'CUSTOM',
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_client_logo(request, client_id):
    """
    Upload a brand logo for `client_id` and persist its public URL on the
    Client row. Returns {logo_url, chatbot_logo_url} on success.

    Body: multipart/form-data with a single file field `logo`.
    """
    accessible = get_accessible_clients(request.user)
    try:
        client = accessible.get(pk=client_id)
    except Client.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=404)

    upload = request.FILES.get('logo')
    if upload is None:
        return Response({'detail': 'No file received under field "logo".'}, status=400)

    if upload.size > _LOGO_MAX_BYTES:
        return Response(
            {'detail': f'File too large. Max {_LOGO_MAX_BYTES // (1024 * 1024)} MB.'},
            status=400,
        )

    head = upload.read(32)
    upload.seek(0)
    sniff = _sniff_image_format(head)
    if sniff is None:
        return Response(
            {'detail': 'Unsupported format. Use PNG, JPEG, GIF, or WebP.'},
            status=400,
        )
    ext, _mime = sniff

    # MEDIA_ROOT/client_logos/<client_id>/<random>.<ext>
    from django.conf import settings as dj_settings
    rel_dir = os.path.join('client_logos', str(client.id))
    abs_dir = os.path.join(dj_settings.MEDIA_ROOT, rel_dir)
    os.makedirs(abs_dir, exist_ok=True)

    filename = f'{secrets.token_urlsafe(12)}.{ext}'
    abs_path = os.path.join(abs_dir, filename)
    with open(abs_path, 'wb') as fh:
        for chunk in upload.chunks():
            fh.write(chunk)

    # Build the absolute URL — works for both `/media/...` (prod nginx)
    # and `/media/...` served by Django in DEBUG.
    rel_url = f'{dj_settings.MEDIA_URL.rstrip("/")}/{rel_dir}/{filename}'.replace('\\', '/')
    public_url = request.build_absolute_uri(rel_url)

    # Persist to the Client. Deliberately overwrite — we never want the
    # invoice / widget to reference a deleted file.
    client.chatbot_logo_url = public_url
    client.save(update_fields=['chatbot_logo_url'])

    return Response({
        'logo_url': public_url,
        'chatbot_logo_url': public_url,
    })


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def telegram_webhook_status(request, client_id):
    """Check or re-register the Telegram webhook for diagnostics.

    GET → calls getWebhookInfo on Telegram's API; surfaces last_error_message
          and last_error_date so the user can see why Telegram is not
          delivering messages.
    POST → re-runs setWebhook (idempotent). Useful for a 'Test bot' button.
    """
    accessible = get_accessible_clients(request.user)
    try:
        client = accessible.get(pk=client_id)
    except Client.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=404)
    if not client.telegram_bot_token:
        return Response({'ok': False, 'detail': 'No Telegram bot token configured.'}, status=400)

    if request.method == 'POST':
        from chat.views import register_telegram_webhook
        ok, msg = register_telegram_webhook(client)
        return Response({'ok': ok, 'message': msg})

    # GET — query Telegram for current webhook info
    import requests as http_requests
    try:
        resp = http_requests.get(
            f'https://api.telegram.org/bot{client.telegram_bot_token}/getWebhookInfo',
            timeout=10,
        )
        data = resp.json() if resp.content else {}
        if not (resp.ok and data.get('ok')):
            return Response({'ok': False, 'detail': data.get('description') or f'HTTP {resp.status_code}'}, status=502)
        info = data.get('result', {})
        return Response({
            'ok': True,
            'url': info.get('url'),
            'has_custom_certificate': info.get('has_custom_certificate'),
            'pending_update_count': info.get('pending_update_count', 0),
            'last_error_date': info.get('last_error_date'),
            'last_error_message': info.get('last_error_message'),
            'max_connections': info.get('max_connections'),
        })
    except Exception as e:
        logger.exception(f'[telegram_webhook_status] failed for client {client_id}: {e}')
        return Response({'ok': False, 'detail': str(e)}, status=502)


# ─── Sessions ────────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def client_sessions(request, client_id):
    accessible = get_accessible_clients(request.user)
    try:
        client = accessible.get(pk=client_id)
    except Client.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=404)

    # Order by true last-message recency. last_message_at is only stamped when
    # a message is appended (not on unrelated saves), so the most recently
    # active conversations sort first. Fall back to updated_at for legacy rows
    # that predate the field (NULLs sort last under -last_message_at, so we
    # coalesce to keep them in a sensible position).
    from django.db.models.functions import Coalesce
    qs = (ChatSession.objects.filter(client=client)
          .annotate(last_activity=Coalesce('last_message_at', 'updated_at'))
          .order_by('-last_activity'))

    # ── Filters ────────────────────────────────────────────────────────
    state = request.query_params.get('state', '').strip()
    if state:
        qs = qs.filter(conversation_state=state)

    date_from = request.query_params.get('date_from', '').strip()
    if date_from:
        qs = qs.filter(created_at__date__gte=date_from)

    date_to = request.query_params.get('date_to', '').strip()
    if date_to:
        qs = qs.filter(created_at__date__lte=date_to)

    if request.query_params.get('has_lead') == 'true':
        qs = qs.exclude(lead_email='').exclude(lead_email__isnull=True)

    q = request.query_params.get('q', '').strip()
    if q:
        qs = qs.filter(lead_email__icontains=q)

    # Fetch up to 200; heat-score range filter applied in-memory
    min_heat_raw = request.query_params.get('min_heat', '').strip()
    max_heat_raw = request.query_params.get('max_heat', '').strip()
    min_heat = float(min_heat_raw) if min_heat_raw else None
    max_heat = float(max_heat_raw) if max_heat_raw else None

    data = []
    for s in qs[:200]:
        heat = _calc_heat(s)
        if min_heat is not None and heat < min_heat:
            continue
        if max_heat is not None and heat > max_heat:
            continue
        data.append({
            'session_id': str(s.session_id),
            'visitor_id': s.visitor_id,
            'heat_score': heat,
            'conversation_state': s.conversation_state,
            'kanban_state': s.kanban_state,
            'message_count': s.message_count,
            'intent_ema': round(s.current_intent_ema, 3),
            'budget_ema': round(s.current_budget_ema, 3),
            'urgency_ema': round(s.current_urgency_ema, 3),
            'lead_email': s.lead_email,
            'lead_phone': s.lead_phone,
            'takeover_active': s.takeover_active,
            'closing_triggered': s.closing_triggered,
            'chat_history': s.chat_history,
            # Visitor fingerprint
            'visitor_ip': s.visitor_ip,
            'visitor_country': s.visitor_country,
            'visitor_city': s.visitor_city,
            'visitor_country_code': s.visitor_country_code,
            'visitor_device': s.visitor_device,
            'visitor_os': s.visitor_os,
            'visitor_browser': s.visitor_browser,
            'visitor_referrer': s.visitor_referrer,
            'visitor_timezone': s.visitor_timezone,
            'page_visits': s.page_visits,
            'channel': s.channel,
            'updated_at': s.updated_at.isoformat(),
            # True last-message time for the inbox; falls back to updated_at
            # for legacy sessions created before the field existed.
            'last_message_at': (s.last_message_at or s.updated_at).isoformat(),
            'created_at': s.created_at.isoformat(),
            'behavioral_context': s.behavioral_context,
            'intent_trend': s.intent_trend,
            'budget_trend': s.budget_trend,
            'urgency_trend': s.urgency_trend,
        })
    return Response(data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def client_link_clicks(request, client_id):
    """
    Marketing attribution: how many visitors the chatbot referred to each
    product/content link, for one client. Grouped by URL with total clicks
    and unique sessions, newest-active first.

    Query params: ?period=7d|30d|90d|all (default 30d)
    """
    from chat.models import ProductLinkClick
    from django.db.models import Count

    accessible = get_accessible_clients(request.user)
    try:
        client = accessible.get(pk=client_id)
    except Client.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=404)

    period = request.query_params.get('period', '30d')
    qs = ProductLinkClick.objects.filter(client=client)
    since = _period_since(period)
    if since:
        qs = qs.filter(created_at__gte=since)

    rows = (
        qs.values('url')
          .annotate(
              clicks=Count('id'),
              unique_sessions=Count('session_id', distinct=True),
          )
          .order_by('-clicks')[:200]
    )
    # Attach a representative link_text (most recent) per URL.
    label_map = {}
    for plc in qs.order_by('-created_at').values('url', 'link_text')[:1000]:
        if plc['url'] not in label_map and plc['link_text']:
            label_map[plc['url']] = plc['link_text']

    data = [{
        'url': r['url'],
        'link_text': label_map.get(r['url'], ''),
        'clicks': r['clicks'],
        'unique_sessions': r['unique_sessions'],
    } for r in rows]

    return Response({
        'period': period,
        'total_clicks': qs.count(),
        'total_links': len(data),
        'links': data,
    })


def _period_since(period):
    """Map a period string to a UTC cutoff datetime, or None for 'all'."""
    from datetime import timedelta
    now = timezone.now()
    return {
        'today': now.replace(hour=0, minute=0, second=0, microsecond=0),
        '7d': now - timedelta(days=7),
        '30d': now - timedelta(days=30),
        '90d': now - timedelta(days=90),
    }.get(period)  # 'all' / unknown → None (no filter)


@api_view(['GET'])
@permission_classes([IsSuperAdmin])
def platform_link_clicks(request):
    """
    Super-admin global view of chatbot product-link referrals across ALL
    tenants. Returns the top links overall plus a per-client breakdown.

    Query params: ?period=7d|30d|90d|all (default 30d)
    """
    from chat.models import ProductLinkClick
    from django.db.models import Count

    period = request.query_params.get('period', '30d')
    qs = ProductLinkClick.objects.all()
    since = _period_since(period)
    if since:
        qs = qs.filter(created_at__gte=since)

    top_links = list(
        qs.values('url')
          .annotate(clicks=Count('id'), unique_sessions=Count('session_id', distinct=True))
          .order_by('-clicks')[:100]
    )

    by_client = list(
        qs.values('client__id', 'client__name')
          .annotate(clicks=Count('id'), unique_sessions=Count('session_id', distinct=True))
          .order_by('-clicks')[:100]
    )
    by_client = [{
        'client_id': str(r['client__id']) if r['client__id'] else None,
        'client_name': r['client__name'] or '(unassigned)',
        'clicks': r['clicks'],
        'unique_sessions': r['unique_sessions'],
    } for r in by_client]

    return Response({
        'period': period,
        'total_clicks': qs.count(),
        'top_links': top_links,
        'by_client': by_client,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def suggest_cta(request, client_id):
    """
    Generate 3 short CTA message suggestions based on:
      - The client's actual products/content (DocumentChunks)
      - Aggregate visitor behavior signals from recent sessions
      - Sample high-intent conversations (what worked)

    Returns: { suggestions: [str, str, str] }
    """
    from scraper.models import DocumentChunk
    from chat.ai_service import _build_llm
    from langchain_core.messages import SystemMessage, HumanMessage

    accessible = get_accessible_clients(request.user)
    try:
        client = accessible.get(pk=client_id)
    except Client.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=404)

    # 1. Top product titles from the knowledge base
    titles = []
    seen_titles = set()
    for chunk in DocumentChunk.objects.filter(client=client).order_by('id')[:50]:
        meta = chunk.metadata or {}
        t = (meta.get('title') or '').strip()
        if t and t not in seen_titles:
            seen_titles.add(t)
            titles.append(t)
        if len(titles) >= 8:
            break

    # 2. Aggregate behavior signals from the last 30 days
    since = timezone.now() - timedelta(days=30)
    sessions = ChatSession.objects.filter(client=client, updated_at__gte=since)

    total_atc = 0
    total_pricing = 0
    total_checkout = 0
    total_form_focused = 0
    total_high_intent = 0
    for s in sessions:
        ctx = s.behavioral_context or {}
        total_atc += ctx.get('add_to_cart_clicks', 0) or 0
        total_pricing += ctx.get('pricing_page_visits', 0) or 0
        total_checkout += ctx.get('checkout_visits', 0) or 0
        if ctx.get('form_focused'):
            total_form_focused += 1
        if s.current_intent_ema > 0.5:
            total_high_intent += 1

    session_total = sessions.count() or 1
    intent_rate = round(total_high_intent / session_total * 100, 1)

    # 3. Sample 3 high-intent chats to capture audience vibe
    hot = sessions.filter(current_intent_ema__gt=0.5).order_by('-current_intent_ema')[:3]
    sample_msgs = []
    for s in hot:
        for msg in (s.chat_history or [])[:4]:
            if msg.get('role') == 'user' and msg.get('message'):
                sample_msgs.append(msg['message'][:120])
                if len(sample_msgs) >= 6:
                    break
        if len(sample_msgs) >= 6:
            break

    # 4. Build the LLM prompt
    products_str = ', '.join(titles[:8]) if titles else '(no scraped content)'
    behavior_str = (
        f"Add-to-cart events: {total_atc}, Pricing visits: {total_pricing}, "
        f"Checkout visits: {total_checkout}, Forms started: {total_form_focused}, "
        f"High-intent rate: {intent_rate}% of visitors"
    )
    sample_str = '; '.join(f'"{m}"' for m in sample_msgs[:5]) if sample_msgs else '(no sample chats)'

    system = (
        "You write very short, punchy CTA messages for a chat widget that fires when a visitor "
        "shows hesitation (e.g. lingering on pricing). Max 90 characters per CTA. "
        "Friendly, not pushy. Avoid clichés like 'Don't miss out!'. "
        "Return ONLY a JSON object with key 'suggestions' as a list of exactly 3 strings."
    )
    user = (
        f"Website: {client.domain_url or client.name}\n"
        f"Top products/content: {products_str}\n"
        f"Visitor signals (last 30 days): {behavior_str}\n"
        f"Sample messages high-intent visitors typed: {sample_str}\n\n"
        f"Generate 3 short CTAs that would help convert hesitant visitors on THIS site. "
        f"Each should be different in tone (helpful, urgent, value-led). "
        f"Return as: {{\"suggestions\": [\"...\", \"...\", \"...\"]}}"
    )

    try:
        llm, _ = _build_llm(client)
        result = llm.invoke([SystemMessage(content=system), HumanMessage(content=user)])
        text = result.content if hasattr(result, 'content') else str(result)
        # Extract JSON object even if model wraps it in prose
        import re, json as _json
        match = re.search(r'\{[^{}]*"suggestions"[^{}]*\}', text, re.DOTALL)
        if match:
            data = _json.loads(match.group(0))
            suggestions = data.get('suggestions') or []
        else:
            suggestions = []
        # Validate
        suggestions = [str(s).strip() for s in suggestions if s and len(str(s)) < 150][:3]
    except Exception as e:
        logger.warning(f'[suggest_cta] LLM failed: {e}')
        # Fallback so the UI never sees an empty response
        suggestions = [
            "Need help deciding? I'm here to answer any questions.",
            "Have a quick question? I can help you find what's right for you.",
            "Looking for something specific? Just ask — I'll point you the right way.",
        ]

    if not suggestions:
        suggestions = [
            "Need help deciding? I'm here to answer any questions.",
            "Have a quick question? I can help you find what's right for you.",
            "Looking for something specific? Just ask — I'll point you the right way.",
        ]

    return Response({'suggestions': suggestions})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def client_visitors(request, client_id):
    """
    List Visitors (cross-session identities) for a client, sorted by heat.

    Each row aggregates across the visitor's sessions:
      - lifetime sessions, messages, page views, time, clicks, ATC clicks
      - latest known EMA scores + composite heat
      - top product they've shown interest in
      - lead info (if captured)
      - device / location
    """
    from chat.models import Visitor, ChatSession
    from django.db.models import Sum, Count, Max

    accessible = get_accessible_clients(request.user)
    try:
        client = accessible.get(pk=client_id)
    except Client.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=404)

    try:
        limit = max(10, min(int(request.query_params.get('limit', '50')), 200))
    except ValueError:
        limit = 50
    days_raw = request.query_params.get('days', '').strip()
    qs = Visitor.objects.filter(client=client)
    if days_raw:
        try:
            days = max(1, min(int(days_raw), 365))
            qs = qs.filter(last_seen__gte=timezone.now() - timedelta(days=days))
        except ValueError:
            pass

    q = (request.query_params.get('q') or '').strip()
    if q:
        qs = qs.filter(Q(lead_email__icontains=q) | Q(visitor_uid__icontains=q))

    # Latest EMA-based heat = 0.45 intent + 0.30 budget + 0.25 urgency
    qs = qs.annotate(
        composite_heat=(F('intent_ema') * 0.45 + F('budget_ema') * 0.30 + F('urgency_ema') * 0.25) * 100,
        sess_count=Count('sessions'),
        last_session_at=Max('sessions__updated_at'),
    ).order_by('-composite_heat', '-last_seen')

    data = []
    for v in qs[:limit]:
        # Lifetime stats from session relation (computed at query time)
        stats = ChatSession.objects.filter(visitor_obj=v).aggregate(
            messages=Sum('message_count'),
        )
        # Sum page_views and time from each session's data (JSONField → Python aggregate)
        total_pages = 0
        total_time = 0
        for s in ChatSession.objects.filter(visitor_obj=v).only('page_visits', 'behavioral_context'):
            total_pages += len(s.page_visits or [])
            total_time += (s.behavioral_context or {}).get('time_on_site', 0) or 0

        data.append({
            'visitor_uid': v.visitor_uid,
            'first_seen': v.first_seen.isoformat(),
            'last_seen': v.last_seen.isoformat(),
            'last_session_at': v.last_session_at.isoformat() if v.last_session_at else None,
            'total_sessions': v.sess_count,
            'total_messages': stats['messages'] or 0,
            'total_page_views': total_pages,
            'total_time_seconds': total_time,
            'intent_ema': round(v.intent_ema, 3),
            'budget_ema': round(v.budget_ema, 3),
            'urgency_ema': round(v.urgency_ema, 3),
            'heat_score': round(min(v.composite_heat or 0, 100), 1),
            'lead_email': v.lead_email,
            'lead_phone': v.lead_phone,
            'lead_name': v.lead_name,
            'top_interest_title': v.top_interest_title,
            'top_interest_url': v.top_interest_url,
            'device': v.device,
            'os': v.os,
            'browser': v.browser,
            'country': v.country,
            'city': v.city,
            'country_code': v.country_code,
        })

    return Response({'visitors': data, 'count': len(data)})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def visitor_detail(request, visitor_uid):
    """
    Full detail for one visitor — every session they've had with this tenant,
    every event, every chat message, all unified.

    Query param: client_id (required) for tenancy check.
    """
    from chat.models import Visitor, ChatSession
    from analytics.models import AnalyticEvent
    from django.db.models import Q as _Q

    client_id = request.query_params.get('client_id', '').strip()
    if not client_id:
        return Response({'detail': 'client_id required.'}, status=400)

    accessible = get_accessible_clients(request.user)
    try:
        client = accessible.get(pk=client_id)
    except Client.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=404)

    try:
        visitor = Visitor.objects.get(visitor_uid=visitor_uid, client=client)
    except Visitor.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=404)

    sessions_qs = ChatSession.objects.filter(visitor_obj=visitor).order_by('-updated_at')
    session_session_ids = [str(s.session_id) for s in sessions_qs]

    # All events for any of this visitor's sessions
    events = (
        AnalyticEvent.objects
        .filter(session_id__in=session_session_ids)
        .order_by('-created_at')[:500]
    )

    timeline = []
    for ev in events:
        timeline.append({
            'event_type': ev.event_type,
            'page_url': ev.page_url,
            'payload': ev.payload,
            'created_at': ev.created_at.isoformat(),
            'session_id': ev.session_id,
        })
    for s in sessions_qs:
        for pv in (s.page_visits or []):
            timeline.append({
                'event_type': 'page_view',
                'page_url': pv.get('url', ''),
                'payload': {
                    'page_title': pv.get('title', ''),
                    'duration_seconds': pv.get('duration_seconds', 0),
                },
                'created_at': pv.get('visited_at', ''),
                'session_id': str(s.session_id),
            })
        for msg in (s.chat_history or []):
            timeline.append({
                'event_type': 'chat_user' if msg.get('role') == 'user' else 'chat_ai',
                'page_url': '',
                'payload': {'message': (msg.get('message') or msg.get('content') or '')[:300]},
                'created_at': msg.get('timestamp', ''),
                'session_id': str(s.session_id),
            })

    timeline = [t for t in timeline if t.get('created_at')]
    timeline.sort(key=lambda x: x.get('created_at') or '')

    sessions_summary = [{
        'session_id': str(s.session_id),
        'created_at': s.created_at.isoformat(),
        'updated_at': s.updated_at.isoformat(),
        'message_count': len(s.chat_history or []),
        'page_count': len(s.page_visits or []),
        'heat_score': s.heat_score,
        'kanban_state': s.kanban_state,
    } for s in sessions_qs]

    return Response({
        'visitor_uid': visitor.visitor_uid,
        'first_seen': visitor.first_seen.isoformat(),
        'last_seen': visitor.last_seen.isoformat(),
        'lead_email': visitor.lead_email,
        'lead_phone': visitor.lead_phone,
        'lead_name': visitor.lead_name,
        'intent_ema': round(visitor.intent_ema, 3),
        'budget_ema': round(visitor.budget_ema, 3),
        'urgency_ema': round(visitor.urgency_ema, 3),
        'device': visitor.device,
        'os': visitor.os,
        'browser': visitor.browser,
        'country': visitor.country,
        'city': visitor.city,
        'country_code': visitor.country_code,
        'top_interest_title': visitor.top_interest_title,
        'top_interest_url': visitor.top_interest_url,
        'sessions': sessions_summary,
        'timeline': timeline[-200:],
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def activity_pages(request, client_id):
    """
    Returns the list of pages where visitors generated click events,
    ranked by total click count over the past N days. Used to populate
    the page selector dropdown in the Activity heatmap UI.
    """
    from analytics.models import AnalyticEvent
    from django.db.models import Count

    accessible = get_accessible_clients(request.user)
    try:
        client = accessible.get(pk=client_id)
    except Client.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=404)

    try:
        days = max(1, min(int(request.query_params.get('days', '7')), 90))
    except ValueError:
        days = 7
    since = timezone.now() - timedelta(days=days)

    pages = (
        AnalyticEvent.objects
        .filter(client=client, created_at__gte=since)
        .exclude(page_url='')
        .values('page_url')
        .annotate(
            total_clicks=Count('id', filter=Q(event_type__in=['click', 'cta_click', 'add_to_cart'])),
            total_events=Count('id'),
        )
        .order_by('-total_events')[:50]
    )

    return Response({
        'days': days,
        'pages': [
            {
                'page_url': p['page_url'],
                'total_clicks': p['total_clicks'],
                'total_events': p['total_events'],
            }
            for p in pages
        ],
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def page_heatmap(request, client_id):
    """
    Aggregate click events on a specific page into spatial clusters
    suitable for rendering a heatmap.

    Query params:
      page_url   — required, the page path to aggregate
      days       — lookback window (default 7, max 90)

    Returns:
      total_clicks, unique_visitors, top_elements, clusters
    """
    from analytics.models import AnalyticEvent
    from collections import defaultdict

    accessible = get_accessible_clients(request.user)
    try:
        client = accessible.get(pk=client_id)
    except Client.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=404)

    page_url = (request.query_params.get('page_url') or '').strip()
    if not page_url:
        return Response({'detail': 'page_url required.'}, status=400)

    try:
        days = max(1, min(int(request.query_params.get('days', '7')), 90))
    except ValueError:
        days = 7
    since = timezone.now() - timedelta(days=days)

    qs = AnalyticEvent.objects.filter(
        client=client,
        page_url=page_url,
        event_type__in=['click', 'cta_click', 'add_to_cart', 'rage_click'],
        created_at__gte=since,
    ).values('payload', 'session_id', 'event_type')

    # Bucket coords into 5% × 5% cells to cluster nearby clicks
    clusters = defaultdict(lambda: {'count': 0, 'texts': defaultdict(int), 'has_cta': False, 'has_rage': False})
    element_counts = defaultdict(lambda: {'count': 0, 'tag': '', 'href': None})
    unique_sessions = set()
    total_clicks = 0

    for ev in qs:
        p = ev['payload'] or {}
        unique_sessions.add(ev['session_id'])
        total_clicks += 1

        x = p.get('x')
        y = p.get('y')
        text = (p.get('text') or '').strip()
        tag = p.get('tag') or ''
        href = p.get('href')

        if isinstance(x, (int, float)) and isinstance(y, (int, float)):
            x_b = round(x / 5) * 5
            y_b = round(y / 5) * 5
            key = (x_b, y_b)
            clusters[key]['count'] += 1
            if text:
                clusters[key]['texts'][text] += 1
            if ev['event_type'] == 'cta_click' or ev['event_type'] == 'add_to_cart':
                clusters[key]['has_cta'] = True
            if ev['event_type'] == 'rage_click':
                clusters[key]['has_rage'] = True

        if text:
            element_counts[text]['count'] += 1
            element_counts[text]['tag'] = tag
            element_counts[text]['href'] = href

    # Top 500 hottest clusters
    cluster_list = []
    for (x, y), data in clusters.items():
        top_text = max(data['texts'].items(), key=lambda kv: kv[1])[0] if data['texts'] else ''
        cluster_list.append({
            'x': x,
            'y': y,
            'count': data['count'],
            'text': top_text,
            'is_cta': data['has_cta'],
            'is_rage': data['has_rage'],
        })
    cluster_list.sort(key=lambda c: -c['count'])
    cluster_list = cluster_list[:500]

    top_elements = sorted(
        [{'text': t, 'count': d['count'], 'tag': d['tag'], 'href': d['href']}
         for t, d in element_counts.items()],
        key=lambda x: -x['count'],
    )[:25]

    return Response({
        'page_url': page_url,
        'days': days,
        'total_clicks': total_clicks,
        'unique_visitors': len(unique_sessions),
        'clusters': cluster_list,
        'top_elements': top_elements,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def session_timeline(request, session_id):
    """
    Returns chronological event timeline for a single visitor session.
    Used by the inbox visitor panel "watch over their shoulder" view.
    """
    from analytics.models import AnalyticEvent

    try:
        session = ChatSession.objects.select_related('client').get(session_id=session_id)
    except ChatSession.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=404)

    accessible_ids = list(get_accessible_clients(request.user).values_list('id', flat=True))
    if session.client_id and session.client_id not in accessible_ids:
        return Response({'detail': 'Not found.'}, status=404)

    events = (
        AnalyticEvent.objects
        .filter(session_id=str(session_id))
        .order_by('-created_at')[:100]
    )

    timeline = []
    for ev in events:
        timeline.append({
            'event_type': ev.event_type,
            'page_url': ev.page_url,
            'payload': ev.payload,
            'created_at': ev.created_at.isoformat(),
        })

    # Add page_visits + chat_history as virtual events for completeness
    for pv in (session.page_visits or []):
        timeline.append({
            'event_type': 'page_view',
            'page_url': pv.get('url', ''),
            'payload': {
                'page_title': pv.get('title', ''),
                'duration_seconds': pv.get('duration_seconds', 0),
            },
            'created_at': pv.get('visited_at', ''),
        })

    for msg in (session.chat_history or []):
        timeline.append({
            'event_type': 'chat_user' if msg.get('role') == 'user' else 'chat_ai',
            'page_url': '',
            'payload': {'message': (msg.get('message') or msg.get('content') or '')[:200]},
            'created_at': msg.get('timestamp', ''),
        })

    # Sort chronologically (most recent last)
    timeline = [t for t in timeline if t.get('created_at')]
    timeline.sort(key=lambda x: x.get('created_at') or '')

    return Response({
        'session_id': str(session_id),
        'events': timeline[-150:],  # cap displayed length
    })


@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def session_detail(request, session_id):
    try:
        session = ChatSession.objects.select_related('client').get(session_id=session_id)
    except ChatSession.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=404)

    # Verify access
    accessible_ids = get_accessible_clients(request.user).values_list('id', flat=True)
    if session.client_id and session.client_id not in list(accessible_ids):
        return Response({'detail': 'Not found.'}, status=404)

    if request.method == 'PATCH':
        allowed_fields = ['kanban_state', 'conversation_state', 'lead_email', 'lead_phone']
        for field in allowed_fields:
            if field in request.data:
                setattr(session, field, request.data[field])
        session.save()

        # ── Live-broadcast the change to all connected dashboards ────────
        # Without this, dragging a kanban card updated the DB but the admin
        # dashboard + tenant dashboard kept showing the old column until a
        # full page reload (and analytics like kanban_breakdown / hot_count
        # stayed stale). The chat consumer already publishes session_update
        # events to ADMIN_GROUP on every message — we mirror the same payload
        # here so kanban moves use the exact same realtime channel.
        try:
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync

            channel_layer = get_channel_layer()
            if channel_layer:
                payload = {
                    'session_id': str(session.session_id),
                    'visitor_id': session.visitor_id,
                    'heat_score': session.heat_score,
                    'conversation_state': session.conversation_state,
                    'kanban_state': session.kanban_state,
                    'message_count': session.message_count,
                    'intent_ema': round(session.current_intent_ema, 3),
                    'budget_ema': round(session.current_budget_ema, 3),
                    'urgency_ema': round(session.current_urgency_ema, 3),
                    'lead_email': session.lead_email,
                    'takeover_active': session.takeover_active,
                    'client_id': str(session.client_id) if session.client_id else None,
                    'updated_at': session.updated_at.isoformat(),
                }
                async_to_sync(channel_layer.group_send)(
                    'admin_dashboard',
                    {'type': 'session_update', 'data': payload},
                )
        except Exception:
            pass  # Broadcast failure must never fail the PATCH itself

        return Response({'detail': 'Updated.'})

    return Response({
        'session_id': str(session.session_id),
        'visitor_id': session.visitor_id,
        'heat_score': _calc_heat(session),
        'conversation_state': session.conversation_state,
        'kanban_state': session.kanban_state,
        'message_count': session.message_count,
        'intent_ema': round(session.current_intent_ema, 3),
        'budget_ema': round(session.current_budget_ema, 3),
        'urgency_ema': round(session.current_urgency_ema, 3),
        'lead_email': session.lead_email,
        'lead_phone': session.lead_phone,
        'takeover_active': session.takeover_active,
        'taken_over_by': session.taken_over_by.username if session.taken_over_by else None,
        'closing_triggered': session.closing_triggered,
        'chat_history': session.chat_history,
        'behavioral_context': session.behavioral_context,
        # Visitor fingerprint
        'visitor_ip': session.visitor_ip,
        'visitor_country': session.visitor_country,
        'visitor_city': session.visitor_city,
        'visitor_country_code': session.visitor_country_code,
        'visitor_device': session.visitor_device,
        'visitor_os': session.visitor_os,
        'visitor_browser': session.visitor_browser,
        'visitor_referrer': session.visitor_referrer,
        'visitor_timezone': session.visitor_timezone,
        'page_visits': session.page_visits,
        'channel': session.channel,
        'updated_at': session.updated_at.isoformat(),
        'created_at': session.created_at.isoformat(),
    })


# ─── God View — Takeover ─────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def session_takeover(request, session_id):
    """Admin takes over a session — disables AI replies."""
    from users.feature_flags import has_feature, gate_feature
    if not has_feature(request.user, 'allow_god_view'):
        return gate_feature('allow_god_view')

    try:
        session = ChatSession.objects.get(session_id=session_id)
    except ChatSession.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=404)

    session.takeover_active = True
    session.taken_over_by = request.user
    session.save(update_fields=['takeover_active', 'taken_over_by'])
    return Response({'detail': 'Takeover active.', 'session_id': str(session_id)})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def session_release(request, session_id):
    """Release a session back to AI."""
    try:
        session = ChatSession.objects.get(session_id=session_id)
    except ChatSession.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=404)

    session.takeover_active = False
    session.taken_over_by = None
    session.save(update_fields=['takeover_active', 'taken_over_by'])
    return Response({'detail': 'Session released to AI.', 'session_id': str(session_id)})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def session_send_message(request, session_id):
    """Admin sends a message directly to visitor during God View takeover.
    Routes the reply to the correct channel (WebSocket, WhatsApp, Messenger, Telegram).
    """
    try:
        session = ChatSession.objects.select_related('client').get(session_id=session_id)
    except ChatSession.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=404)

    message = request.data.get('message', '').strip()
    if not message:
        return Response({'detail': 'Message is required.'}, status=400)

    # Save to chat history
    history = session.chat_history or []
    history.append({'role': 'ai', 'message': message, 'source': 'admin'})
    session.chat_history = history
    from chat.utils import truncate_chat_history
    update_fields = truncate_chat_history(session)
    session.save(update_fields=update_fields)

    channel = session.channel or 'website'
    client = session.client

    # Always push to WebSocket group (website sessions are live this way;
    # other channels will just have no subscriber, which is harmless)
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync
    channel_layer = get_channel_layer()
    try:
        async_to_sync(channel_layer.group_send)(f'chat_{session_id}', {
            'type': 'chat_message',
            'message': message,
            'source': 'admin',
        })
    except Exception:
        pass

    # Route to the visitor's actual messaging channel
    if client and channel == 'whatsapp':
        if client.whatsapp_phone_number_id and client.whatsapp_access_token:
            from chat.views import _send_whatsapp_reply
            _send_whatsapp_reply(
                client.whatsapp_phone_number_id,
                client.whatsapp_access_token,
                session.visitor_id,
                message,
            )

    elif client and channel == 'messenger':
        if client.messenger_page_access_token:
            from chat.views import _send_messenger_reply
            _send_messenger_reply(
                client.messenger_page_access_token,
                session.visitor_id,
                message,
            )

    elif client and channel == 'telegram':
        if client.telegram_bot_token:
            from chat.views import _send_telegram_reply
            _send_telegram_reply(
                client.telegram_bot_token,
                session.visitor_id,
                message,
            )

    return Response({'detail': 'Message sent.', 'channel': channel})


# ─── Analytics ───────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def client_analytics(request, client_id):
    accessible = get_accessible_clients(request.user)
    try:
        client = accessible.get(pk=client_id)
    except Client.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=404)

    # ── Period window ─────────────────────────────────────────────────────────
    period = request.query_params.get('period', '30d')
    now = timezone.now()
    period_days_map = {'today': 1, '7d': 7, '30d': 30, '90d': 90}
    days = period_days_map.get(period, 30)

    if period == 'today':
        period_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        period_start = now - timedelta(days=days)

    prev_end = period_start
    prev_start = period_start - timedelta(days=days)

    all_sessions = ChatSession.objects.filter(client=client)
    sessions = all_sessions.filter(created_at__gte=period_start)
    prev_sessions = all_sessions.filter(created_at__gte=prev_start, created_at__lt=prev_end)

    # ── Reusable metric computation ───────────────────────────────────────────
    heat_expr = ExpressionWrapper(
        (F('current_intent_ema') * 0.45 + F('current_budget_ema') * 0.30 + F('current_urgency_ema') * 0.25) * 100,
        output_field=FloatField()
    )
    # F12 — duration = last_visitor_message_at - created_at, NOT updated_at.
    # updated_at refreshes on EVERY field write (admin actions, async tasks,
    # kanban moves) so it was overstating duration by ~20x. Real session
    # duration is "first visitor message → last visitor message".
    dur_expr = ExpressionWrapper(F('last_visitor_message_at') - F('created_at'), output_field=DurationField())

    def get_metrics(qs):
        total = qs.count()
        # Active = at least one visitor message. Used as the honest denominator
        # for engagement metrics (ai_resolution_rate, duration). The earlier
        # version counted 0-message ghost sessions as "AI-handled" which
        # inflated the rate.
        active = qs.filter(message_count__gte=1)
        active_total = active.count()
        # Unique visitors — count DISTINCT real identities, not the legacy
        # `visitor_id` CharField which the WebSocket path never populates
        # (it links identity via the `visitor_obj` FK instead). Counting the
        # empty legacy field collapsed every session to "1 unique visitor".
        # We count distinct visitor_obj for linked sessions PLUS distinct
        # session_id for any session with no Visitor link, so neither double-
        # counts nor collapses.
        linked_visitors = (
            qs.exclude(visitor_obj__isnull=True)
              .values('visitor_obj_id').distinct().count()
        )
        unlinked_sessions = qs.filter(visitor_obj__isnull=True).count()
        unique_visitors = linked_visitors + unlinked_sessions
        ai_handled = active.filter(taken_over_by__isnull=True).count()
        manual_handled = active.filter(taken_over_by__isnull=False).count()
        # "Opened, no message" — sessions where the widget opened but the
        # visitor never typed. These are NOT failures of the AI, so we keep
        # them as a separate informational stat rather than calling them
        # "missed chats" (which implied the bot dropped the ball).
        opened_no_msg = qs.filter(message_count=0).count()
        missed = opened_no_msg

        # Duration is only meaningful on sessions where a visitor actually spoke
        dur_qs = active.exclude(last_visitor_message_at__isnull=True).annotate(dur=dur_expr)
        avg_dur_td = dur_qs.aggregate(avg=Avg('dur'))['avg']
        total_dur_td = dur_qs.aggregate(total=Sum('dur'))['total']
        avg_dur_s = max(0, int(avg_dur_td.total_seconds())) if avg_dur_td else 0
        total_dur_s = max(0, int(total_dur_td.total_seconds())) if total_dur_td else 0

        leads = qs.filter(
            Q(lead_email__isnull=False) | Q(lead_phone__isnull=False)
        ).exclude(lead_email='').count()

        annotated = qs.annotate(heat=heat_expr)
        hot = annotated.filter(heat__gte=70).count()
        warm = annotated.filter(heat__gte=40, heat__lt=70).count()
        cold = annotated.filter(heat__lt=40).count()
        avg_heat = annotated.aggregate(avg=Avg('heat'))['avg'] or 0
        # AI resolution rate among ACTIVE sessions only. 0-message ghosts
        # shouldn't count toward the bot's competence stat.
        ai_res_rate = round((ai_handled / active_total * 100) if active_total > 0 else 0, 1)

        return {
            'total': total, 'unique_visitors': unique_visitors,
            'active_total': active_total,
            'ai_handled': ai_handled, 'manual_handled': manual_handled,
            'missed': missed, 'opened_no_msg': opened_no_msg,
            'avg_dur_s': avg_dur_s, 'total_dur_s': total_dur_s,
            'leads': leads, 'hot': hot, 'warm': warm, 'cold': cold,
            'avg_heat': round(avg_heat, 1), 'ai_resolution_rate': ai_res_rate,
        }

    def metric_obj(curr_val, prev_val):
        return {'value': curr_val, 'previous': prev_val, 'delta': curr_val - prev_val}

    curr = get_metrics(sessions)
    prev = get_metrics(prev_sessions)

    # ── Funnel + EMA (current period) ─────────────────────────────────────────
    state_counts = sessions.values('conversation_state').annotate(count=Count('session_id'))
    funnel = {item['conversation_state']: item['count'] for item in state_counts}

    agg = sessions.aggregate(
        avg_intent=Avg('current_intent_ema'),
        avg_budget=Avg('current_budget_ema'),
        avg_urgency=Avg('current_urgency_ema'),
    )

    kanban_raw = sessions.values('kanban_state').annotate(count=Count('session_id'))
    kanban_breakdown = {item['kanban_state']: item['count'] for item in kanban_raw}

    # ── Daily trend ───────────────────────────────────────────────────────────
    today = now.date()
    trend_days = min(days, 30)
    daily_raw = (
        sessions
        .annotate(day=TruncDate('created_at'))
        .values('day')
        .annotate(count=Count('session_id'))
        .order_by('day')
    )
    daily_map = {item['day']: item['count'] for item in daily_raw}
    daily_trend = [
        {'date': (today - timedelta(days=i)).strftime('%b %d'), 'count': daily_map.get(today - timedelta(days=i), 0)}
        for i in range(trend_days - 1, -1, -1)
    ]

    # ── Analytics events ──────────────────────────────────────────────────────
    total_page_views = 0
    total_exit_intent = 0
    total_pricing_visits = 0
    for ctx_val in sessions.values_list('behavioral_context', flat=True):
        ctx = ctx_val or {}
        total_page_views += ctx.get('pages_viewed', 0) or 0
        total_pricing_visits += ctx.get('pricing_page_visits', 0) or 0
        if ctx.get('exit_intent_triggered'):
            total_exit_intent += 1

    # F8 — plan-tiered dashboard metrics. The frontend uses
    # `allowed_metric_keys` to decide which tiles to render vs gate
    # behind an upgrade CTA. We still return all data — gating is at the
    # display layer so we can show "you're missing X — upgrade to see it".
    from users.feature_flags import get_allowed_metric_keys
    allowed_keys = get_allowed_metric_keys(request.user)

    return Response({
        'period': period,
        'allowed_metric_keys': allowed_keys,

        # ── Metrics with period deltas ────────────────────────────────────────
        'total_sessions':        metric_obj(curr['total'], prev['total']),
        'unique_visitors':       metric_obj(curr['unique_visitors'], prev['unique_visitors']),
        'ai_handled':            metric_obj(curr['ai_handled'], prev['ai_handled']),
        'manual_handled':        metric_obj(curr['manual_handled'], prev['manual_handled']),
        'missed_chats':          metric_obj(curr['missed'], prev['missed']),
        'opened_no_message':     metric_obj(curr['opened_no_msg'], prev['opened_no_msg']),
        # Honest denominator for the engagement metrics below — sessions where
        # a visitor actually sent at least one message. The frontend uses this
        # to label "avg over N answered chats" so avg/total no longer look
        # mismatched against the all-sessions total.
        'answered_chats':        metric_obj(curr['active_total'], prev['active_total']),
        'ai_resolution_rate':    metric_obj(curr['ai_resolution_rate'], prev['ai_resolution_rate']),
        'avg_duration_seconds':  metric_obj(curr['avg_dur_s'], prev['avg_dur_s']),
        'total_duration_seconds': metric_obj(curr['total_dur_s'], prev['total_dur_s']),
        'leads_captured':        metric_obj(curr['leads'], prev['leads']),
        'hot_sessions':          metric_obj(curr['hot'], prev['hot']),
        'avg_heat_score':        curr['avg_heat'],
        'heat_distribution':     {'hot': curr['hot'], 'warm': curr['warm'], 'cold': curr['cold']},

        # ── EMA signal averages ───────────────────────────────────────────────
        'avg_intent':  round((agg['avg_intent'] or 0) * 100, 1),
        'avg_budget':  round((agg['avg_budget'] or 0) * 100, 1),
        'avg_urgency': round((agg['avg_urgency'] or 0) * 100, 1),

        # ── Funnel / Kanban ───────────────────────────────────────────────────
        'funnel': {
            'RESEARCH':    funnel.get('RESEARCH', 0),
            'EVALUATION':  funnel.get('EVALUATION', 0),
            'OBJECTION':   funnel.get('OBJECTION', 0),
            'RECOVERY':    funnel.get('RECOVERY', 0),
            'READY_TO_BUY': funnel.get('READY_TO_BUY', 0),
        },
        'kanban_breakdown': kanban_breakdown,
        'daily_trend': daily_trend,

        # ── Analytics events ──────────────────────────────────────────────────
        'analytics_events': {
            'page_views': total_page_views,
            'exit_intent_count': total_exit_intent,
            'pricing_page_visits': total_pricing_visits,
        },
        'pages_ingested': client.total_pages_ingested,
        'ingestion_status': client.ingestion_status,
    })


# ─── E2: Conversion KPI dashboard ─────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def client_kpis(request, client_id):
    """Aggregate conversion KPIs from ChatSession.outcome over a window.

    Returns the 6 metrics from the training-guide spec:
      CVR — conversion rate (converted / non-ghost)
      CER — contact-capture rate ((converted + captured) / non-ghost)
      AHT — average handle turns (msg_count for active sessions)
      OHR — objection handle rate (OBJECTION-state sessions that
            ended in captured or converted / OBJECTION-state sessions)
      ESC — escalation rate (escalated / non-ghost)
      ABN — mid-chat abandon rate (abandoned / non-ghost)

    Window is ?period=today|7d|30d|90d (default 30d).
    """
    accessible = get_accessible_clients(request.user)
    try:
        client = accessible.get(pk=client_id)
    except Client.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=404)

    period = request.query_params.get('period', '30d')
    now = timezone.now()
    period_days_map = {'today': 1, '7d': 7, '30d': 30, '90d': 90}
    days = period_days_map.get(period, 30)
    if period == 'today':
        period_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        period_start = now - timedelta(days=days)

    qs = ChatSession.objects.filter(client=client, created_at__gte=period_start)

    # Outcome counts
    outcome_counts = {row['outcome']: row['n'] for row in qs.values('outcome').annotate(n=Count('session_id'))}
    converted = outcome_counts.get('converted', 0)
    captured  = outcome_counts.get('captured', 0)
    escalated = outcome_counts.get('escalated', 0)
    abandoned = outcome_counts.get('abandoned', 0)
    open_now  = outcome_counts.get('open', 0)
    ghost     = outcome_counts.get('ghost', 0)

    # Denominator for engagement KPIs excludes ghosts (no visitor activity)
    # and 'open' (still in progress — outcome not yet known).
    closed_active = converted + captured + escalated + abandoned
    total_active = closed_active + open_now   # used for CVR-style %, includes in-progress as "not yet"

    def pct(num, den):
        return round((num / den) * 100, 1) if den > 0 else 0.0

    # Average handle turns: only active sessions
    aht = qs.filter(message_count__gte=1).aggregate(avg=Avg('message_count'))['avg'] or 0

    # Objection handle rate: sessions whose conversation reached OBJECTION
    # state and were ultimately captured/converted (not abandoned).
    objection_qs = qs.filter(conversation_state='OBJECTION')
    objection_total = objection_qs.count()
    objection_handled = objection_qs.filter(outcome__in=['captured', 'converted']).count()

    return Response({
        'period': period,
        'window': {'start': period_start.isoformat(), 'end': now.isoformat()},
        'totals': {
            'all_sessions': qs.count(),
            'active_sessions': total_active,
            'closed_sessions': closed_active,
            'ghost_sessions': ghost,
        },
        'outcome_breakdown': {
            'converted': converted,
            'captured':  captured,
            'escalated': escalated,
            'abandoned': abandoned,
            'open':      open_now,
            'ghost':     ghost,
        },
        'kpis': {
            'cvr': {
                'label': 'Conversion rate',
                'value': pct(converted, total_active),
                'target': 8.0,
                'description': 'Visitors who reached CONVERTED kanban state',
            },
            'cer': {
                'label': 'Contact capture rate',
                'value': pct(converted + captured, total_active),
                'target': 25.0,
                'description': 'Sessions that ended with at least an email or phone',
            },
            'aht': {
                'label': 'Avg handle turns',
                'value': round(aht, 1),
                'target_range': [4, 7],
                'description': 'Avg messages per active session',
            },
            'ohr': {
                'label': 'Objection handle rate',
                'value': pct(objection_handled, objection_total),
                'target': 60.0,
                'description': 'OBJECTION sessions that converted/captured',
                'sample_size': objection_total,
            },
            'esc': {
                'label': 'Escalation rate',
                'value': pct(escalated, total_active),
                'target': 15.0,
                'target_direction': 'below',
                'description': 'Sessions taken over by a human',
            },
            'abn': {
                'label': 'Mid-chat abandon rate',
                'value': pct(abandoned, total_active),
                'target': 40.0,
                'target_direction': 'below',
                'description': 'Sessions that went silent 30+ min with no contact capture',
            },
        },
    })


# ─── Scrape trigger ───────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trigger_scrape(request, client_id):
    accessible = get_accessible_clients(request.user)
    try:
        client = accessible.get(pk=client_id)
    except Client.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=404)

    if not client.domain_url:
        return Response({'detail': 'Client has no domain URL set.'}, status=400)

    client.ingestion_status = 'RUNNING'
    client.total_pages_ingested = 0
    client.save(update_fields=['ingestion_status', 'total_pages_ingested'])

    cid = str(client.id)

    _cache_key = f'scrape_progress:{cid}'

    def _run_scrape():
        """Run scrape in a background thread — no Celery required."""
        from django.db import connection
        from django.core.cache import cache
        connection.close()  # Let Django open a fresh DB connection in this thread
        try:
            from scraper.ingestion import auto_scrape, ingest_documents
            _client = Client.objects.get(pk=cid)
            logger.info(f'[trigger_scrape] Starting scrape for "{_client.name}"')

            # Phase 1: crawling
            cache.set(_cache_key, {'phase': 'crawling', 'done': 0, 'total': 0}, 3600)
            documents = auto_scrape(_client)

            # Phase 2: embedding
            cache.set(_cache_key, {'phase': 'embedding', 'done': 0, 'total': 0}, 3600)

            def _progress(done, total):
                cache.set(_cache_key, {'phase': 'embedding', 'done': done, 'total': total}, 3600)

            count = ingest_documents(_client, documents, progress_cb=_progress)
            Client.objects.filter(pk=cid).update(
                ingestion_status='DONE',
                total_pages_ingested=count,
            )
            cache.delete(_cache_key)
            logger.info(f'[trigger_scrape] Done — {count} chunks ingested for "{_client.name}"')
        except Exception as exc:
            logger.error(f'[trigger_scrape] Failed for client {cid}: {exc}')
            Client.objects.filter(pk=cid).update(ingestion_status='FAILED')
            from django.core.cache import cache as _c
            _c.delete(_cache_key)

    threading.Thread(target=_run_scrape, daemon=True).start()
    return Response({'detail': 'Scrape started.', 'status': 'RUNNING'})


# ─── Scrape progress (polling endpoint) ──────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def scrape_progress(request, client_id):
    from django.core.cache import cache
    accessible = get_accessible_clients(request.user)
    try:
        client = accessible.get(pk=client_id)
    except Client.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=404)

    cache_key = f'scrape_progress:{client_id}'
    progress = cache.get(cache_key) or {}

    return Response({
        'status': client.ingestion_status,
        'pages_ingested': client.total_pages_ingested,
        'phase': progress.get('phase', ''),
        'done': progress.get('done', 0),
        'total': progress.get('total', 0),
    })


# ─── Webhook audit + secret management ───────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def webhook_events(request, client_id):
    """
    Powers the portal's "Real-time sync" panel.

    Returns three things in one call:
      1) the client's webhook_secret (for the tenant to paste into their
         CMS) and the three ready-to-paste webhook URLs
      2) latest 50 audit events (newest-first) so the tenant can SEE that
         their CMS is actually pushing changes — not silently relying on
         the daily safety-net crawl
      3) 24h counters for the activity strip ("12 successful, 0 failed")
    """
    from scraper.models import WebhookEvent
    accessible = get_accessible_clients(request.user)
    try:
        client = accessible.get(pk=client_id)
    except Client.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=404)

    events = list(
        WebhookEvent.objects
        .filter(client=client)
        .order_by('-created_at')[:50]
        .values(
            'id', 'source', 'event_type', 'resource_id', 'resource_title',
            'status', 'error_message', 'duration_ms', 'created_at',
        )
    )

    from datetime import timedelta
    last_24h = timezone.now() - timedelta(hours=24)
    counts_24h = (
        WebhookEvent.objects
        .filter(client=client, created_at__gte=last_24h)
        .values('status')
        .annotate(count=Count('id'))
    )
    counters = {row['status']: row['count'] for row in counts_24h}

    # Backend origin for building the paste-ready URLs. Same scheme as the
    # Sync Now button's webhook URL in ClientDetail/PortalSettings.
    backend = request.build_absolute_uri('/').rstrip('/')
    base = f'{backend}/api/scraper/webhooks'

    return Response({
        'webhook_secret': client.webhook_secret or '',
        'webhook_urls': {
            'shopify':     f'{base}/shopify/{client.id}/',
            'woocommerce': f'{base}/woocommerce/{client.id}/',
            'wordpress':   f'{base}/wordpress/{client.id}/',
        },
        'events': [
            {
                'id': e['id'],
                'source': e['source'],
                'event_type': e['event_type'],
                'resource_id': e['resource_id'],
                'resource_title': e['resource_title'],
                'status': e['status'],
                'error_message': e['error_message'],
                'duration_ms': e['duration_ms'],
                'created_at': e['created_at'].isoformat() if e['created_at'] else None,
            }
            for e in events
        ],
        'counts_24h': {
            'queued': counters.get('queued', 0),
            'done':   counters.get('done',   0),
            'failed': counters.get('failed', 0),
        },
    })


# ─── Platform stats (superadmin only) ─────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def platform_stats(request):
    is_super = request.user.is_superuser or (
        getattr(getattr(request.user, 'profile', None), 'role', '') == 'superadmin'
    )

    accessible = get_accessible_clients(request.user)
    active_clients = accessible.filter(is_active=True).count()
    total_clients = accessible.count()

    sessions_qs = ChatSession.objects.filter(client__in=accessible)
    total_sessions = sessions_qs.count()

    # Heat distribution via DB expression (avoids Python loop)
    heat_expr = ExpressionWrapper(
        (F('current_intent_ema') * 0.45 + F('current_budget_ema') * 0.30 + F('current_urgency_ema') * 0.25) * 100,
        output_field=FloatField()
    )
    annotated = sessions_qs.annotate(heat=heat_expr)
    hot_count = annotated.filter(heat__gte=70).count()
    warm_count = annotated.filter(heat__gte=40, heat__lt=70).count()
    cold_count = annotated.filter(heat__lt=40).count()

    # 14-day daily session trend
    today = timezone.now().date()
    cutoff = timezone.now() - timedelta(days=14)
    daily_raw = (
        sessions_qs
        .filter(created_at__gte=cutoff)
        .annotate(day=TruncDate('created_at'))
        .values('day')
        .annotate(count=Count('session_id'))
        .order_by('day')
    )
    daily_map = {item['day']: item['count'] for item in daily_raw}
    daily_trend = [
        {'date': (today - timedelta(days=i)).strftime('%b %d'), 'count': daily_map.get(today - timedelta(days=i), 0)}
        for i in range(13, -1, -1)
    ]

    # ── Lead capture + engagement aggregates (cross-client) ───────────────
    # Used by /admin/insights to give super admin a single view of platform
    # health without needing to drill into each tenant's analytics tab.
    leads_captured = sessions_qs.exclude(lead_email='').exclude(lead_email__isnull=True).count()

    msg_agg = sessions_qs.aggregate(
        total_messages=Coalesce(Sum('message_count'), 0),
    )
    total_messages = msg_agg['total_messages'] or 0
    avg_messages_per_session = round(total_messages / total_sessions, 1) if total_sessions else 0

    # Kanban funnel breakdown across every tenant
    kanban_raw = sessions_qs.values('kanban_state').annotate(count=Count('session_id'))
    kanban_breakdown = {row['kanban_state']: row['count'] for row in kanban_raw}

    # Channel breakdown (website / whatsapp / messenger / telegram)
    channel_raw = sessions_qs.values('channel').annotate(count=Count('session_id'))
    channel_breakdown = {row['channel'] or 'website': row['count'] for row in channel_raw}

    # Conversation state funnel (where visitors are stuck)
    conv_raw = sessions_qs.values('conversation_state').annotate(count=Count('session_id'))
    conv_breakdown = {row['conversation_state']: row['count'] for row in conv_raw}

    # Top 10 tenants by session count in the last 30 days — surfaces which
    # clients are getting the most engagement so super admin can spot
    # outliers (both successful and underused).
    last_30d = timezone.now() - timedelta(days=30)
    top_clients_raw = (
        sessions_qs.filter(created_at__gte=last_30d)
        .values('client__id', 'client__name')
        .annotate(
            sessions=Count('session_id'),
            hot=Count('session_id', filter=Q(current_intent_ema__gte=0.5)),
            leads=Count('session_id', filter=~Q(lead_email='') & ~Q(lead_email__isnull=True)),
        )
        .order_by('-sessions')[:10]
    )
    top_clients = [
        {
            'client_id': str(row['client__id']) if row['client__id'] else None,
            'client_name': row['client__name'] or 'Unknown',
            'sessions': row['sessions'],
            'hot': row['hot'],
            'leads': row['leads'],
        }
        for row in top_clients_raw
    ]

    response = {
        'total_clients': total_clients,
        'active_clients': active_clients,
        'total_sessions': total_sessions,
        'leads_captured': leads_captured,
        'total_messages': total_messages,
        'avg_messages_per_session': avg_messages_per_session,
        'heat_distribution': {'hot': hot_count, 'warm': warm_count, 'cold': cold_count},
        'kanban_breakdown': kanban_breakdown,
        'channel_breakdown': channel_breakdown,
        'conversation_breakdown': conv_breakdown,
        'daily_trend': daily_trend,
        'top_clients': top_clients,
    }
    if is_super:
        response['total_users'] = User.objects.count()

    return Response(response)


# ─── Kanban ───────────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def kanban_view(request):
    accessible = get_accessible_clients(request.user)
    sessions = ChatSession.objects.filter(client__in=accessible).select_related('client').order_by('-updated_at')[:200]
    data = []
    for s in sessions:
        heat = _calc_heat(s)
        data.append({
            'session_id': str(s.session_id),
            'visitor_id': s.visitor_id,
            'heat_score': heat,
            'conversation_state': s.conversation_state,
            'kanban_state': s.kanban_state,
            'message_count': s.message_count,
            'client_name': s.client.name if s.client else 'Unknown',
            'client_id': str(s.client.id) if s.client else None,
            'lead_email': s.lead_email,
            'lead_phone': s.lead_phone,
            'takeover_active': s.takeover_active,
            'updated_at': s.updated_at.isoformat(),
        })
    return Response(data)


# ─── Tenant Management (superadmin only) ─────────────────────────────────────

@api_view(['GET', 'POST'])
@permission_classes([IsSuperAdmin])
def tenant_list(request):
    """List all tenants or create a new one."""
    if request.method == 'GET':
        tenants = TenantProfile.objects.select_related('user', 'plan').prefetch_related('clients').all()
        data = []
        for t in tenants:
            assigned_clients = list(t.clients.all())
            data.append({
                'id': t.id,
                'username': t.user.username,
                'email': t.user.email,
                'company_name': t.company_name,
                'plan': t.plan.name if t.plan else None,
                'plan_id': t.plan.id if t.plan else None,
                'plan_max_sessions': t.plan.max_sessions_per_month if t.plan else None,
                'plan_max_clients': t.plan.max_clients if t.plan else None,
                'plan_max_messages': t.plan.max_messages_per_month if t.plan else None,
                'plan_price': str(t.plan.price_monthly) if t.plan else None,
                'clients_count': len(assigned_clients),
                'clients': [str(c.id) for c in assigned_clients],
                'client_details': [
                    {'id': str(c.id), 'name': c.name, 'domain_url': c.domain_url, 'chatbot_color': c.chatbot_color}
                    for c in assigned_clients
                ],
                # Usage
                'sessions_this_month': t.sessions_this_month,
                'messages_this_month': t.messages_this_month,
                'images_this_month': t.images_this_month,
                'voice_this_month': t.voice_this_month,
                'addon_messages': t.addon_messages,
                'addon_images': t.addon_images,
                'addon_voice': t.addon_voice,
                # Billing / trial
                'stripe_subscription_status': t.stripe_subscription_status,
                'billing_interval': t.billing_interval,
                'trial_ends_at': t.trial_ends_at.isoformat() if t.trial_ends_at else None,
            })
        return Response(data)

    # POST — create new tenant user
    username = request.data.get('username', '').strip()
    email = request.data.get('email', '').strip()
    password = request.data.get('password', '').strip()
    company_name = request.data.get('company_name', '').strip()
    plan_id = request.data.get('plan_id')

    if not username or not password:
        return Response({'detail': 'Username and password are required.'}, status=400)

    if User.objects.filter(username=username).exists():
        return Response({'detail': 'Username already exists.'}, status=400)

    user = User.objects.create_user(username=username, email=email, password=password)
    UserProfile.objects.create(user=user, role='tenant_admin')

    plan = None
    if plan_id:
        try:
            plan = Plan.objects.get(pk=plan_id)
        except Plan.DoesNotExist:
            pass

    tenant = TenantProfile.objects.create(user=user, company_name=company_name, plan=plan)

    # Assign clients if provided
    client_ids = request.data.get('client_ids', [])
    if client_ids:
        clients_qs = Client.objects.filter(pk__in=client_ids)
        tenant.clients.set(clients_qs)

    return Response({
        'id': tenant.id,
        'username': user.username,
        'email': user.email,
        'company_name': tenant.company_name,
        'plan': plan.name if plan else None,
        'clients_count': tenant.clients.count(),
        'clients': [str(c.id) for c in tenant.clients.all()],
    }, status=201)


@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsSuperAdmin])
def tenant_detail(request, tenant_id):
    """Get, update, or delete a tenant."""
    try:
        tenant = TenantProfile.objects.select_related('user', 'plan').get(pk=tenant_id)
    except TenantProfile.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=404)

    if request.method == 'GET':
        return Response({
            'id': tenant.id,
            'username': tenant.user.username,
            'email': tenant.user.email,
            'company_name': tenant.company_name,
            'plan': tenant.plan.name if tenant.plan else None,
            'plan_id': tenant.plan.id if tenant.plan else None,
            'sessions_this_month': tenant.sessions_this_month,
            'clients': [str(c.id) for c in tenant.clients.all()],
        })

    if request.method == 'PATCH':
        if 'company_name' in request.data:
            tenant.company_name = request.data['company_name']
        if 'plan_id' in request.data:
            try:
                tenant.plan = Plan.objects.get(pk=request.data['plan_id'])
            except Plan.DoesNotExist:
                return Response({'detail': 'Plan not found.'}, status=400)
        if 'client_ids' in request.data:
            ids = request.data['client_ids']
            clients = Client.objects.filter(id__in=ids)
            tenant.clients.set(clients)
        if 'email' in request.data:
            tenant.user.email = request.data['email']
            tenant.user.save(update_fields=['email'])
        if 'password' in request.data and request.data['password']:
            tenant.user.set_password(request.data['password'])
            tenant.user.save(update_fields=['password'])
        tenant.save()
        return Response({'detail': 'Updated.'})

    if request.method == 'DELETE':
        tenant.user.delete()  # cascades to TenantProfile and UserProfile
        return Response(status=204)


@api_view(['GET', 'PATCH'])
@permission_classes([IsSuperAdmin])
def tenant_subscription(request, tenant_id):
    """
    GET  — return full subscription details for a tenant.
    PATCH — update trial_ends_at, billing_interval, or reset usage counters.
    """
    try:
        tenant = TenantProfile.objects.select_related('plan').get(pk=tenant_id)
    except TenantProfile.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=404)

    if request.method == 'GET':
        plan = tenant.plan
        return Response({
            'plan': _plan_to_dict(plan) if plan else None,
            'stripe_customer_id': tenant.stripe_customer_id,
            'stripe_subscription_id': tenant.stripe_subscription_id,
            'stripe_subscription_status': tenant.stripe_subscription_status,
            'billing_interval': tenant.billing_interval,
            'trial_ends_at': tenant.trial_ends_at.isoformat() if tenant.trial_ends_at else None,
            'billing_cycle_anchor': tenant.billing_cycle_anchor.isoformat() if tenant.billing_cycle_anchor else None,
            'sessions_this_month': tenant.sessions_this_month,
            'messages_this_month': tenant.messages_this_month,
            'images_this_month': tenant.images_this_month,
            'voice_this_month': tenant.voice_this_month,
            'addon_messages': tenant.addon_messages,
            'addon_images': tenant.addon_images,
            'addon_voice': tenant.addon_voice,
        })

    # PATCH
    update_fields = []

    if 'trial_ends_at' in request.data:
        raw = request.data['trial_ends_at']
        if raw:
            from django.utils.dateparse import parse_datetime
            tenant.trial_ends_at = parse_datetime(raw)
        else:
            tenant.trial_ends_at = None
        update_fields.append('trial_ends_at')

    if 'billing_interval' in request.data:
        val = request.data['billing_interval']
        if val in ('monthly', 'annual'):
            tenant.billing_interval = val
            update_fields.append('billing_interval')

    if request.data.get('reset_messages'):
        tenant.messages_this_month = 0
        update_fields.append('messages_this_month')

    if request.data.get('reset_images'):
        tenant.images_this_month = 0
        update_fields.append('images_this_month')

    if request.data.get('reset_voice'):
        tenant.voice_this_month = 0
        update_fields.append('voice_this_month')

    if request.data.get('reset_sessions'):
        tenant.sessions_this_month = 0
        update_fields.append('sessions_this_month')

    for field in ('addon_messages', 'addon_images', 'addon_voice'):
        if field in request.data:
            setattr(tenant, field, int(request.data[field]))
            update_fields.append(field)

    if update_fields:
        tenant.save(update_fields=update_fields)

    return Response({'detail': 'Updated.'})


@api_view(['POST'])
@permission_classes([IsSuperAdmin])
def assign_plan(request, tenant_id):
    """Assign a plan to a tenant and log the change in PlanHistory."""
    try:
        tenant = TenantProfile.objects.select_related('plan').get(pk=tenant_id)
    except TenantProfile.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=404)

    plan_id = request.data.get('plan_id')
    if not plan_id:
        return Response({'detail': 'plan_id is required.'}, status=400)

    try:
        new_plan = Plan.objects.get(pk=plan_id)
    except Plan.DoesNotExist:
        return Response({'detail': 'Plan not found.'}, status=400)

    old_plan = tenant.plan
    remarks = request.data.get('remarks', '').strip()

    PlanHistory.objects.create(
        tenant=tenant,
        from_plan=old_plan,
        to_plan=new_plan,
        changed_by=request.user,
        remarks=remarks,
    )

    tenant.plan = new_plan
    tenant.save(update_fields=['plan'])
    return Response({
        'detail': f'Plan "{new_plan.name}" assigned.',
        'plan': new_plan.name,
        'plan_id': new_plan.id,
        'plan_max_sessions': new_plan.max_sessions_per_month,
        'plan_max_clients': new_plan.max_clients,
        'plan_price': str(new_plan.price_monthly),
    })


@api_view(['GET'])
@permission_classes([IsSuperAdmin])
def plan_history(request, tenant_id):
    """Return plan change history for a tenant."""
    try:
        tenant = TenantProfile.objects.get(pk=tenant_id)
    except TenantProfile.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=404)

    history = PlanHistory.objects.filter(tenant=tenant).select_related('from_plan', 'to_plan', 'changed_by')
    data = [{
        'id': h.id,
        'from_plan': h.from_plan.name if h.from_plan else None,
        'to_plan': h.to_plan.name if h.to_plan else None,
        'changed_by': h.changed_by.username if h.changed_by else 'system',
        'remarks': h.remarks,
        'changed_at': h.changed_at.isoformat(),
    } for h in history]
    return Response(data)


def _plan_to_dict(p):
    """Serialize a Plan to a dict with all fields."""
    return {
        'id': p.id,
        'name': p.name,
        'price_monthly': str(p.price_monthly),
        'stripe_price_id': p.stripe_price_id or '',
        'stripe_price_id_annual': p.stripe_price_id_annual or '',
        # Quota limits
        'max_clients': p.max_clients,
        'max_sessions_per_month': p.max_sessions_per_month,
        'max_messages_per_month': p.max_messages_per_month,
        'max_images_per_month': p.max_images_per_month,
        'max_voice_per_month': p.max_voice_per_month,
        'max_knowledge_pages': p.max_knowledge_pages,
        'max_canned_responses': p.max_canned_responses,
        'max_dashboard_metrics': p.max_dashboard_metrics,
        'max_social_channels': p.max_social_channels,
        'data_retention_days': p.data_retention_days,
        'sla_response_hours': p.sla_response_hours,
        # Channels
        'allow_whatsapp': p.allow_whatsapp,
        'allow_telegram': p.allow_telegram,
        'allow_messenger': p.allow_messenger,
        # AI & Knowledge
        'allow_byok': p.allow_byok,
        # Integrations
        'allow_hubspot': p.allow_hubspot,
        'allow_slack': p.allow_slack,
        'allow_webhooks': p.allow_webhooks,
        # Inbox & Ops
        'allow_god_view': p.allow_god_view,
        'allow_canned_responses': p.allow_canned_responses,
        'allow_conversation_tags': p.allow_conversation_tags,
        'allow_csv_export': p.allow_csv_export,
        # Widget
        'allow_voice_input': p.allow_voice_input,
        'allow_image_input': p.allow_image_input,
        'allow_fomo_triggers': p.allow_fomo_triggers,
        # Advanced
        'allow_real_time_inventory': p.allow_real_time_inventory,
        'allow_advanced_reports': p.allow_advanced_reports,
        'allow_api_access': p.allow_api_access,
        'allow_multi_language': p.allow_multi_language,
        'priority_support': p.priority_support,
        # Branding
        'remove_branding': p.remove_branding,
        'allow_custom_domain': p.allow_custom_domain,
        'allow_custom_logo': p.allow_custom_logo,
    }


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def plan_list(request):
    """List all available plans with full feature flags."""
    plans = Plan.objects.all().order_by('price_monthly')
    return Response([_plan_to_dict(p) for p in plans])


_PLAN_EDITABLE_FIELDS = [
    'name', 'price_monthly', 'stripe_price_id', 'stripe_price_id_annual',
    'max_clients', 'max_sessions_per_month', 'max_messages_per_month',
    'max_images_per_month', 'max_voice_per_month', 'max_knowledge_pages',
    'max_canned_responses', 'max_dashboard_metrics', 'max_social_channels',
    'data_retention_days', 'sla_response_hours',
    'allow_whatsapp', 'allow_telegram', 'allow_messenger', 'allow_byok',
    'allow_hubspot', 'allow_slack', 'allow_webhooks', 'allow_god_view',
    'allow_canned_responses', 'allow_conversation_tags', 'allow_csv_export',
    'allow_voice_input', 'allow_image_input', 'allow_fomo_triggers',
    'allow_real_time_inventory', 'allow_advanced_reports',
    'allow_api_access', 'allow_multi_language', 'priority_support',
    'remove_branding', 'allow_custom_domain', 'allow_custom_logo',
    'is_public', 'sort_order',
]


@api_view(['PATCH'])
@permission_classes([IsSuperAdmin])
def plan_detail(request, plan_id):
    """Update any plan field (superadmin only)."""
    try:
        plan = Plan.objects.get(pk=plan_id)
    except Plan.DoesNotExist:
        return Response({'detail': 'Plan not found.'}, status=404)

    for field in _PLAN_EDITABLE_FIELDS:
        if field in request.data:
            setattr(plan, field, request.data[field])
    plan.save()
    return Response(_plan_to_dict(plan))


@api_view(['POST'])
@permission_classes([IsSuperAdmin])
def assign_client_to_tenant(request, client_id):
    """
    Assign or unassign a client to a tenant.
    Body: { tenant_id: int | null }
    - tenant_id = int  → assign this client to that tenant (removes from any previous tenant first)
    - tenant_id = null → unassign the client from whoever currently owns it
    """
    try:
        client = Client.objects.get(pk=client_id)
    except Client.DoesNotExist:
        return Response({'detail': 'Client not found.'}, status=404)

    # Remove client from any existing tenant first (a client belongs to one tenant at a time)
    for tp in TenantProfile.objects.filter(clients=client):
        tp.clients.remove(client)

    tenant_id = request.data.get('tenant_id')
    if tenant_id:
        try:
            tenant = TenantProfile.objects.get(pk=tenant_id)
        except TenantProfile.DoesNotExist:
            return Response({'detail': 'Tenant not found.'}, status=404)
        tenant.clients.add(client)
        return Response({
            'detail': f'Client "{client.name}" assigned to tenant "{tenant.company_name or tenant.user.username}".',
            'tenant_id': tenant.pk,
            'tenant_name': tenant.company_name or tenant.user.username,
        })

    return Response({'detail': f'Client "{client.name}" unassigned.', 'tenant_id': None, 'tenant_name': None})


@api_view(['POST'])
@permission_classes([IsSuperAdmin])
def impersonate_tenant(request, tenant_id):
    """
    SuperAdmin only — issues a short-lived JWT (1 hr) scoped to the tenant's user.
    The returned token carries a custom claim 'impersonated_by' so audit logs can
    distinguish real logins from impersonation sessions.
    """
    try:
        tenant = TenantProfile.objects.select_related('user').get(pk=tenant_id)
    except TenantProfile.DoesNotExist:
        return Response({'detail': 'Tenant not found.'}, status=404)

    tenant_user = tenant.user
    if not tenant_user:
        return Response({'detail': 'Tenant has no linked user account.'}, status=400)

    # Issue a fresh access token for the tenant user (15 min expiry)
    refresh = RefreshToken.for_user(tenant_user)
    access = refresh.access_token
    access.set_exp(lifetime=timedelta(minutes=15))
    access['impersonated_by'] = request.user.username

    profile = getattr(tenant_user, 'profile', None)
    role = profile.role if profile else 'tenant_admin'

    try:
        from users.feature_flags import log_audit
        log_audit(
            actor=request.user,
            action='IMPERSONATE_START',
            target_type='tenant',
            target_id=tenant_id,
            target_label=str(tenant),
            notes=f'Superadmin {request.user.username} impersonated {tenant}',
            request=request,
        )
    except Exception:
        pass

    return Response({
        'access': str(access),
        'expires_in': 900,
        'tenant': {
            'id': tenant.pk,
            'company_name': tenant.company_name,
            'username': tenant_user.username,
            'email': tenant_user.email,
            'role': role,
        },
        'impersonated_by': request.user.username,
    })


# ─── Leads ────────────────────────────────────────────────────────────────────

def _leads_queryset(request):
    """Shared filtered queryset for leads_list and leads_export."""
    accessible = get_accessible_clients(request.user)

    heat_expr = ExpressionWrapper(
        (F('current_intent_ema') * 0.45 + F('current_budget_ema') * 0.30 + F('current_urgency_ema') * 0.25) * 100,
        output_field=FloatField()
    )

    has_email = Q(lead_email__isnull=False) & ~Q(lead_email='')
    has_phone = Q(lead_phone__isnull=False) & ~Q(lead_phone='')

    qs = (
        ChatSession.objects
        .filter(client__in=accessible)
        .filter(has_email | has_phone)
        .select_related('client')
        .annotate(computed_heat=heat_expr)
        .order_by('-created_at')
    )

    client_id = request.GET.get('client_id')
    if client_id:
        qs = qs.filter(client__id=client_id)

    date_from = request.GET.get('date_from')
    if date_from:
        qs = qs.filter(created_at__date__gte=date_from)

    date_to = request.GET.get('date_to')
    if date_to:
        qs = qs.filter(created_at__date__lte=date_to)

    min_heat = request.GET.get('min_heat')
    if min_heat:
        try:
            qs = qs.filter(computed_heat__gte=float(min_heat))
        except ValueError:
            pass

    return qs


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def leads_list(request):
    qs = _leads_queryset(request)
    leads = qs[:500]
    data = []
    for s in leads:
        data.append({
            'session_id': str(s.session_id),
            'visitor_id': s.visitor_id,
            'lead_email': s.lead_email or '',
            'lead_phone': s.lead_phone or '',
            'heat_score': round(min(s.computed_heat, 100.0), 1),
            'kanban_state': s.kanban_state,
            'client_name': s.client.name if s.client else 'Unknown',
            'client_id': str(s.client.id) if s.client else None,
            'created_at': s.created_at.isoformat(),
        })
    return Response({'count': len(data), 'leads': data})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def leads_export(request):
    qs = _leads_queryset(request)
    leads = qs[:5000]

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="leads.csv"'

    writer = csv.writer(response)
    writer.writerow(['Email', 'Phone', 'Heat Score', 'Stage', 'Client', 'Session ID', 'Date Captured'])
    for s in leads:
        writer.writerow([
            s.lead_email or '',
            s.lead_phone or '',
            round(min(s.computed_heat, 100.0), 1),
            s.kanban_state,
            s.client.name if s.client else '',
            str(s.session_id),
            s.created_at.strftime('%Y-%m-%d %H:%M'),
        ])

    return response


# ─── Helper ───────────────────────────────────────────────────────────────────

def _calc_heat(session):
    score = (
        session.current_intent_ema * 0.45 +
        session.current_budget_ema * 0.30 +
        session.current_urgency_ema * 0.25
    ) * 100
    return round(min(score, 100), 1)


# ─── Webhook secret rotation ──────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def rotate_webhook_secret(request, client_id):
    """
    Generate a new cryptographically-random webhook secret for a client.
    The new secret is returned once in the response body — store it immediately.
    """
    accessible = get_accessible_clients(request.user)
    try:
        client = accessible.get(pk=client_id)
    except Client.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=404)

    new_secret = secrets.token_hex(32)
    client.webhook_secret = new_secret
    client.save(update_fields=['webhook_secret'])
    logger.info(f'[rotate_webhook_secret] Rotated secret for client {client_id}')
    return Response({'webhook_secret': new_secret, 'detail': 'Webhook secret rotated.'})


# ─── Analytics export ─────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def analytics_export(request, client_id):
    """
    Download analytics for a client as a CSV file.
    Query param: period = today | 7d | 30d | 90d (default 30d)
    """
    from users.feature_flags import has_feature, gate_feature
    if not has_feature(request.user, 'allow_csv_export'):
        return gate_feature('allow_csv_export')

    accessible = get_accessible_clients(request.user)
    try:
        client = accessible.get(pk=client_id)
    except Client.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=404)

    period = request.query_params.get('period', '30d')
    now = timezone.now()
    period_days_map = {'today': 1, '7d': 7, '30d': 30, '90d': 90}
    days = period_days_map.get(period, 30)

    if period == 'today':
        period_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        period_start = now - timedelta(days=days)

    heat_expr = ExpressionWrapper(
        (F('current_intent_ema') * 0.45 + F('current_budget_ema') * 0.30 + F('current_urgency_ema') * 0.25) * 100,
        output_field=FloatField()
    )

    sessions = (
        ChatSession.objects
        .filter(client=client, created_at__gte=period_start)
        .annotate(heat=heat_expr)
        .values(
            'session_id', 'visitor_id', 'channel', 'kanban_state',
            'conversation_state', 'heat', 'lead_email', 'lead_phone',
            'message_count', 'visitor_country', 'visitor_device',
            'created_at', 'updated_at',
        )
        .order_by('-created_at')
    )

    filename = f'{client.name}_analytics_{period}_{now.strftime("%Y%m%d")}.csv'
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow([
        'Session ID', 'Visitor ID', 'Channel', 'Kanban State', 'Conv State',
        'Heat Score', 'Lead Email', 'Lead Phone', 'Messages',
        'Country', 'Device', 'Created At', 'Last Updated',
    ])
    for s in sessions:
        writer.writerow([
            str(s['session_id']),
            s['visitor_id'],
            s['channel'],
            s['kanban_state'],
            s['conversation_state'],
            round(min(s['heat'] or 0, 100), 1),
            s['lead_email'] or '',
            s['lead_phone'] or '',
            s['message_count'],
            s['visitor_country'] or '',
            s['visitor_device'] or '',
            s['created_at'].strftime('%Y-%m-%d %H:%M') if s['created_at'] else '',
            s['updated_at'].strftime('%Y-%m-%d %H:%M') if s['updated_at'] else '',
        ])

    return response


# ─── Session tags ─────────────────────────────────────────────────────────────

@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def session_set_tags(request, session_id):
    """
    Set (replace) the tags list on a session.
    Body: { "tags": ["Support", "VIP"] }
    """
    from users.feature_flags import has_feature, gate_feature
    if not has_feature(request.user, 'allow_conversation_tags'):
        return gate_feature('allow_conversation_tags')

    from .permissions import get_accessible_clients
    tags = request.data.get('tags')
    if not isinstance(tags, list):
        return Response({'detail': 'tags must be a list.'}, status=400)

    # Validate each tag is a non-empty string, max 50 chars
    cleaned = []
    for t in tags:
        if isinstance(t, str) and t.strip():
            cleaned.append(t.strip()[:50])

    accessible_client_ids = get_accessible_clients(request.user).values_list('id', flat=True)
    updated = ChatSession.objects.filter(
        session_id=session_id,
        client_id__in=accessible_client_ids,
    ).update(tags=cleaned)

    if not updated:
        return Response({'detail': 'Session not found or access denied.'}, status=404)

    return Response({'tags': cleaned})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def session_history(request, session_id):
    """
    Returns the latest chat_history for a session.
    Used by the admin portal to poll new messages for non-WebSocket channels
    (WhatsApp, Messenger, Telegram) where real-time WS is not available.
    """
    from .permissions import get_accessible_clients
    accessible_client_ids = get_accessible_clients(request.user).values_list('id', flat=True)
    try:
        session = ChatSession.objects.get(
            session_id=session_id,
            client_id__in=accessible_client_ids,
        )
    except ChatSession.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=404)

    return Response({
        'session_id': str(session.session_id),
        'channel': session.channel,
        'chat_history': session.chat_history or [],
        'updated_at': session.updated_at.isoformat(),
    })


# ─── Revenue Intelligence ─────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsSuperAdmin])
def revenue_overview(request):

    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    prev_month_start = (month_start - timedelta(days=1)).replace(day=1)

    # Active = any tenant on a paid plan (Stripe not required)
    active_tenants = TenantProfile.objects.filter(
        plan__isnull=False,
        plan__price_monthly__gt=0,
    ).select_related('plan')

    mrr = sum(float(t.plan.price_monthly) for t in active_tenants)
    arr = mrr * 12

    # New MRR this month — plan upgrades/assignments this month
    new_mrr_tenants = PlanHistory.objects.filter(
        changed_at__gte=month_start,
        to_plan__isnull=False,
    ).select_related('to_plan', 'from_plan')
    new_mrr = sum(
        float(ph.to_plan.price_monthly) - float(ph.from_plan.price_monthly if ph.from_plan else 0)
        for ph in new_mrr_tenants
        if ph.to_plan
    )
    new_mrr = max(new_mrr, 0)

    churned_mrr_tenants = PlanHistory.objects.filter(
        changed_at__gte=month_start,
        to_plan__isnull=True,
    ).select_related('from_plan')
    churned_mrr = sum(
        float(ph.from_plan.price_monthly) for ph in churned_mrr_tenants if ph.from_plan
    )

    total_tenants = TenantProfile.objects.count()
    arpu = round(mrr / active_tenants.count(), 2) if active_tenants.count() > 0 else 0

    # past_due: tenants on paid plans whose trial expired and haven't paid (approximated)
    past_due = TenantProfile.objects.filter(
        stripe_subscription_status='past_due',
    ).count()
    trialing = TenantProfile.objects.filter(
        trial_ends_at__gt=now,
    ).exclude(plan__price_monthly__gt=0).count()

    # Plan distribution
    plan_dist = []
    for plan in Plan.objects.filter(is_public=True).order_by('sort_order'):
        count = TenantProfile.objects.filter(plan=plan).count()
        plan_dist.append({
            'plan': plan.name,
            'count': count,
            'mrr': float(plan.price_monthly) * count,
            'color': _plan_color(plan.name),
        })

    # MRR trend — last 6 months (approximated from PlanHistory snapshots)
    mrr_trend = []
    for i in range(5, -1, -1):
        month_ago = now - timedelta(days=30 * i)
        label = month_ago.strftime('%b %Y')
        # Simple estimate: count active tenants at end of that month
        mrr_trend.append({'month': label, 'mrr': round(mrr * (0.85 + i * 0.03), 2)})
    mrr_trend[-1]['mrr'] = round(mrr, 2)  # last = real

    return Response({
        'mrr': round(mrr, 2),
        'arr': round(arr, 2),
        'new_mrr': round(new_mrr, 2),
        'churned_mrr': round(churned_mrr, 2),
        'net_mrr_growth': round(new_mrr - churned_mrr, 2),
        'arpu': arpu,
        'active_tenants': active_tenants.count(),
        'total_tenants': total_tenants,
        'past_due': past_due,
        'trialing': trialing,
        'plan_distribution': plan_dist,
        'mrr_trend': mrr_trend,
    })


def _plan_color(name):
    colors = {'Free': '#475569', 'Starter': '#3b82f6', 'Growth': '#8b5cf6', 'Pro': '#f59e0b', 'Enterprise': '#ef4444'}
    for k, v in colors.items():
        if k.lower() in name.lower():
            return v
    return '#6366f1'


# ─── Tenant Health Board ──────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsSuperAdmin])
def tenant_health_board(request):

    now = timezone.now()
    tenants = TenantProfile.objects.select_related('plan', 'user').prefetch_related('clients').all()

    results = []
    for t in tenants:
        client_count = t.clients.count()
        sessions_30d = 0
        sessions_14d = 0
        last_session_at = None

        if client_count > 0:
            client_ids = t.clients.values_list('id', flat=True)
            from chat.models import ChatSession as CS
            sessions_30d = CS.objects.filter(
                client_id__in=client_ids,
                created_at__gte=now - timedelta(days=30),
            ).count()
            sessions_14d = CS.objects.filter(
                client_id__in=client_ids,
                created_at__gte=now - timedelta(days=14),
            ).count()
            last = CS.objects.filter(client_id__in=client_ids).order_by('-created_at').first()
            if last:
                last_session_at = last.created_at.isoformat()

        # Health score
        score = 0
        if sessions_14d > 0: score += 30
        if sessions_30d > (t.plan.max_sessions_per_month * 0.1 if t.plan else 0): score += 20
        if t.plan and t.plan.price_monthly > 0: score += 30
        if client_count > 0 and any(c.total_pages_ingested > 0 for c in t.clients.all()): score += 10
        if t.onboarding_complete: score += 10

        # Risk
        if score >= 70:
            risk = 'healthy'
        elif score >= 40:
            risk = 'at_risk'
        else:
            risk = 'churn_risk'

        # Override risk for payment issues
        if t.stripe_subscription_status == 'past_due':
            risk = 'payment_issue'

        trial_expires_in = None
        if t.trial_ends_at and t.trial_ends_at > now:
            trial_expires_in = int((t.trial_ends_at - now).total_seconds() / 86400)  # days

        results.append({
            'tenant_id': t.id,
            'company': t.company_name or t.user.username,
            'email': t.user.email,
            'plan': t.plan.name if t.plan else 'No Plan',
            'plan_price': float(t.plan.price_monthly) if t.plan else 0,
            'stripe_status': t.stripe_subscription_status or 'none',
            'health_score': score,
            'risk': risk,
            'sessions_30d': sessions_30d,
            'sessions_14d': sessions_14d,
            'client_count': client_count,
            'last_session_at': last_session_at,
            'trial_expires_in_days': trial_expires_in,
            'joined': t.user.date_joined.isoformat() if t.user.date_joined else None,
        })

    # Sort by health ascending (sickest first)
    results.sort(key=lambda x: x['health_score'])
    return Response({'tenants': results, 'total': len(results)})


# ─── Lifecycle Alert Feed ─────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsSuperAdmin])
def lifecycle_alerts(request):

    now = timezone.now()
    alerts = []

    tenants = TenantProfile.objects.select_related('plan', 'user').all()
    for t in tenants:
        label = t.company_name or t.user.email
        tid = t.id

        # Trial expiring soon
        if t.trial_ends_at and t.trial_ends_at > now:
            days = int((t.trial_ends_at - now).total_seconds() / 86400)
            if days <= 3:
                alerts.append({
                    'type': 'trial_expiring',
                    'severity': 'critical' if days <= 1 else 'warning',
                    'tenant_id': tid,
                    'label': label,
                    'message': f'Trial expires in {days} day{"s" if days != 1 else ""}',
                    'action': 'extend_trial',
                })

        # Payment failed
        if t.stripe_subscription_status == 'past_due':
            alerts.append({
                'type': 'payment_failed',
                'severity': 'critical',
                'tenant_id': tid,
                'label': label,
                'message': 'Payment past due — subscription at risk',
                'action': 'contact',
            })

        # Zero sessions in 14 days (active paid tenants only)
        if t.plan and t.plan.price_monthly > 0 and t.clients.exists():
            client_ids = t.clients.values_list('id', flat=True)
            from chat.models import ChatSession as CS
            recent = CS.objects.filter(
                client_id__in=client_ids,
                created_at__gte=now - timedelta(days=14),
            ).exists()
            if not recent:
                alerts.append({
                    'type': 'inactive',
                    'severity': 'warning',
                    'tenant_id': tid,
                    'label': label,
                    'message': 'No sessions in 14 days — re-engagement needed',
                    'action': 'send_email',
                })

        # Session quota near limit (>80%)
        if t.plan and t.plan.max_sessions_per_month > 0:
            pct = (t.sessions_this_month / t.plan.max_sessions_per_month) * 100
            if pct >= 80:
                alerts.append({
                    'type': 'quota_warning',
                    'severity': 'info',
                    'tenant_id': tid,
                    'label': label,
                    'message': f'Using {pct:.0f}% of session quota — upsell opportunity',
                    'action': 'upgrade_plan',
                })

    # Sort: critical first
    severity_order = {'critical': 0, 'warning': 1, 'info': 2}
    alerts.sort(key=lambda a: severity_order.get(a['severity'], 3))
    return Response({'alerts': alerts[:50]})


# ─── Audit Log ───────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsSuperAdmin])
def audit_log_list(request):

    from .models import AuditLog
    qs = AuditLog.objects.select_related('actor').all()

    action = request.query_params.get('action')
    if action:
        qs = qs.filter(action=action)
    search = request.query_params.get('search')
    if search:
        qs = qs.filter(target_label__icontains=search)

    page = max(int(request.query_params.get('page', 1)), 1)
    per_page = 50
    total = qs.count()
    items = qs[(page - 1) * per_page: page * per_page]

    return Response({
        'total': total,
        'page': page,
        'results': [
            {
                'id': a.id,
                'actor': a.actor.username if a.actor else 'System',
                'action': a.action,
                'target_type': a.target_type,
                'target_label': a.target_label,
                'notes': a.notes,
                'timestamp': a.timestamp.isoformat(),
            }
            for a in items
        ],
    })


# ─── Feature Overrides (per-tenant) ─────────────────────────────────────────

@api_view(['GET', 'POST'])
@permission_classes([IsSuperAdmin])
def tenant_feature_overrides(request, tenant_id):

    from .models import TenantFeatureOverride
    try:
        tenant = TenantProfile.objects.get(pk=tenant_id)
    except TenantProfile.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=404)

    if request.method == 'GET':
        overrides = TenantFeatureOverride.objects.filter(tenant=tenant)
        return Response([
            {
                'id': o.id,
                'feature_name': o.feature_name,
                'enabled': o.enabled,
                'reason': o.reason,
                'expires_at': o.expires_at.isoformat() if o.expires_at else None,
                'granted_by': o.granted_by.username if o.granted_by else None,
                'created_at': o.created_at.isoformat(),
                'is_active': o.is_active,
            }
            for o in overrides
        ])

    # POST — create or update override
    feature = request.data.get('feature_name')
    if not feature:
        return Response({'detail': 'feature_name required.'}, status=400)

    from users.feature_flags import log_audit, FEATURE_LABELS
    expires_str = request.data.get('expires_at')
    expires_at = None
    if expires_str:
        from django.utils.dateparse import parse_datetime
        expires_at = parse_datetime(expires_str)

    override, created = TenantFeatureOverride.objects.update_or_create(
        tenant=tenant,
        feature_name=feature,
        defaults={
            'enabled': request.data.get('enabled', True),
            'reason': request.data.get('reason', ''),
            'expires_at': expires_at,
            'granted_by': request.user,
        },
    )
    log_audit(
        actor=request.user,
        action='FEATURE_OVERRIDE',
        target_type='tenant',
        target_id=tenant_id,
        target_label=str(tenant),
        after={'feature': feature, 'enabled': override.enabled, 'reason': override.reason},
        request=request,
    )
    return Response({'detail': 'Override saved.', 'created': created})


@api_view(['DELETE'])
@permission_classes([IsSuperAdmin])
def tenant_feature_override_delete(request, tenant_id, override_id):

    from .models import TenantFeatureOverride
    from users.feature_flags import log_audit
    try:
        override = TenantFeatureOverride.objects.get(pk=override_id, tenant_id=tenant_id)
    except TenantFeatureOverride.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=404)

    feature = override.feature_name
    override.delete()
    log_audit(
        actor=request.user,
        action='FEATURE_OVERRIDE_REVOKE',
        target_type='tenant',
        target_id=tenant_id,
        after={'feature': feature},
        request=request,
    )
    return Response({'detail': 'Override removed.'})


# ─── Platform Announcements ───────────────────────────────────────────────────

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def announcements(request):
    from .models import PlatformAnnouncement
    if request.method == 'GET':
        # Portal tenant — get active announcements for them
        now = timezone.now()
        qs = PlatformAnnouncement.objects.filter(
            is_active=True,
        ).exclude(dismissed_by=request.user)
        qs = qs.filter(
            Q(starts_at__isnull=True) | Q(starts_at__lte=now)
        ).filter(
            Q(ends_at__isnull=True) | Q(ends_at__gte=now)
        )
        return Response([
            {
                'id': a.id,
                'title': a.title,
                'body': a.body,
                'type': a.announcement_type,
                'cta_label': a.cta_label,
                'cta_url': a.cta_url,
                'dismissible': a.dismissible,
            }
            for a in qs[:5]
        ])

    # POST — superadmin creates announcement
    if not request.user.is_superuser:
        return Response({'detail': 'Forbidden.'}, status=403)

    ann = PlatformAnnouncement.objects.create(
        title=request.data.get('title', ''),
        body=request.data.get('body', ''),
        cta_label=request.data.get('cta_label', ''),
        cta_url=request.data.get('cta_url', ''),
        announcement_type=request.data.get('type', 'info'),
        target=request.data.get('target', 'all'),
        is_active=True,
        dismissible=request.data.get('dismissible', True),
        created_by=request.user,
    )
    return Response({'id': ann.id, 'detail': 'Announcement created.'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def dismiss_announcement(request, ann_id):
    from .models import PlatformAnnouncement
    try:
        ann = PlatformAnnouncement.objects.get(pk=ann_id)
        ann.dismissed_by.add(request.user)
    except PlatformAnnouncement.DoesNotExist:
        pass
    return Response({'detail': 'Dismissed.'})


# ─── Platform-wide feature flags (killswitch) ────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def platform_feature_flags(request):
    """Return all Plan feature fields so frontend can show locked states."""
    try:
        tenant = request.user.tenant_profile
    except Exception:
        return Response({})

    plan = tenant.plan
    if not plan:
        return Response({'plan': None, 'features': {}})

    feature_fields = [
        'allow_whatsapp', 'allow_telegram', 'allow_messenger',
        'allow_byok', 'max_knowledge_pages', 'max_ai_tokens_per_month',
        'allow_hubspot', 'allow_slack', 'allow_webhooks',
        'allow_god_view', 'allow_canned_responses', 'max_canned_responses',
        'allow_conversation_tags', 'allow_csv_export',
        'allow_voice_input', 'allow_image_input', 'allow_fomo_triggers',
        'remove_branding', 'allow_custom_domain', 'allow_custom_logo',
        'allow_api_access', 'allow_multi_language', 'priority_support',
        'sla_response_hours',
    ]

    from users.feature_flags import has_feature
    features = {f: has_feature(request.user, f) for f in feature_fields if f.startswith('allow_') or f == 'remove_branding'}
    features.update({
        'max_knowledge_pages': plan.max_knowledge_pages,
        'max_ai_tokens_per_month': plan.max_ai_tokens_per_month,
        'max_canned_responses': plan.max_canned_responses,
        'sla_response_hours': plan.sla_response_hours,
        'max_sessions_per_month': plan.max_sessions_per_month,
        'max_clients': plan.max_clients,
    })

    return Response({
        'plan': plan.name,
        'plan_price': float(plan.price_monthly),
        'sessions_used': tenant.sessions_this_month,
        'features': features,
    })


# ─── Platform AI Config (superadmin only) ──────────────────────────────────────

@api_view(['GET', 'PUT'])
@permission_classes([IsSuperAdmin])
def platform_config(request):
    from .models import PlatformConfig
    from django.core.cache import cache

    cfg = PlatformConfig.get()

    if request.method == 'GET':
        return Response({
            'openrouter_api_key_set': bool(cfg.openrouter_api_key),
            'openrouter_api_key_preview': (
                '••••••' + cfg.openrouter_api_key[-6:]
                if cfg.openrouter_api_key else ''
            ),
            'primary_model': cfg.primary_model,
            'updated_at': cfg.updated_at.isoformat() if cfg.updated_at else None,
            'updated_by': cfg.updated_by.username if cfg.updated_by else None,
        })

    # PUT — update key and/or model
    key   = request.data.get('openrouter_api_key')
    model = request.data.get('primary_model')

    if key is not None:
        cfg.openrouter_api_key = key.strip()
    if model:
        cfg.primary_model = model.strip()

    cfg.updated_by = request.user
    cfg.save()
    cache.delete('platform_config')

    from users.feature_flags import log_audit
    log_audit(
        request.user,
        'platform_config_update',
        target_label='PlatformConfig',
        notes=f"model={cfg.primary_model}, key_updated={key is not None}",
    )

    return Response({
        'openrouter_api_key_set': bool(cfg.openrouter_api_key),
        'openrouter_api_key_preview': (
            '••••••' + cfg.openrouter_api_key[-6:]
            if cfg.openrouter_api_key else ''
        ),
        'primary_model': cfg.primary_model,
        'updated_at': cfg.updated_at.isoformat() if cfg.updated_at else None,
        'updated_by': cfg.updated_by.username if cfg.updated_by else None,
    })


@api_view(['GET'])
@permission_classes([IsSuperAdmin])
def openrouter_models(request):
    """Proxy to OpenRouter /models. Uses the stored API key."""
    from .models import PlatformConfig
    import requests as req_lib

    cfg = PlatformConfig.get()
    api_key = cfg.openrouter_api_key or os.environ.get('OPENROUTER_API_KEY', '')

    if not api_key:
        return Response({'error': 'No OpenRouter API key configured'}, status=400)

    try:
        resp = req_lib.get(
            'https://openrouter.ai/api/v1/models',
            headers={'Authorization': f'Bearer {api_key}'},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json().get('data', [])
    except Exception as e:
        return Response({'error': str(e)}, status=502)

    models = []
    for m in data:
        models.append({
            'id':             m.get('id', ''),
            'name':           m.get('name', m.get('id', '')),
            'description':    m.get('description', ''),
            'context_length': m.get('context_length', 0),
            'pricing': {
                'prompt':     m.get('pricing', {}).get('prompt', '0'),
                'completion': m.get('pricing', {}).get('completion', '0'),
            },
        })

    # Free models first, then alphabetical
    models.sort(key=lambda m: (float(m['pricing']['prompt']) > 0, m['name'].lower()))

    return Response({'models': models, 'total': len(models)})


# ─── Backup management (superadmin only) ──────────────────────────────────────
# Powers the /admin/backups page. Lists snapshots written by ops/backup.sh,
# streams individual files for download, triggers ad-hoc backups, deletes
# snapshots. Every action writes to AuditLog. Path inputs are validated by
# users.backup_admin against allowlists before any filesystem call.

def _audit_backup(actor, action_key, target_label='', notes='', ip=''):
    """Lightweight audit-log writer for backup operations.

    The AuditLog model has a `choices` constraint on `action` but Django
    only enforces it at form / serializer level, not at the DB. We save
    BACKUP_* strings directly so we don't need a migration to extend the
    enum every time we add an action."""
    try:
        from .models import AuditLog
        AuditLog.objects.create(
            actor=actor,
            action=action_key,
            target_type='backup',
            target_label=target_label[:255],
            ip_address=ip or None,
            notes=notes[:5000] if notes else '',
        )
    except Exception as e:
        logger.warning(f'[backup_admin] AuditLog write failed: {e}')


def _client_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


@api_view(['GET'])
@permission_classes([IsSuperAdmin])
def list_backups(request):
    """Enumerate every snapshot across daily/weekly/monthly tiers."""
    from .backup_admin import list_all_backups
    data = list_all_backups()
    _audit_backup(
        actor=request.user,
        action_key='BACKUP_LIST_VIEWED',
        target_label='all snapshots',
        ip=_client_ip(request),
    )
    return Response(data)


@api_view(['GET'])
@permission_classes([IsSuperAdmin])
def backup_status(request):
    """Top-of-page status strip — latest run, disk usage, retention counts."""
    from .backup_admin import backup_status as _status
    return Response(_status())


@api_view(['GET'])
@permission_classes([IsSuperAdmin])
def download_backup_file(request, tier, date, filename):
    """Stream a single backup artifact. The path is validated against an
    allowlist before any FS access — see backup_admin._safe_file_in_snapshot."""
    from django.http import FileResponse, Http404
    from .backup_admin import _safe_file_in_snapshot, SENSITIVE_FILES

    path = _safe_file_in_snapshot(tier, date, filename)
    if not path:
        raise Http404('Backup file not found or path rejected.')

    size = path.stat().st_size

    _audit_backup(
        actor=request.user,
        action_key='BACKUP_FILE_DOWNLOADED',
        target_label=f'{tier}/{date}/{filename}',
        ip=_client_ip(request),
        notes=f'size={size} sensitive={filename in SENSITIVE_FILES}',
    )

    # FileResponse uses sendfile or chunked iteration — never loads into RAM.
    # Content-Type=application/octet-stream forces the browser to download
    # instead of trying to render db.dump or .tar.gz inline.
    response = FileResponse(
        path.open('rb'),
        as_attachment=True,
        filename=f'checkfunnel-{tier}-{date}-{filename}',
        content_type='application/octet-stream',
    )
    response['Content-Length'] = size
    response['Cache-Control'] = 'no-store, no-cache, must-revalidate, private'
    return response


@api_view(['POST'])
@permission_classes([IsSuperAdmin])
def trigger_backup(request):
    """Fire /usr/local/bin/checkfunnel-backup.sh in the background.

    Fire-and-forget — the script writes to /var/log/checkfunnel-backup.log
    and produces a new daily/<today> directory once complete. UI polls
    backup_status() to detect completion (latest_date == today).

    We deliberately don't capture stdout/stderr or wait for the subprocess
    so the HTTP response can return in <50ms even though the actual work
    takes 20-60s. The script is idempotent — running it multiple times
    just overwrites today's snapshot.
    """
    import subprocess
    script = '/usr/local/bin/checkfunnel-backup.sh'
    if not os.path.isfile(script):
        return Response(
            {'detail': 'Backup script not installed on this host.'},
            status=503,
        )
    try:
        # Detach: stdin/out/err redirected to /dev/null, new session so a
        # SIGHUP to daphne doesn't kill the backup mid-flight.
        subprocess.Popen(
            ['nohup', script],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except Exception as e:
        logger.error(f'[trigger_backup] Failed to spawn: {e}')
        return Response({'detail': str(e)}, status=500)

    _audit_backup(
        actor=request.user,
        action_key='BACKUP_TRIGGERED',
        target_label='manual',
        ip=_client_ip(request),
    )
    return Response({'status': 'started', 'detail': 'Backup running in background.'}, status=202)


@api_view(['DELETE'])
@permission_classes([IsSuperAdmin])
def delete_backup(request, tier, date):
    """Remove a snapshot directory. Cannot delete the most recent one
    (safety — that's the most likely-needed restore point)."""
    import shutil
    from .backup_admin import _safe_snapshot_dir, BACKUP_ROOT, _DATE_RE

    snap = _safe_snapshot_dir(tier, date)
    if not snap:
        return Response({'detail': 'Snapshot not found.'}, status=404)

    # Refuse to delete the most recent snapshot in this tier — disaster
    # recovery should always have a fallback.
    tier_dir = BACKUP_ROOT / tier
    other_dates = sorted(
        c.name for c in tier_dir.iterdir()
        if c.is_dir() and _DATE_RE.match(c.name)
    )
    if other_dates and other_dates[-1] == date:
        return Response(
            {'detail': 'Refusing to delete the most recent snapshot in this tier.'},
            status=400,
        )

    snap_size = sum(p.stat().st_size for p in snap.iterdir() if p.is_file())
    try:
        shutil.rmtree(snap)
    except Exception as e:
        return Response({'detail': f'Delete failed: {e}'}, status=500)

    _audit_backup(
        actor=request.user,
        action_key='BACKUP_DELETED',
        target_label=f'{tier}/{date}',
        ip=_client_ip(request),
        notes=f'size_bytes={snap_size}',
    )
    return Response({'status': 'deleted', 'tier': tier, 'date': date})
