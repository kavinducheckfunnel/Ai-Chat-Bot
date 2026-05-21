"""Tests for the super-admin prompt editor:

  POST /api/admin/prompts/reauth/
  GET  /api/admin/prompts/
  GET  /api/admin/prompts/<slug>/
  GET  /api/admin/prompts/<slug>/versions/
  GET  /api/admin/prompts/<slug>/versions/<id>/
  POST /api/admin/prompts/<slug>/preview/
  POST /api/admin/prompts/<slug>/save/
  POST /api/admin/prompts/<slug>/rollback/
  POST /api/admin/prompts/<slug>/reset/

Also covers the prompt_service runtime resolver: cache hit, fail-safe
fallback to the file constant, and that build_prompt picks up DB changes.
"""

import time

import jwt
import pytest
from django.conf import settings

from chat import prompts as prompts_module
from chat import prompt_service
from chat.models import PromptTemplate, PromptVersion


BASE = '/api/admin/prompts'
REAUTH_URL = f'{BASE}/reauth/'


# ─── Helpers ────────────────────────────────────────────────────────────────


def _get_reauth_token(client, password='SuperPass123!'):
    """Walks through /reauth/ and returns the token string."""
    resp = client.post(REAUTH_URL, {'password': password}, format='json')
    assert resp.status_code == 200, resp.data
    return resp.data['reauth_token']


def _seed_templates(db):
    """Migration 0014 seeds system_persona, then 0015 removes the
    state_instructions row. Pytest's transaction rollback can leave us
    with an empty table inside a test class, so re-seed defensively."""
    if PromptTemplate.objects.filter(slug='system_persona').exists():
        return

    persona = PromptTemplate.objects.create(
        slug='system_persona',
        description='Persona block.',
    )
    pv = PromptVersion.objects.create(
        template=persona,
        version=1,
        body=prompts_module.SYSTEM_PERSONA,
        notes='seed',
        is_default=True,
    )
    persona.active_version = pv
    persona.save()


@pytest.fixture
def seeded_templates(db):
    _seed_templates(db)
    # Always start each test with a cold cache so we exercise the DB load path.
    prompt_service.bump_cache()
    yield
    prompt_service.bump_cache()


# ─── Re-auth flow ───────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestReauth:
    def test_correct_password_returns_token(self, superadmin_client, seeded_templates):
        resp = superadmin_client.post(REAUTH_URL, {'password': 'SuperPass123!'}, format='json')
        assert resp.status_code == 200
        assert 'reauth_token' in resp.data
        assert resp.data['expires_in'] == 5 * 60
        # Token is a valid JWT with scope=prompt_write
        payload = jwt.decode(
            resp.data['reauth_token'], settings.SECRET_KEY, algorithms=['HS256']
        )
        assert payload['scope'] == 'prompt_write'

    def test_wrong_password_rejected(self, superadmin_client, seeded_templates):
        resp = superadmin_client.post(REAUTH_URL, {'password': 'wrong'}, format='json')
        assert resp.status_code == 401

    def test_missing_password_rejected(self, superadmin_client, seeded_templates):
        resp = superadmin_client.post(REAUTH_URL, {}, format='json')
        assert resp.status_code == 400

    def test_non_superadmin_rejected(self, tenant_client, seeded_templates):
        resp = tenant_client.post(REAUTH_URL, {'password': 'TenantPass123!'}, format='json')
        assert resp.status_code == 403

    def test_anon_rejected(self, anon_client, seeded_templates):
        resp = anon_client.post(REAUTH_URL, {'password': 'x'}, format='json')
        assert resp.status_code in (401, 403)


# ─── Listing + detail ──────────────────────────────────────────────────────


@pytest.mark.django_db
class TestListAndDetail:
    def test_list_returns_system_persona_only(self, superadmin_client, seeded_templates):
        resp = superadmin_client.get(f'{BASE}/')
        assert resp.status_code == 200
        slugs = {item['slug'] for item in resp.data}
        assert slugs == {'system_persona'}

    def test_detail_returns_active_body(self, superadmin_client, seeded_templates):
        resp = superadmin_client.get(f'{BASE}/system_persona/')
        assert resp.status_code == 200
        assert resp.data['slug'] == 'system_persona'
        assert resp.data['active_body'] == prompts_module.SYSTEM_PERSONA
        assert resp.data['file_default_body'] == prompts_module.SYSTEM_PERSONA

    def test_detail_unknown_slug_404(self, superadmin_client, seeded_templates):
        resp = superadmin_client.get(f'{BASE}/nope/')
        assert resp.status_code == 404

    def test_list_rejects_non_superadmin(self, tenant_client, seeded_templates):
        resp = tenant_client.get(f'{BASE}/')
        assert resp.status_code == 403

    def test_versions_returns_history(self, superadmin_client, seeded_templates):
        resp = superadmin_client.get(f'{BASE}/system_persona/versions/')
        assert resp.status_code == 200
        assert resp.data['count'] == 1
        assert resp.data['results'][0]['is_default'] is True


# ─── Preview / validation ──────────────────────────────────────────────────


@pytest.mark.django_db
class TestPreview:
    def test_preview_persona_ok(self, superadmin_client, seeded_templates):
        resp = superadmin_client.post(
            f'{BASE}/system_persona/preview/',
            {'body': 'You are a helpful sales bot.'},
            format='json',
        )
        assert resp.status_code == 200
        assert resp.data['ok'] is True
        assert resp.data['errors'] == []
        assert resp.data['stats']['characters'] > 0

    def test_preview_persona_empty_rejected(self, superadmin_client, seeded_templates):
        resp = superadmin_client.post(
            f'{BASE}/system_persona/preview/',
            {'body': '   '},
            format='json',
        )
        assert resp.status_code == 200
        assert resp.data['ok'] is False
        assert any('empty' in e.lower() for e in resp.data['errors'])

    def test_preview_persona_unknown_placeholder_rejected(self, superadmin_client, seeded_templates):
        resp = superadmin_client.post(
            f'{BASE}/system_persona/preview/',
            {'body': 'Hello {not_allowed}.'},
            format='json',
        )
        assert resp.status_code == 200
        assert resp.data['ok'] is False
        assert any('Unknown placeholders' in e for e in resp.data['errors'])

# ─── Save flow ──────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestSave:
    def test_save_without_reauth_token_rejected(self, superadmin_client, seeded_templates):
        resp = superadmin_client.post(
            f'{BASE}/system_persona/save/',
            {'body': 'new persona', 'notes': 'test'},
            format='json',
        )
        assert resp.status_code == 403

    def test_save_with_reauth_creates_new_version(self, superadmin_client, seeded_templates):
        token = _get_reauth_token(superadmin_client)
        resp = superadmin_client.post(
            f'{BASE}/system_persona/save/',
            {'body': 'BRAND NEW PERSONA', 'notes': 'first edit'},
            format='json',
            HTTP_X_REAUTH_TOKEN=token,
        )
        assert resp.status_code == 201, resp.data
        assert resp.data['version']['version'] == 2

        template = PromptTemplate.objects.get(slug='system_persona')
        assert template.versions.count() == 2
        assert template.active_version.body == 'BRAND NEW PERSONA'

    def test_save_invalid_body_returns_422(self, superadmin_client, seeded_templates):
        token = _get_reauth_token(superadmin_client)
        resp = superadmin_client.post(
            f'{BASE}/system_persona/save/',
            {'body': 'Bad {unknown_placeholder}', 'notes': ''},
            format='json',
            HTTP_X_REAUTH_TOKEN=token,
        )
        assert resp.status_code == 422
        assert 'errors' in resp.data

    def test_save_with_expired_token_rejected(self, superadmin_client, seeded_templates):
        # Build a token that already expired.
        from users.admin_prompts_views import REAUTH_SCOPE
        expired = jwt.encode(
            {
                'sub': '1', 'scope': REAUTH_SCOPE, 'jti': 'x',
                'ip': '', 'iat': 0, 'exp': int(time.time()) - 10,
            },
            settings.SECRET_KEY, algorithm='HS256',
        )
        resp = superadmin_client.post(
            f'{BASE}/system_persona/save/',
            {'body': 'x', 'notes': ''},
            format='json',
            HTTP_X_REAUTH_TOKEN=expired,
        )
        assert resp.status_code == 403
        assert 'expired' in str(resp.data['detail']).lower()

    def test_save_bumps_runtime_resolver(self, superadmin_client, seeded_templates):
        """After a save, get_system_persona() returns the new body."""
        token = _get_reauth_token(superadmin_client)
        superadmin_client.post(
            f'{BASE}/system_persona/save/',
            {'body': 'RUNTIME UPDATED PERSONA', 'notes': 'live test'},
            format='json',
            HTTP_X_REAUTH_TOKEN=token,
        )
        assert prompt_service.get_system_persona() == 'RUNTIME UPDATED PERSONA'


# ─── Rollback ───────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestRollback:
    def test_rollback_creates_new_version_with_old_body(self, superadmin_client, seeded_templates):
        token = _get_reauth_token(superadmin_client)
        # Save v2
        superadmin_client.post(
            f'{BASE}/system_persona/save/',
            {'body': 'V2 BODY', 'notes': 'v2'}, format='json',
            HTTP_X_REAUTH_TOKEN=token,
        )
        # Save v3
        superadmin_client.post(
            f'{BASE}/system_persona/save/',
            {'body': 'V3 BODY', 'notes': 'v3'}, format='json',
            HTTP_X_REAUTH_TOKEN=token,
        )
        # Roll back to v2
        v2 = PromptVersion.objects.get(template__slug='system_persona', version=2)
        resp = superadmin_client.post(
            f'{BASE}/system_persona/rollback/',
            {'version_id': str(v2.id)}, format='json',
            HTTP_X_REAUTH_TOKEN=token,
        )
        assert resp.status_code == 201
        # New version (v4) is now active with v2's body
        template = PromptTemplate.objects.get(slug='system_persona')
        assert template.active_version.version == 4
        assert template.active_version.body == 'V2 BODY'

    def test_rollback_to_already_active_rejected(self, superadmin_client, seeded_templates):
        token = _get_reauth_token(superadmin_client)
        template = PromptTemplate.objects.get(slug='system_persona')
        active_id = str(template.active_version.id)
        resp = superadmin_client.post(
            f'{BASE}/system_persona/rollback/',
            {'version_id': active_id}, format='json',
            HTTP_X_REAUTH_TOKEN=token,
        )
        assert resp.status_code == 400

    def test_rollback_unknown_version_404(self, superadmin_client, seeded_templates):
        import uuid as _uuid
        token = _get_reauth_token(superadmin_client)
        resp = superadmin_client.post(
            f'{BASE}/system_persona/rollback/',
            {'version_id': str(_uuid.uuid4())}, format='json',
            HTTP_X_REAUTH_TOKEN=token,
        )
        assert resp.status_code == 404


# ─── Reset to factory default ───────────────────────────────────────────────


@pytest.mark.django_db
class TestReset:
    def test_reset_writes_file_default_as_new_version(self, superadmin_client, seeded_templates):
        token = _get_reauth_token(superadmin_client)
        # Save a custom v2 first.
        superadmin_client.post(
            f'{BASE}/system_persona/save/',
            {'body': 'CUSTOM', 'notes': ''}, format='json',
            HTTP_X_REAUTH_TOKEN=token,
        )
        # Now reset.
        resp = superadmin_client.post(
            f'{BASE}/system_persona/reset/', {}, format='json',
            HTTP_X_REAUTH_TOKEN=token,
        )
        assert resp.status_code == 201
        template = PromptTemplate.objects.get(slug='system_persona')
        assert template.active_version.body == prompts_module.SYSTEM_PERSONA


# ─── Runtime resolver ──────────────────────────────────────────────────────


@pytest.mark.django_db
class TestRuntimeResolver:
    def test_resolves_seed_to_file_constant(self, seeded_templates):
        prompt_service.bump_cache()
        assert prompt_service.get_system_persona() == prompts_module.SYSTEM_PERSONA

    def test_falls_back_to_file_when_no_template(self, db):
        """With an empty DB, the resolver returns the file constant. The
        chatbot must keep working even before migrations seed the template."""
        PromptTemplate.objects.all().delete()
        prompt_service.bump_cache()
        assert prompt_service.get_system_persona() == prompts_module.SYSTEM_PERSONA

    def test_picks_up_db_change_after_invalidate(self, seeded_templates):
        template = PromptTemplate.objects.get(slug='system_persona')
        new_v = PromptVersion.objects.create(
            template=template, version=2, body='UPDATED', notes='', is_default=False,
        )
        template.active_version = new_v
        template.save()

        prompt_service.bump_cache('system_persona')
        assert prompt_service.get_system_persona() == 'UPDATED'
