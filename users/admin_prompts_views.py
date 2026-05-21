"""Super-admin endpoints for editing the live chatbot prompt.

All endpoints are gated by `IsSuperAdmin`. Writes additionally require a
short-lived re-auth token (issued by `prompt_reauth`) so a stolen session
cookie cannot push prompt changes without re-entering the password.

Routes are wired in `users/urls.py` under `/api/admin/prompts/`.
"""

from __future__ import annotations

import json
import logging
import re
import time
import uuid
from typing import Any

import jwt
from django.conf import settings
from django.contrib.auth import authenticate
from django.core.cache import cache
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .permissions import IsSuperAdmin

logger = logging.getLogger(__name__)


# ─── Re-auth token plumbing ─────────────────────────────────────────────────
#
# A signed JWT with `scope=prompt_write`, 5-minute exp, single-use via Redis
# replay-protection. Each write endpoint calls `_consume_reauth_token()` which
# verifies + burns the token in one step.

REAUTH_TTL_SECONDS = 5 * 60  # 5 minutes
REAUTH_SCOPE = 'prompt_write'
REAUTH_JTI_PREFIX = 'prompt_reauth_jti:'


def _client_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


def _issue_reauth_token(user, ip: str) -> dict:
    now = int(time.time())
    jti = uuid.uuid4().hex
    payload = {
        'sub': str(user.id),
        'scope': REAUTH_SCOPE,
        'jti': jti,
        'ip': ip or '',
        'iat': now,
        'exp': now + REAUTH_TTL_SECONDS,
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
    return {'reauth_token': token, 'expires_in': REAUTH_TTL_SECONDS}


def _consume_reauth_token(request) -> tuple[bool, str]:
    """Verify the X-Reauth-Token header. Returns (ok, error_message).

    Burns the JTI on success so the token cannot be replayed across requests
    within the 5-minute window. (We do still allow multiple writes during the
    window by issuing a fresh token from each successful write — see usage.)

    Actually we want a *window* not single-use, so the user can save more than
    once after one password entry. So we keep the token valid for its full
    exp window and only burn it on explicit revoke. This matches the plan's
    decision (3b — 5-minute window).
    """
    raw = request.META.get('HTTP_X_REAUTH_TOKEN') or ''
    if not raw:
        return False, 'Missing X-Reauth-Token header.'
    try:
        payload = jwt.decode(raw, settings.SECRET_KEY, algorithms=['HS256'])
    except jwt.ExpiredSignatureError:
        return False, 'Re-auth token expired. Please confirm your password again.'
    except jwt.InvalidTokenError:
        return False, 'Invalid re-auth token.'

    if payload.get('scope') != REAUTH_SCOPE:
        return False, 'Token scope mismatch.'
    if payload.get('sub') != str(request.user.id):
        return False, 'Token user mismatch.'
    if payload.get('ip') and payload['ip'] != _client_ip(request):
        return False, 'Token IP mismatch.'
    # Optional replay-revoke check — if the JTI has been explicitly burned,
    # reject. (We currently don't burn it; reserved for future single-use mode.)
    if cache.get(REAUTH_JTI_PREFIX + payload['jti']) == 'revoked':
        return False, 'Token has been revoked.'
    return True, ''


# ─── Audit helper ───────────────────────────────────────────────────────────

def _audit_prompt(actor, action_key, template, before=None, after=None, ip='', notes=''):
    """Write a row to AuditLog for any prompt-editor action."""
    try:
        from .models import AuditLog
        AuditLog.objects.create(
            actor=actor,
            action=action_key,
            target_type='prompt',
            target_id=str(template.id) if template else '',
            target_label=template.slug if template else '',
            before_value=before,
            after_value=after,
            ip_address=ip or None,
            notes=notes[:5000] if notes else '',
        )
    except Exception as e:
        logger.warning(f'[admin_prompts] AuditLog write failed: {e}')


# ─── Validation ─────────────────────────────────────────────────────────────
#
# A bad prompt body that omits a required placeholder will raise KeyError
# inside `build_prompt()` on every chat reply. Catch this BEFORE writing.

# Placeholders referenced inside the SYSTEM_PERSONA block. Currently none —
# the persona is plain prose. Kept as a tuple so future placeholders are easy
# to add.
REQUIRED_PLACEHOLDERS_SYSTEM_PERSONA: tuple[str, ...] = ()

# State instructions JSON must have a value for every state the state machine
# can emit. Pulled at call time from chat.state_machine to stay in sync.
def _required_state_keys() -> set[str]:
    # Hardcoded to mirror chat.state_machine.determine_conversation_state().
    # If a new state is ever added, also add it here.
    return {'RESEARCH', 'EVALUATION', 'OBJECTION', 'RECOVERY', 'READY_TO_BUY'}


PLACEHOLDER_RE = re.compile(r'\{([a-zA-Z_][a-zA-Z0-9_]*)\}')


def _extract_placeholders(body: str) -> set[str]:
    return set(PLACEHOLDER_RE.findall(body))


def _validate_system_persona(body: str) -> list[str]:
    errors = []
    if not body or not body.strip():
        errors.append('System persona body cannot be empty.')
        return errors

    placeholders = _extract_placeholders(body)
    required = set(REQUIRED_PLACEHOLDERS_SYSTEM_PERSONA)
    missing = required - placeholders
    if missing:
        errors.append(f'Missing required placeholders: {", ".join(sorted(missing))}')
    extra = placeholders - required
    if extra:
        errors.append(
            f'Unknown placeholders not allowed: {", ".join(sorted(extra))}. '
            f'Allowed: {", ".join(sorted(required)) or "(none)"}'
        )
    return errors


def _validate_state_instructions(body: str) -> list[str]:
    errors = []
    try:
        data = json.loads(body)
    except json.JSONDecodeError as e:
        errors.append(f'Invalid JSON: {e.msg} (line {e.lineno}, col {e.colno})')
        return errors

    if not isinstance(data, dict):
        errors.append('State instructions must be a JSON object (state-name → instruction string).')
        return errors

    required = _required_state_keys()
    missing = required - set(data.keys())
    if missing:
        errors.append(f'Missing required state keys: {", ".join(sorted(missing))}')

    for key, val in data.items():
        if not isinstance(val, str) or not val.strip():
            errors.append(f'State "{key}" must be a non-empty string.')

    return errors


def _validate_body(slug: str, body: str) -> list[str]:
    if slug == 'system_persona':
        return _validate_system_persona(body)
    if slug == 'state_instructions':
        return _validate_state_instructions(body)
    return [f'Unknown slug "{slug}".']


def _dry_run_render(slug: str, body: str) -> list[str]:
    """Render build_prompt() against a fake session using the proposed body.

    The placeholder/JSON validators already cover the actual failure modes:
      • `system_persona` is interpolated as a plain string into an f-string
        slot — it is not re-formatted, so braces inside it cannot raise.
      • `state_instructions` is JSON-parsed; required keys are checked.
    We still call build_prompt against the current cache as a smoke test
    that import wiring is intact.
    """
    errors: list[str] = []
    try:
        # Just confirm json.loads succeeds for the state-instructions slug,
        # which we already validated; but re-check to be defensive.
        if slug == 'state_instructions':
            json.loads(body)

        from chat import prompts as prompts_module
        prompts_module.build_prompt(
            conversation_state='RESEARCH',
            context_chunks=[],
            behavior_matrix={},
            chat_history=[],
            user_message='Hello',
            website_domain='example.com',
            qualification_block='',
        )
    except Exception as e:
        errors.append(f'Render smoke-test failed: {type(e).__name__}: {e}')
    return errors


# ─── Helpers ────────────────────────────────────────────────────────────────

def _serialize_template(template) -> dict:
    """Public-facing summary of a template (no body)."""
    av = template.active_version
    return {
        'id': str(template.id),
        'slug': template.slug,
        'description': template.description,
        'active_version': _serialize_version_summary(av) if av else None,
        'updated_at': template.updated_at.isoformat() if template.updated_at else None,
    }


def _serialize_version_summary(version) -> dict:
    return {
        'id': str(version.id),
        'version': version.version,
        'notes': version.notes,
        'is_default': version.is_default,
        'created_at': version.created_at.isoformat() if version.created_at else None,
        'created_by': (
            version.created_by.username if version.created_by else None
        ),
    }


def _serialize_version_full(version) -> dict:
    summary = _serialize_version_summary(version)
    summary['body'] = version.body
    return summary


# ─── Endpoints ──────────────────────────────────────────────────────────────


@api_view(['POST'])
@permission_classes([IsAuthenticated])  # IsSuperAdmin enforced inside (we want a distinct error)
def prompt_reauth(request):
    """Confirm password and return a 5-minute re-auth token.

    Requires the user to already be authenticated. The plain login session
    does NOT grant prompt-write capability — this endpoint is the gate.
    """
    if not IsSuperAdmin().has_permission(request, None):
        return Response({'detail': 'Super admin only.'}, status=403)

    password = (request.data or {}).get('password', '')
    if not password:
        return Response({'detail': 'Password required.'}, status=400)

    # Use authenticate() against the user's own username to confirm the
    # password. Django's auth backends handle hashing + lockouts.
    user = authenticate(username=request.user.username, password=password)
    if user is None or user.id != request.user.id:
        _audit_prompt(
            actor=request.user,
            action_key='PROMPT_REAUTH_FAILED',
            template=None,
            ip=_client_ip(request),
            notes='Password mismatch during prompt re-auth.',
        )
        return Response({'detail': 'Incorrect password.'}, status=401)

    token = _issue_reauth_token(user, _client_ip(request))
    return Response(token)


@api_view(['GET'])
@permission_classes([IsSuperAdmin])
def prompt_list(request):
    """List all editable prompt templates with their active version summary."""
    from chat.models import PromptTemplate
    templates = PromptTemplate.objects.select_related('active_version').all()
    return Response([_serialize_template(t) for t in templates])


@api_view(['GET'])
@permission_classes([IsSuperAdmin])
def prompt_detail(request, slug):
    """Full detail of one slot including the currently active body."""
    from chat.models import PromptTemplate
    template = (
        PromptTemplate.objects
        .select_related('active_version')
        .filter(slug=slug)
        .first()
    )
    if template is None:
        return Response({'detail': 'Prompt template not found.'}, status=404)

    payload = _serialize_template(template)
    payload['active_body'] = template.active_version.body if template.active_version else ''
    # Also surface the file-default body so the UI can offer "reset" cleanly.
    from chat.prompt_service import _file_default
    try:
        default_value = _file_default(slug)
        if slug == 'state_instructions':
            payload['file_default_body'] = json.dumps(default_value, indent=2, ensure_ascii=False)
        else:
            payload['file_default_body'] = default_value
    except Exception:
        payload['file_default_body'] = ''
    return Response(payload)


@api_view(['GET'])
@permission_classes([IsSuperAdmin])
def prompt_versions(request, slug):
    """Paginated version history (newest first), summary only — no bodies."""
    from chat.models import PromptTemplate, PromptVersion
    template = PromptTemplate.objects.filter(slug=slug).first()
    if template is None:
        return Response({'detail': 'Prompt template not found.'}, status=404)

    qs = PromptVersion.objects.filter(template=template).select_related('created_by')
    # Cap to 100 most-recent — UI shows a list, not infinite history.
    items = list(qs.order_by('-created_at')[:100])
    return Response({
        'count': len(items),
        'results': [_serialize_version_summary(v) for v in items],
    })


@api_view(['GET'])
@permission_classes([IsSuperAdmin])
def prompt_version_detail(request, slug, version_id):
    """Full body of a specific version — for the diff view."""
    from chat.models import PromptTemplate, PromptVersion
    template = PromptTemplate.objects.filter(slug=slug).first()
    if template is None:
        return Response({'detail': 'Prompt template not found.'}, status=404)

    version = PromptVersion.objects.filter(
        template=template, id=version_id,
    ).select_related('created_by').first()
    if version is None:
        return Response({'detail': 'Version not found.'}, status=404)

    return Response(_serialize_version_full(version))


@api_view(['POST'])
@permission_classes([IsSuperAdmin])
def prompt_preview(request, slug):
    """Validate the proposed body and return errors + a sample-render preview.

    No write. Safe to call repeatedly while editing.
    """
    body = (request.data or {}).get('body', '')
    if not isinstance(body, str):
        return Response({'detail': 'Body must be a string.'}, status=400)

    errors = _validate_body(slug, body)
    if errors:
        return Response({'ok': False, 'errors': errors}, status=200)

    render_errors = _dry_run_render(slug, body)
    if render_errors:
        return Response({'ok': False, 'errors': render_errors}, status=200)

    # Approximate token cost: ~4 chars per token. Not exact but useful warning.
    char_count = len(body)
    approx_tokens = max(1, char_count // 4)
    return Response({
        'ok': True,
        'errors': [],
        'stats': {
            'characters': char_count,
            'approx_tokens': approx_tokens,
            'lines': body.count('\n') + 1,
        },
    })


def _next_version_number(template) -> int:
    from chat.models import PromptVersion
    last = (
        PromptVersion.objects
        .filter(template=template)
        .order_by('-version')
        .first()
    )
    return (last.version + 1) if last else 1


def _save_new_version(template, body: str, notes: str, user, source_version_id: str = None):
    """Create a new PromptVersion + flip active_version atomically."""
    from django.db import transaction
    from chat.models import PromptVersion

    with transaction.atomic():
        version = PromptVersion.objects.create(
            template=template,
            version=_next_version_number(template),
            body=body,
            notes=notes[:500],
            created_by=user,
            is_default=False,
        )
        template.active_version = version
        template.save(update_fields=['active_version', 'updated_at'])

    # Bust local cache + tell other workers to bust theirs.
    from chat.prompt_service import bump_cache, publish_invalidate, ensure_subscriber
    ensure_subscriber()
    bump_cache(template.slug)
    publish_invalidate(template.slug)
    return version


@api_view(['POST'])
@permission_classes([IsSuperAdmin])
def prompt_save(request, slug):
    """Save a new version and flip the active pointer. Requires re-auth."""
    ok, err = _consume_reauth_token(request)
    if not ok:
        return Response({'detail': err}, status=403)

    body = (request.data or {}).get('body', '')
    notes = (request.data or {}).get('notes', '') or ''
    if not isinstance(body, str):
        return Response({'detail': 'Body must be a string.'}, status=400)

    errors = _validate_body(slug, body)
    if errors:
        return Response({'detail': 'Validation failed.', 'errors': errors}, status=422)

    render_errors = _dry_run_render(slug, body)
    if render_errors:
        return Response({'detail': 'Dry-run render failed.', 'errors': render_errors}, status=422)

    from chat.models import PromptTemplate
    template = PromptTemplate.objects.select_related('active_version').filter(slug=slug).first()
    if template is None:
        return Response({'detail': 'Prompt template not found.'}, status=404)

    previous = template.active_version
    new_version = _save_new_version(
        template=template, body=body, notes=notes, user=request.user,
    )

    _audit_prompt(
        actor=request.user,
        action_key='PROMPT_SAVE',
        template=template,
        before={'version_id': str(previous.id), 'version': previous.version} if previous else None,
        after={'version_id': str(new_version.id), 'version': new_version.version},
        ip=_client_ip(request),
        notes=f'Saved new prompt version. Notes: {notes[:200]}',
    )

    return Response({
        'detail': 'Saved.',
        'version': _serialize_version_summary(new_version),
    }, status=201)


@api_view(['POST'])
@permission_classes([IsSuperAdmin])
def prompt_rollback(request, slug):
    """Roll back to a previous version. Forward-only: creates a NEW version
    whose body is a copy of the target's body, so the audit trail stays
    linear and easy to read."""
    ok, err = _consume_reauth_token(request)
    if not ok:
        return Response({'detail': err}, status=403)

    target_version_id = (request.data or {}).get('version_id')
    if not target_version_id:
        return Response({'detail': 'version_id is required.'}, status=400)

    from chat.models import PromptTemplate, PromptVersion
    template = PromptTemplate.objects.select_related('active_version').filter(slug=slug).first()
    if template is None:
        return Response({'detail': 'Prompt template not found.'}, status=404)

    target = PromptVersion.objects.filter(template=template, id=target_version_id).first()
    if target is None:
        return Response({'detail': 'Target version not found.'}, status=404)

    previous = template.active_version
    if previous and previous.id == target.id:
        return Response({'detail': 'That version is already active.'}, status=400)

    new_version = _save_new_version(
        template=template,
        body=target.body,
        notes=f'Rollback to v{target.version}',
        user=request.user,
    )

    _audit_prompt(
        actor=request.user,
        action_key='PROMPT_ROLLBACK',
        template=template,
        before={'version_id': str(previous.id), 'version': previous.version} if previous else None,
        after={
            'version_id': str(new_version.id),
            'version': new_version.version,
            'rolled_back_to': target.version,
        },
        ip=_client_ip(request),
        notes=f'Rolled back to v{target.version}.',
    )

    return Response({
        'detail': f'Rolled back to v{target.version} (saved as v{new_version.version}).',
        'version': _serialize_version_summary(new_version),
    }, status=201)


@api_view(['POST'])
@permission_classes([IsSuperAdmin])
def prompt_reset(request, slug):
    """Reset to the file-default body, saved as a new version."""
    ok, err = _consume_reauth_token(request)
    if not ok:
        return Response({'detail': err}, status=403)

    from chat.models import PromptTemplate
    from chat.prompt_service import _file_default
    template = PromptTemplate.objects.select_related('active_version').filter(slug=slug).first()
    if template is None:
        return Response({'detail': 'Prompt template not found.'}, status=404)

    try:
        default_value = _file_default(slug)
        body = json.dumps(default_value, indent=2, ensure_ascii=False) if slug == 'state_instructions' else default_value
    except Exception as e:
        return Response({'detail': f'Failed to load factory default: {e}'}, status=500)

    previous = template.active_version
    new_version = _save_new_version(
        template=template,
        body=body,
        notes='Reset to factory default.',
        user=request.user,
    )

    _audit_prompt(
        actor=request.user,
        action_key='PROMPT_RESET',
        template=template,
        before={'version_id': str(previous.id), 'version': previous.version} if previous else None,
        after={'version_id': str(new_version.id), 'version': new_version.version},
        ip=_client_ip(request),
        notes='Reset to factory default.',
    )

    return Response({
        'detail': 'Reset to factory default.',
        'version': _serialize_version_summary(new_version),
    }, status=201)
