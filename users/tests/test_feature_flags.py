"""
Tests for feature_flags module:
  - has_feature() — plan gating, trial access, overrides
  - check_message_quota() / check_image_quota() / check_voice_quota()
  - check_session_quota() / check_client_quota()
  - gate_feature() response shape
  - gate_quota() response shape
"""
import pytest
from datetime import timedelta
from django.utils import timezone

from users.feature_flags import (
    has_feature, gate_feature, gate_quota,
    check_message_quota, check_image_quota,
    check_voice_quota, check_session_quota,
    check_client_quota, usage_summary,
)
from users.models import TenantFeatureOverride


# ─── has_feature ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestHasFeature:
    def test_superadmin_has_all_features(self, superadmin_user):
        assert has_feature(superadmin_user, 'allow_whatsapp') is True
        assert has_feature(superadmin_user, 'remove_branding') is True
        assert has_feature(superadmin_user, 'allow_api_access') is True

    def test_free_plan_lacks_whatsapp(self, tenant_user, free_plan):
        assert has_feature(tenant_user, 'allow_whatsapp') is False

    def test_growth_plan_has_whatsapp(self, tenant_user, growth_plan):
        tenant_user.tenant_profile.plan = growth_plan
        tenant_user.tenant_profile.save()
        assert has_feature(tenant_user, 'allow_whatsapp') is True

    def test_free_plan_lacks_byok(self, tenant_user):
        assert has_feature(tenant_user, 'allow_byok') is False

    def test_free_plan_has_god_view(self, tenant_user):
        assert has_feature(tenant_user, 'allow_god_view') is True

    def test_free_plan_has_fomo(self, tenant_user):
        assert has_feature(tenant_user, 'allow_fomo_triggers') is True

    def test_active_trial_grants_non_pro_features(self, tenant_user, free_plan):
        tp = tenant_user.tenant_profile
        tp.trial_ends_at = timezone.now() + timedelta(days=14)
        tp.save()
        assert has_feature(tenant_user, 'allow_whatsapp') is True
        assert has_feature(tenant_user, 'allow_byok') is True

    def test_active_trial_does_not_grant_pro_features(self, tenant_user, free_plan):
        tp = tenant_user.tenant_profile
        tp.trial_ends_at = timezone.now() + timedelta(days=14)
        tp.save()
        assert has_feature(tenant_user, 'remove_branding') is False
        assert has_feature(tenant_user, 'allow_custom_domain') is False

    def test_expired_trial_reverts_to_plan(self, tenant_user, free_plan):
        tp = tenant_user.tenant_profile
        tp.trial_ends_at = timezone.now() - timedelta(days=1)
        tp.save()
        assert has_feature(tenant_user, 'allow_whatsapp') is False

    def test_feature_override_grants_access(self, tenant_user, free_plan, superadmin_user):
        TenantFeatureOverride.objects.create(
            tenant=tenant_user.tenant_profile,
            feature_name='allow_whatsapp',
            enabled=True,
            granted_by=superadmin_user,
        )
        assert has_feature(tenant_user, 'allow_whatsapp') is True

    def test_expired_override_falls_back_to_plan(self, tenant_user, free_plan, superadmin_user):
        TenantFeatureOverride.objects.create(
            tenant=tenant_user.tenant_profile,
            feature_name='allow_whatsapp',
            enabled=True,
            granted_by=superadmin_user,
            expires_at=timezone.now() - timedelta(hours=1),
        )
        assert has_feature(tenant_user, 'allow_whatsapp') is False

    def test_no_plan_returns_false(self, tenant_user):
        tenant_user.tenant_profile.plan = None
        tenant_user.tenant_profile.save()
        assert has_feature(tenant_user, 'allow_whatsapp') is False


# ─── Quota checks ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestQuotaChecks:
    def test_message_quota_within_limit(self, tenant_user, free_plan):
        tp = tenant_user.tenant_profile
        tp.messages_this_month = 50
        tp.save()
        assert check_message_quota(tenant_user) is True

    def test_message_quota_at_limit(self, tenant_user, free_plan):
        tp = tenant_user.tenant_profile
        tp.messages_this_month = free_plan.max_messages_per_month
        tp.save()
        assert check_message_quota(tenant_user) is False

    def test_message_quota_with_addon(self, tenant_user, free_plan):
        tp = tenant_user.tenant_profile
        tp.messages_this_month = free_plan.max_messages_per_month
        tp.addon_messages = 50
        tp.save()
        assert check_message_quota(tenant_user) is True

    def test_message_quota_unlimited(self, tenant_user, free_plan):
        free_plan.max_messages_per_month = -1
        free_plan.save()
        tp = tenant_user.tenant_profile
        tp.messages_this_month = 999999
        tp.save()
        assert check_message_quota(tenant_user) is True

    def test_image_quota_at_limit(self, tenant_user, free_plan):
        tp = tenant_user.tenant_profile
        tp.images_this_month = 0  # max_images = 0 on free_plan
        tp.save()
        assert check_image_quota(tenant_user) is False

    def test_voice_quota_at_limit(self, tenant_user, free_plan):
        tp = tenant_user.tenant_profile
        tp.voice_this_month = 0  # max_voice = 0 on free_plan
        tp.save()
        assert check_voice_quota(tenant_user) is False

    def test_session_quota_within_limit(self, tenant_user, free_plan):
        tp = tenant_user.tenant_profile
        tp.sessions_this_month = 50
        tp.save()
        assert check_session_quota(tenant_user) is True

    def test_session_quota_at_limit(self, tenant_user, free_plan):
        tp = tenant_user.tenant_profile
        tp.sessions_this_month = free_plan.max_sessions_per_month
        tp.save()
        assert check_session_quota(tenant_user) is False

    def test_client_quota_within_limit(self, tenant_user, free_plan):
        # free_plan allows 1 client and no clients are added
        assert check_client_quota(tenant_user) is True

    def test_client_quota_at_limit(self, tenant_user, free_plan, client_obj):
        # client_obj is already assigned; max_clients=1 so quota is full
        assert check_client_quota(tenant_user) is False

    def test_no_tenant_returns_true(self, superadmin_user):
        # Superadmin has no TenantProfile → no limit enforced
        assert check_message_quota(superadmin_user) is True


# ─── gate_feature / gate_quota ────────────────────────────────────────────────

@pytest.mark.django_db
class TestGateFunctions:
    def test_gate_feature_returns_402(self):
        resp = gate_feature('allow_whatsapp')
        assert resp.status_code == 402
        data = resp.data
        assert data['error'] == 'feature_not_available'
        assert data['feature'] == 'allow_whatsapp'
        assert 'upgrade_url' in data

    def test_gate_quota_returns_402(self):
        resp = gate_quota('messages', 100)
        assert resp.status_code == 402
        data = resp.data
        assert data['error'] == 'quota_exceeded'
        assert data['resource'] == 'messages'
        assert data['limit'] == 100


# ─── usage_summary ────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestUsageSummary:
    def test_summary_structure(self, tenant_user, free_plan):
        summary = usage_summary(tenant_user)
        assert 'messages' in summary
        assert 'sessions' in summary
        assert 'used' in summary['messages']
        assert 'limit' in summary['messages']

    def test_summary_no_plan(self, tenant_user):
        tenant_user.tenant_profile.plan = None
        tenant_user.tenant_profile.save()
        summary = usage_summary(tenant_user)
        assert summary == {}
