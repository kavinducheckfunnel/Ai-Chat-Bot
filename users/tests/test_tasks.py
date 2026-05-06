"""
Tests for Celery tasks:
  users.tasks.reset_monthly_sessions
  users.tasks.send_monthly_lead_reports
  chat.tasks.trigger_fomo_for_hot_sessions
  chat.tasks.check_afk_sessions
  chat.tasks.send_hot_lead_alert
  chat.tasks.send_daily_digest
"""
import pytest
from datetime import timedelta
from django.utils import timezone
from unittest.mock import patch

from users.models import TenantProfile
from chat.models import ChatSession


# ─── reset_monthly_sessions ───────────────────────────────────────────────────

@pytest.mark.django_db
class TestResetMonthlySessions:
    def test_resets_all_counters(self, tenant_user, tenant_user2):
        TenantProfile.objects.filter(user=tenant_user).update(
            sessions_this_month=250,
            messages_this_month=500,
        )
        TenantProfile.objects.filter(user=tenant_user2).update(
            sessions_this_month=999,
            messages_this_month=1000,
        )

        from users.tasks import reset_monthly_sessions
        reset_monthly_sessions()

        tenant_user.tenant_profile.refresh_from_db()
        tenant_user2.tenant_profile.refresh_from_db()
        assert tenant_user.tenant_profile.sessions_this_month == 0
        assert tenant_user2.tenant_profile.sessions_this_month == 0


# ─── send_monthly_lead_reports ────────────────────────────────────────────────

@pytest.mark.django_db
class TestSendMonthlyLeadReports:
    def test_sends_email_when_leads_exist(self, tenant_user, client_obj):
        from django.core import mail
        session = ChatSession.objects.create(
            client=client_obj,
            visitor_id='lead-report-visitor',
            kanban_state='HOT_LEAD',
            heat_score=80.0,
            lead_email='lead@example.com',
            created_at=timezone.now() - timedelta(days=10),
        )
        # Manually adjust created_at into the right window
        ChatSession.objects.filter(session_id=session.session_id).update(
            created_at=timezone.now() - timedelta(days=10)
        )

        from users.tasks import send_monthly_lead_reports
        send_monthly_lead_reports()

        assert len(mail.outbox) >= 1
        emails_to = [e.to[0] for e in mail.outbox]
        assert tenant_user.email in emails_to

    def test_skips_tenant_with_no_clients(self, tenant_user2):
        from django.core import mail
        from users.tasks import send_monthly_lead_reports
        send_monthly_lead_reports()
        emails_to = [e.to[0] for e in mail.outbox]
        assert tenant_user2.email not in emails_to


# ─── trigger_fomo_for_hot_sessions ────────────────────────────────────────────

@pytest.mark.django_db
class TestTriggerFomoForHotSessions:
    @patch('asgiref.sync.async_to_sync')
    def test_fires_fomo_for_hot_session(self, mock_async, client_obj, chat_session):
        client_obj.fomo_offer_text = 'Special deal!'
        client_obj.discount_code = 'HOT20'
        client_obj.save()

        ChatSession.objects.filter(session_id=chat_session.session_id).update(
            heat_score=80.0,
            closing_triggered=False,
        )

        from chat.tasks import trigger_fomo_for_hot_sessions
        trigger_fomo_for_hot_sessions()

        chat_session.refresh_from_db()
        assert chat_session.closing_triggered is True
        history = chat_session.chat_history
        assert any(m.get('source') == 'fomo' for m in history)

    def test_does_not_fire_for_already_triggered(self, client_obj, chat_session):
        ChatSession.objects.filter(session_id=chat_session.session_id).update(
            heat_score=90.0,
            closing_triggered=True,
        )

        from chat.tasks import trigger_fomo_for_hot_sessions
        trigger_fomo_for_hot_sessions()

        chat_session.refresh_from_db()
        # No new FOMO entries added
        fomo_entries = [m for m in chat_session.chat_history if m.get('source') == 'fomo']
        assert len(fomo_entries) == 0

    def test_does_not_fire_when_no_offer_text(self, client_obj, chat_session):
        client_obj.fomo_offer_text = None
        client_obj.discount_code = None
        client_obj.save()

        ChatSession.objects.filter(session_id=chat_session.session_id).update(
            heat_score=80.0,
            closing_triggered=False,
        )

        from chat.tasks import trigger_fomo_for_hot_sessions
        trigger_fomo_for_hot_sessions()

        chat_session.refresh_from_db()
        assert chat_session.closing_triggered is False


# ─── check_afk_sessions ───────────────────────────────────────────────────────

@pytest.mark.django_db
class TestCheckAfkSessions:
    @patch('asgiref.sync.async_to_sync')
    def test_nudge_sent_to_idle_session(self, mock_async, chat_session):
        ChatSession.objects.filter(session_id=chat_session.session_id).update(
            last_visitor_message_at=timezone.now() - timedelta(minutes=5),
            message_count=3,
            nudge_count=0,
            takeover_active=False,
        )

        from chat.tasks import check_afk_sessions
        check_afk_sessions()

        chat_session.refresh_from_db()
        assert chat_session.nudge_count == 1
        assert chat_session.last_nudge_at is not None
        nudge_msgs = [m for m in chat_session.chat_history if m.get('source') == 'afk_nudge']
        assert len(nudge_msgs) == 1

    @patch('asgiref.sync.async_to_sync')
    def test_max_3_nudges_respected(self, mock_async, chat_session):
        ChatSession.objects.filter(session_id=chat_session.session_id).update(
            last_visitor_message_at=timezone.now() - timedelta(minutes=5),
            message_count=3,
            nudge_count=3,  # already at max
            takeover_active=False,
        )

        from chat.tasks import check_afk_sessions
        check_afk_sessions()

        chat_session.refresh_from_db()
        assert chat_session.nudge_count == 3  # unchanged

    @patch('asgiref.sync.async_to_sync')
    def test_active_session_not_nudged(self, mock_async, chat_session):
        ChatSession.objects.filter(session_id=chat_session.session_id).update(
            last_visitor_message_at=timezone.now(),  # just now
            message_count=3,
            nudge_count=0,
        )

        from chat.tasks import check_afk_sessions
        check_afk_sessions()

        chat_session.refresh_from_db()
        assert chat_session.nudge_count == 0

    @patch('asgiref.sync.async_to_sync')
    def test_takeover_session_not_nudged(self, mock_async, chat_session):
        ChatSession.objects.filter(session_id=chat_session.session_id).update(
            last_visitor_message_at=timezone.now() - timedelta(minutes=5),
            message_count=3,
            nudge_count=0,
            takeover_active=True,
        )

        from chat.tasks import check_afk_sessions
        check_afk_sessions()

        chat_session.refresh_from_db()
        assert chat_session.nudge_count == 0


# ─── send_hot_lead_alert ──────────────────────────────────────────────────────

@pytest.mark.django_db
class TestSendHotLeadAlert:
    def test_sends_email_to_notification_email(self, client_obj, chat_session):
        from django.core import mail
        client_obj.notification_email = 'alerts@store.com'
        client_obj.save()

        ChatSession.objects.filter(session_id=chat_session.session_id).update(
            heat_score=82.0,
            hot_lead_email_sent=False,
            lead_email='buyer@example.com',
        )

        from chat.tasks import send_hot_lead_alert
        send_hot_lead_alert(str(chat_session.session_id))

        assert len(mail.outbox) == 1
        assert 'alerts@store.com' in mail.outbox[0].to
        assert 'Hot Lead' in mail.outbox[0].subject

        chat_session.refresh_from_db()
        assert chat_session.hot_lead_email_sent is True

    def test_does_not_resend_if_already_sent(self, chat_session):
        from django.core import mail
        ChatSession.objects.filter(session_id=chat_session.session_id).update(
            hot_lead_email_sent=True
        )

        from chat.tasks import send_hot_lead_alert
        send_hot_lead_alert(str(chat_session.session_id))

        assert len(mail.outbox) == 0


# ─── send_daily_digest ────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestSendDailyDigest:
    def test_sends_digest_when_sessions_today(self, tenant_user, client_obj, chat_session):
        from django.core import mail
        tenant_user.email = 'tenant@test.com'
        tenant_user.save()

        from chat.tasks import send_daily_digest
        send_daily_digest()

        emails_to = [e.to[0] for e in mail.outbox]
        assert tenant_user.email in emails_to
        assert any('Daily Digest' in e.subject for e in mail.outbox)

    def test_skips_tenant_with_no_activity(self, tenant_user2):
        from django.core import mail
        from chat.tasks import send_daily_digest
        send_daily_digest()

        emails_to = [e.to[0] for e in mail.outbox]
        assert tenant_user2.email not in emails_to
