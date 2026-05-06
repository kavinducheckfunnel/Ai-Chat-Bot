"""
Tests for authentication endpoints:
  POST /api/admin/auth/register/
  POST /api/admin/auth/login/
  POST /api/admin/auth/refresh/
  GET  /api/admin/auth/me/
  POST /api/admin/auth/forgot-password/
  POST /api/admin/auth/reset-password/
  POST /api/admin/auth/change-password/
"""
import pytest
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from users.models import UserProfile, TenantProfile


REGISTER_URL = '/api/admin/auth/register/'
LOGIN_URL = '/api/admin/auth/login/'
REFRESH_URL = '/api/admin/auth/refresh/'
ME_URL = '/api/admin/auth/me/'
FORGOT_URL = '/api/admin/auth/forgot-password/'
RESET_URL = '/api/admin/auth/reset-password/'
CHANGE_URL = '/api/admin/auth/change-password/'


# ─── Registration ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestRegister:
    def test_register_valid(self):
        client = APIClient()
        resp = client.post(REGISTER_URL, {
            'company_name': 'Test Corp',
            'email': 'new@example.com',
            'password': 'SecurePass1!',
            'confirm_password': 'SecurePass1!',
        }, format='json')
        assert resp.status_code == 201
        data = resp.json()
        assert 'access' in data
        assert 'refresh' in data
        assert data['user']['role'] == 'tenant_admin'
        # Verify DB objects were created
        user = User.objects.get(email='new@example.com')
        assert user.profile.role == 'tenant_admin'
        assert TenantProfile.objects.filter(user=user).exists()

    def test_register_duplicate_email(self, tenant_user):
        client = APIClient()
        resp = client.post(REGISTER_URL, {
            'company_name': 'Another Corp',
            'email': tenant_user.email,
            'password': 'SecurePass1!',
            'confirm_password': 'SecurePass1!',
        }, format='json')
        assert resp.status_code == 400
        assert 'already exists' in resp.json().get('detail', '').lower()

    def test_register_missing_company_name(self):
        client = APIClient()
        resp = client.post(REGISTER_URL, {
            'email': 'new2@example.com',
            'password': 'SecurePass1!',
            'confirm_password': 'SecurePass1!',
        }, format='json')
        assert resp.status_code == 400

    def test_register_short_password(self):
        client = APIClient()
        resp = client.post(REGISTER_URL, {
            'company_name': 'Test Corp',
            'email': 'short@example.com',
            'password': 'abc',
            'confirm_password': 'abc',
        }, format='json')
        assert resp.status_code == 400
        assert '8 characters' in resp.json().get('detail', '').lower()

    def test_register_password_mismatch(self):
        client = APIClient()
        resp = client.post(REGISTER_URL, {
            'company_name': 'Test Corp',
            'email': 'mismatch@example.com',
            'password': 'SecurePass1!',
            'confirm_password': 'DifferentPass1!',
        }, format='json')
        assert resp.status_code == 400
        assert 'match' in resp.json().get('detail', '').lower()

    def test_register_missing_email(self):
        client = APIClient()
        resp = client.post(REGISTER_URL, {
            'company_name': 'Test Corp',
            'password': 'SecurePass1!',
            'confirm_password': 'SecurePass1!',
        }, format='json')
        assert resp.status_code == 400


# ─── Login ────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestLogin:
    def test_login_valid(self, tenant_user):
        client = APIClient()
        resp = client.post(LOGIN_URL, {
            'username': tenant_user.email,
            'password': 'TenantPass123!',
        }, format='json')
        assert resp.status_code == 200
        data = resp.json()
        assert 'access' in data
        assert 'refresh' in data
        assert data['user']['role'] == 'tenant_admin'

    def test_login_superadmin(self, superadmin_user):
        client = APIClient()
        resp = client.post(LOGIN_URL, {
            'username': superadmin_user.email,
            'password': 'SuperPass123!',
        }, format='json')
        assert resp.status_code == 200
        assert resp.json()['user']['role'] == 'superadmin'

    def test_login_wrong_password(self, tenant_user):
        client = APIClient()
        resp = client.post(LOGIN_URL, {
            'username': tenant_user.email,
            'password': 'WrongPassword!',
        }, format='json')
        assert resp.status_code == 401

    def test_login_unknown_user(self):
        client = APIClient()
        resp = client.post(LOGIN_URL, {
            'username': 'ghost@example.com',
            'password': 'SomePass123!',
        }, format='json')
        assert resp.status_code == 401

    def test_login_missing_fields(self):
        client = APIClient()
        resp = client.post(LOGIN_URL, {}, format='json')
        assert resp.status_code == 400


# ─── JWT Refresh ──────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestJWTRefresh:
    def test_refresh_valid(self, tenant_user):
        client = APIClient()
        refresh = str(RefreshToken.for_user(tenant_user))
        resp = client.post(REFRESH_URL, {'refresh': refresh}, format='json')
        assert resp.status_code == 200
        assert 'access' in resp.json()

    def test_refresh_invalid_token(self):
        client = APIClient()
        resp = client.post(REFRESH_URL, {'refresh': 'not.a.valid.token'}, format='json')
        assert resp.status_code == 401


# ─── Me ───────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestMe:
    def test_me_authenticated(self, tenant_client, tenant_user):
        resp = tenant_client.get(ME_URL)
        assert resp.status_code == 200
        data = resp.json()
        assert data['email'] == tenant_user.email
        assert data['role'] == 'tenant_admin'
        assert 'quota' in data

    def test_me_superadmin(self, superadmin_client, superadmin_user):
        resp = superadmin_client.get(ME_URL)
        assert resp.status_code == 200
        assert resp.json()['role'] == 'superadmin'

    def test_me_unauthenticated(self, anon_client):
        resp = anon_client.get(ME_URL)
        assert resp.status_code == 401


# ─── Forgot Password ──────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestForgotPassword:
    def test_forgot_known_email(self, tenant_user):
        from django.core import mail
        client = APIClient()
        resp = client.post(FORGOT_URL, {'email': tenant_user.email}, format='json')
        assert resp.status_code == 200
        assert 'reset link' in resp.json()['detail'].lower()
        # Email should be queued
        assert len(mail.outbox) == 1
        assert tenant_user.email in mail.outbox[0].to

    def test_forgot_unknown_email(self):
        """Security: must return 200 even for unknown emails (no account enumeration)."""
        from django.core import mail
        client = APIClient()
        resp = client.post(FORGOT_URL, {'email': 'nobody@example.com'}, format='json')
        assert resp.status_code == 200
        assert len(mail.outbox) == 0


# ─── Reset Password ───────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestResetPassword:
    def _make_token(self, user):
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        return uid, token

    def test_reset_valid(self, tenant_user):
        uid, token = self._make_token(tenant_user)
        client = APIClient()
        resp = client.post(RESET_URL, {
            'uid': uid,
            'token': token,
            'new_password': 'NewSecure456!',
        }, format='json')
        assert resp.status_code == 200
        # Verify new password works
        tenant_user.refresh_from_db()
        assert tenant_user.check_password('NewSecure456!')

    def test_reset_invalid_token(self, tenant_user):
        uid = urlsafe_base64_encode(force_bytes(tenant_user.pk))
        client = APIClient()
        resp = client.post(RESET_URL, {
            'uid': uid,
            'token': 'bad-token',
            'new_password': 'NewSecure456!',
        }, format='json')
        assert resp.status_code == 400

    def test_reset_short_password(self, tenant_user):
        uid, token = self._make_token(tenant_user)
        client = APIClient()
        resp = client.post(RESET_URL, {
            'uid': uid,
            'token': token,
            'new_password': 'abc',
        }, format='json')
        assert resp.status_code == 400

    def test_reset_invalid_uid(self):
        client = APIClient()
        resp = client.post(RESET_URL, {
            'uid': 'notavaliduid',
            'token': 'sometoken',
            'new_password': 'NewSecure456!',
        }, format='json')
        assert resp.status_code == 400


# ─── Change Password ──────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestChangePassword:
    def test_change_valid(self, tenant_client, tenant_user):
        resp = tenant_client.post(CHANGE_URL, {
            'current_password': 'TenantPass123!',
            'new_password': 'ChangedPass456!',
        }, format='json')
        assert resp.status_code == 200
        tenant_user.refresh_from_db()
        assert tenant_user.check_password('ChangedPass456!')

    def test_change_wrong_current(self, tenant_client):
        resp = tenant_client.post(CHANGE_URL, {
            'current_password': 'WrongCurrent!',
            'new_password': 'NewPass456!',
        }, format='json')
        assert resp.status_code == 400

    def test_change_short_new_password(self, tenant_client):
        resp = tenant_client.post(CHANGE_URL, {
            'current_password': 'TenantPass123!',
            'new_password': 'abc',
        }, format='json')
        assert resp.status_code == 400

    def test_change_unauthenticated(self, anon_client):
        resp = anon_client.post(CHANGE_URL, {
            'current_password': 'TenantPass123!',
            'new_password': 'NewPass456!',
        }, format='json')
        assert resp.status_code == 401
