"""
Tests for superadmin tenant management endpoints:
  GET         /api/admin/tenants/
  GET/PATCH/DELETE /api/admin/tenants/{id}/
  POST        /api/admin/tenants/{id}/assign-plan/
  POST        /api/admin/tenants/{id}/impersonate/
  GET         /api/admin/tenants/{id}/plan-history/
  GET/POST    /api/admin/tenants/{id}/feature-overrides/
  DELETE      /api/admin/tenants/{id}/feature-overrides/{override_id}/
  GET         /api/admin/stats/
  GET         /api/admin/audit/
"""
import pytest
from users.models import TenantProfile, PlanHistory, TenantFeatureOverride, AuditLog


TENANTS_URL = '/api/admin/tenants/'
STATS_URL = '/api/admin/stats/'
AUDIT_URL = '/api/admin/audit/'


def tenant_detail_url(tenant_id):
    return f'/api/admin/tenants/{tenant_id}/'


def assign_plan_url(tenant_id):
    return f'/api/admin/tenants/{tenant_id}/assign-plan/'


def impersonate_url(tenant_id):
    return f'/api/admin/tenants/{tenant_id}/impersonate/'


def plan_history_url(tenant_id):
    return f'/api/admin/tenants/{tenant_id}/plan-history/'


def overrides_url(tenant_id):
    return f'/api/admin/tenants/{tenant_id}/feature-overrides/'


def override_delete_url(tenant_id, override_id):
    return f'/api/admin/tenants/{tenant_id}/feature-overrides/{override_id}/'


# ─── Tenant List ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestTenantList:
    def test_superadmin_can_list_tenants(self, superadmin_client, tenant_user, tenant_user2):
        resp = superadmin_client.get(TENANTS_URL)
        assert resp.status_code == 200
        data = resp.json()
        user_ids = [t.get('id') or t.get('user_id') for t in data]
        # Both tenants should appear
        assert len(data) >= 2

    def test_tenant_admin_cannot_list_tenants(self, tenant_client):
        resp = tenant_client.get(TENANTS_URL)
        assert resp.status_code == 403

    def test_unauthenticated_cannot_list_tenants(self, anon_client):
        resp = anon_client.get(TENANTS_URL)
        assert resp.status_code == 401


# ─── Tenant Detail ────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestTenantDetail:
    def test_get_tenant(self, superadmin_client, tenant_user):
        tp = tenant_user.tenant_profile
        resp = superadmin_client.get(tenant_detail_url(tp.pk))
        assert resp.status_code == 200

    def test_tenant_admin_blocked(self, tenant_client, tenant_user):
        tp = tenant_user.tenant_profile
        resp = tenant_client.get(tenant_detail_url(tp.pk))
        assert resp.status_code == 403

    def test_delete_tenant(self, superadmin_client, tenant_user):
        user_pk = tenant_user.pk
        tp = tenant_user.tenant_profile
        resp = superadmin_client.delete(tenant_detail_url(tp.pk))
        assert resp.status_code == 204
        from django.contrib.auth.models import User
        assert not User.objects.filter(pk=user_pk).exists()


# ─── Assign Plan ──────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestAssignPlan:
    def test_assign_plan(self, superadmin_client, tenant_user, growth_plan):
        tp = tenant_user.tenant_profile
        resp = superadmin_client.post(assign_plan_url(tp.pk), {
            'plan_id': growth_plan.pk,
        }, format='json')
        assert resp.status_code == 200
        assert resp.json()['plan'] == growth_plan.name
        tp.refresh_from_db()
        assert tp.plan == growth_plan

    def test_assign_invalid_plan(self, superadmin_client, tenant_user):
        tp = tenant_user.tenant_profile
        resp = superadmin_client.post(assign_plan_url(tp.pk), {
            'plan_id': 999999,
        }, format='json')
        assert resp.status_code == 400

    def test_assign_plan_tenant_blocked(self, tenant_client, tenant_user, growth_plan):
        tp = tenant_user.tenant_profile
        resp = tenant_client.post(assign_plan_url(tp.pk), {
            'plan_id': growth_plan.pk,
        }, format='json')
        assert resp.status_code == 403


# ─── Impersonation ────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestImpersonation:
    def test_impersonate_returns_token(self, superadmin_client, tenant_user):
        tp = tenant_user.tenant_profile
        resp = superadmin_client.post(impersonate_url(tp.pk))
        assert resp.status_code == 200
        data = resp.json()
        assert 'access' in data
        assert 'impersonated_by' in data

    def test_impersonate_tenant_cannot_impersonate(self, tenant_client, tenant_user):
        tp = tenant_user.tenant_profile
        resp = tenant_client.post(impersonate_url(tp.pk))
        assert resp.status_code == 403

    def test_impersonate_nonexistent_tenant(self, superadmin_client):
        resp = superadmin_client.post(impersonate_url(999999))
        assert resp.status_code == 404


# ─── Plan History ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestPlanHistory:
    def test_plan_history_list(self, superadmin_client, tenant_user, free_plan, growth_plan, superadmin_user):
        tp = tenant_user.tenant_profile
        PlanHistory.objects.create(
            tenant=tp,
            from_plan=free_plan,
            to_plan=growth_plan,
            changed_by=superadmin_user,
        )
        resp = superadmin_client.get(plan_history_url(tp.pk))
        assert resp.status_code == 200
        assert len(resp.json()) >= 1


# ─── Feature Overrides ────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestFeatureOverrides:
    def test_list_overrides(self, superadmin_client, tenant_user, superadmin_user):
        tp = tenant_user.tenant_profile
        TenantFeatureOverride.objects.create(
            tenant=tp,
            feature_name='allow_whatsapp',
            enabled=True,
            granted_by=superadmin_user,
        )
        resp = superadmin_client.get(overrides_url(tp.pk))
        assert resp.status_code == 200
        names = [o['feature_name'] for o in resp.json()]
        assert 'allow_whatsapp' in names

    def test_create_override(self, superadmin_client, tenant_user):
        tp = tenant_user.tenant_profile
        resp = superadmin_client.post(overrides_url(tp.pk), {
            'feature_name': 'allow_telegram',
            'enabled': True,
            'reason': 'VIP deal',
        }, format='json')
        assert resp.status_code == 200
        assert resp.json()['created'] is True
        assert TenantFeatureOverride.objects.filter(
            tenant=tp, feature_name='allow_telegram'
        ).exists()

    def test_delete_override(self, superadmin_client, tenant_user, superadmin_user):
        tp = tenant_user.tenant_profile
        override = TenantFeatureOverride.objects.create(
            tenant=tp,
            feature_name='allow_byok',
            enabled=True,
            granted_by=superadmin_user,
        )
        resp = superadmin_client.delete(override_delete_url(tp.pk, override.pk))
        assert resp.status_code == 200
        assert not TenantFeatureOverride.objects.filter(pk=override.pk).exists()

    def test_tenant_cannot_manage_overrides(self, tenant_client, tenant_user):
        tp = tenant_user.tenant_profile
        resp = tenant_client.get(overrides_url(tp.pk))
        assert resp.status_code == 403


# ─── Platform Stats ───────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestPlatformStats:
    def test_stats_superadmin(self, superadmin_client):
        resp = superadmin_client.get(STATS_URL)
        assert resp.status_code == 200
        data = resp.json()
        assert 'total_clients' in data
        assert 'active_clients' in data
        assert 'heat_distribution' in data

    def test_stats_tenant_also_accessible(self, tenant_client):
        # /api/admin/stats/ is scoped by tenant (returns their own stats), not blocked.
        resp = tenant_client.get(STATS_URL)
        assert resp.status_code == 200


# ─── Audit Log ───────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestAuditLog:
    def test_audit_list_superadmin(self, superadmin_client, superadmin_user):
        AuditLog.objects.create(
            actor=superadmin_user,
            action='PLAN_CHANGE',
            target_type='tenant',
            target_id='1',
            target_label='ACME Corp',
        )
        resp = superadmin_client.get(AUDIT_URL)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_audit_tenant_blocked(self, tenant_client):
        resp = tenant_client.get(AUDIT_URL)
        assert resp.status_code == 403

    def test_audit_unauthenticated(self, anon_client):
        resp = anon_client.get(AUDIT_URL)
        assert resp.status_code == 401
