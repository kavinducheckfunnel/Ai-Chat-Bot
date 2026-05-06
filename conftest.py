"""
Root conftest — shared fixtures and factories for the entire test suite.
"""
import uuid
import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from users.models import Plan, Client, UserProfile, TenantProfile
from chat.models import ChatSession


# ─── Helpers ─────────────────────────────────────────────────────────────────

def make_jwt(user):
    """Return a Bearer token string for the given user."""
    return str(RefreshToken.for_user(user).access_token)


def auth_client(user):
    """Return an APIClient pre-authenticated as the given user."""
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {make_jwt(user)}')
    return client


# ─── Plans ───────────────────────────────────────────────────────────────────

@pytest.fixture
def free_plan(db):
    return Plan.objects.create(
        name='Free',
        price_monthly=0,
        max_clients=1,
        max_sessions_per_month=100,
        max_messages_per_month=100,
        max_images_per_month=0,
        max_voice_per_month=0,
        max_knowledge_pages=5,
        max_dashboard_metrics=3,
        data_retention_days=30,
        allow_god_view=True,
        allow_fomo_triggers=True,
        allow_slack=True,
        allow_whatsapp=False,
        allow_telegram=False,
        allow_messenger=False,
        allow_byok=False,
        allow_hubspot=False,
        allow_webhooks=False,
        allow_canned_responses=False,
        allow_conversation_tags=False,
        allow_csv_export=False,
        allow_voice_input=False,
        allow_image_input=False,
        remove_branding=False,
        allow_custom_domain=False,
        allow_api_access=False,
        allow_multi_language=False,
        allow_advanced_reports=False,
        is_public=True,
    )


@pytest.fixture
def growth_plan(db):
    return Plan.objects.create(
        name='Growth',
        price_monthly=49,
        stripe_price_id='price_growth_monthly',
        max_clients=5,
        max_sessions_per_month=2000,
        max_messages_per_month=2000,
        max_images_per_month=100,
        max_voice_per_month=100,
        max_knowledge_pages=100,
        max_dashboard_metrics=7,
        data_retention_days=90,
        allow_god_view=True,
        allow_fomo_triggers=True,
        allow_slack=True,
        allow_whatsapp=True,
        allow_telegram=True,
        allow_messenger=True,
        allow_byok=True,
        allow_hubspot=True,
        allow_webhooks=True,
        allow_canned_responses=True,
        allow_conversation_tags=True,
        allow_csv_export=True,
        allow_voice_input=True,
        allow_image_input=True,
        remove_branding=False,
        allow_custom_domain=False,
        allow_api_access=False,
        allow_multi_language=False,
        allow_advanced_reports=True,
        is_public=True,
    )


# ─── Users ───────────────────────────────────────────────────────────────────

@pytest.fixture
def superadmin_user(db):
    user = User.objects.create_user(
        username='superadmin@test.com',
        email='superadmin@test.com',
        password='SuperPass123!',
    )
    UserProfile.objects.create(user=user, role='superadmin')
    return user


@pytest.fixture
def tenant_user(db, free_plan):
    user = User.objects.create_user(
        username='tenant@test.com',
        email='tenant@test.com',
        password='TenantPass123!',
    )
    UserProfile.objects.create(user=user, role='tenant_admin')
    TenantProfile.objects.create(user=user, company_name='ACME Corp', plan=free_plan)
    return user


@pytest.fixture
def tenant_user2(db, free_plan):
    """A second tenant — used to test cross-tenant access control."""
    user = User.objects.create_user(
        username='tenant2@test.com',
        email='tenant2@test.com',
        password='TenantPass123!',
    )
    UserProfile.objects.create(user=user, role='tenant_admin')
    TenantProfile.objects.create(user=user, company_name='Beta Corp', plan=free_plan)
    return user


# ─── API Clients ─────────────────────────────────────────────────────────────

@pytest.fixture
def anon_client():
    return APIClient()


@pytest.fixture
def superadmin_client(superadmin_user):
    return auth_client(superadmin_user)


@pytest.fixture
def tenant_client(tenant_user):
    return auth_client(tenant_user)


@pytest.fixture
def tenant_client2(tenant_user2):
    return auth_client(tenant_user2)


# ─── Clients (chatbot site instances) ────────────────────────────────────────

@pytest.fixture
def client_obj(db, tenant_user):
    """A Client assigned to tenant_user."""
    c = Client.objects.create(
        name='Test Store',
        domain_url='https://teststore.com',
        platform='CUSTOM',
        chatbot_name='Testy',
        chatbot_color='#FF0000',
    )
    tenant_user.tenant_profile.clients.add(c)
    return c


@pytest.fixture
def client_obj2(db, tenant_user2):
    """A Client assigned to tenant_user2 — used for cross-tenant tests."""
    c = Client.objects.create(
        name='Beta Store',
        domain_url='https://betastore.com',
        platform='CUSTOM',
    )
    tenant_user2.tenant_profile.clients.add(c)
    return c


# ─── Chat Sessions ────────────────────────────────────────────────────────────

@pytest.fixture
def chat_session(db, client_obj):
    return ChatSession.objects.create(
        client=client_obj,
        visitor_id='visitor-abc-123',
        channel='website',
    )


@pytest.fixture
def whatsapp_client(db, tenant_user):
    """Client configured for WhatsApp."""
    c = Client.objects.create(
        name='WA Store',
        platform='CUSTOM',
        whatsapp_phone_number_id='1234567890',
        whatsapp_access_token='wa_token_abc',
        whatsapp_verify_token='my_verify_token',
        whatsapp_enabled=True,
    )
    tenant_user.tenant_profile.clients.add(c)
    return c


@pytest.fixture
def messenger_client(db, tenant_user):
    """Client configured for Messenger."""
    c = Client.objects.create(
        name='Messenger Store',
        platform='CUSTOM',
        messenger_page_id='page_001',
        messenger_page_access_token='msg_token_abc',
        messenger_verify_token='msg_verify_token',
        messenger_enabled=True,
    )
    tenant_user.tenant_profile.clients.add(c)
    return c


@pytest.fixture
def telegram_client(db, tenant_user):
    """Client configured for Telegram."""
    c = Client.objects.create(
        name='Telegram Store',
        platform='CUSTOM',
        telegram_bot_token='tg_token_abc',
        telegram_enabled=True,
    )
    tenant_user.tenant_profile.clients.add(c)
    return c
