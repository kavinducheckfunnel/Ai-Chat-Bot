"""
Tests for the Phase-B invoice work:
  • view_invoice_pdf endpoint (signed-token auth + PDF response)
  • list_invoices includes both download_url and pdf_url
  • render_invoice_email — short shell template renders required CTAs
  • email_invoice attaches the PDF and uses the shell HTML
  • _conversations_dashboard_url shape (deep-link the email uses)
  • PortalInbox API path accepts date_from / date_to filters

WeasyPrint is heavy and depends on system libs (Cairo/Pango). We mock
`render_invoice_pdf` everywhere so the suite stays portable.
"""
from datetime import date
from unittest.mock import patch

import pytest
from django.core import mail
from django.urls import reverse

from users.invoice_service import (
    render_invoice_email,
    generate_invoice,
    email_invoice,
)
from users.billing_views import (
    _invoice_signer,
    _invoice_signed_url,
    _invoice_signed_pdf_url,
    _conversations_dashboard_url,
    _public_origin,
)


def _pdf_url(invoice_id, token=None):
    base = f'/api/admin/billing/invoices/{invoice_id}/pdf/'
    return f'{base}?token={token}' if token else base


# ─── _conversations_dashboard_url ────────────────────────────────────────────

class TestConversationsDashboardUrl:
    def test_basic_shape(self):
        url = _conversations_dashboard_url(date(2026, 5, 1), date(2026, 5, 31))
        assert url.startswith('/portal/inbox?')
        assert 'from=2026-05-01' in url
        assert 'to=2026-05-31' in url

    def test_includes_client_id_when_provided(self):
        url = _conversations_dashboard_url(date(2026, 5, 1), date(2026, 5, 31), client_id='abc')
        assert 'client=abc' in url


# ─── render_invoice_email ────────────────────────────────────────────────────

@pytest.mark.django_db
class TestRenderInvoiceEmail:
    def test_renders_three_ctas(self, tenant_user, client_obj):
        client_obj.chatbot_color = '#22c55e'
        client_obj.save()
        invoice = generate_invoice(tenant_user.tenant_profile, 2026, 5)

        html = render_invoice_email(
            invoice,
            pdf_url='https://example.com/pdf',
            view_html_url='https://example.com/view',
            conversations_url='https://example.com/inbox?from=2026-05-01&to=2026-05-31',
        )
        # All three CTA hrefs land in the rendered HTML. Django's
        # auto-escape turns `&` into `&amp;` inside attribute values —
        # which is correct HTML, so check both segments separately.
        assert 'https://example.com/pdf' in html
        assert 'https://example.com/view' in html
        assert 'https://example.com/inbox?from=2026-05-01' in html
        assert 'to=2026-05-31' in html
        # CTA button labels are present
        assert 'Download PDF' in html
        assert 'View Online' in html
        assert 'Conversations' in html
        # Brand colour rendered into the gradient
        assert '#22c55e' in html
        # Invoice number + total present in the hero card
        assert invoice.invoice_number in html
        assert str(invoice.total_usd) in html

    def test_buttons_hidden_when_url_missing(self, tenant_user):
        invoice = generate_invoice(tenant_user.tenant_profile, 2026, 5)
        html = render_invoice_email(invoice)  # no URLs
        # Buttons are conditionally rendered; their labels shouldn't show
        # up when their href is empty.
        assert 'Download PDF' not in html
        assert 'View Online' not in html

    def test_no_full_chat_history_in_email(self, tenant_user):
        invoice = generate_invoice(tenant_user.tenant_profile, 2026, 5)
        invoice.usage_summary = {
            'sessions_total': 5,
            'leads': 2,
            'hot_leads': 1,
            'converted': 1,
            'ai_messages': 40,
        }
        invoice.save()
        html = render_invoice_email(
            invoice, conversations_url='https://example.com/inbox',
        )
        # Quick-stats are aggregated; raw chat lines never appear.
        assert 'visitor:' not in html.lower()
        assert 'role: user' not in html.lower()


# ─── view_invoice_pdf endpoint ───────────────────────────────────────────────

@pytest.mark.django_db
class TestViewInvoicePdfEndpoint:
    def test_signed_token_returns_pdf(self, anon_client, tenant_user):
        invoice = generate_invoice(tenant_user.tenant_profile, 2026, 5)
        token = _invoice_signer().sign(str(invoice.id))
        with patch('users.invoice_service.render_invoice_pdf', return_value=b'%PDF-fake'):
            resp = anon_client.get(_pdf_url(invoice.id, token=token))
        assert resp.status_code == 200
        assert resp['Content-Type'] == 'application/pdf'
        assert b'%PDF-fake' in resp.content
        # Filename includes the invoice number for the download dialog
        assert invoice.invoice_number in resp['Content-Disposition']
        assert 'attachment' in resp['Content-Disposition']

    def test_invalid_token_rejected(self, anon_client, tenant_user):
        invoice = generate_invoice(tenant_user.tenant_profile, 2026, 5)
        resp = anon_client.get(_pdf_url(invoice.id, token='garbage'))
        assert resp.status_code == 403

    def test_no_token_no_auth_rejected(self, anon_client, tenant_user):
        invoice = generate_invoice(tenant_user.tenant_profile, 2026, 5)
        resp = anon_client.get(_pdf_url(invoice.id))
        assert resp.status_code == 401

    def test_jwt_owner_can_download(self, tenant_client, tenant_user):
        invoice = generate_invoice(tenant_user.tenant_profile, 2026, 5)
        with patch('users.invoice_service.render_invoice_pdf', return_value=b'%PDF-fake'):
            resp = tenant_client.get(_pdf_url(invoice.id))
        assert resp.status_code == 200

    def test_other_tenant_blocked(self, tenant_client2, tenant_user):
        invoice = generate_invoice(tenant_user.tenant_profile, 2026, 5)
        resp = tenant_client2.get(_pdf_url(invoice.id))
        assert resp.status_code == 403

    def test_pdf_generation_failure_returns_503(self, anon_client, tenant_user):
        invoice = generate_invoice(tenant_user.tenant_profile, 2026, 5)
        token = _invoice_signer().sign(str(invoice.id))
        with patch(
            'users.invoice_service.render_invoice_pdf',
            side_effect=RuntimeError('libpango missing'),
        ):
            resp = anon_client.get(_pdf_url(invoice.id, token=token))
        assert resp.status_code == 503


# ─── list_invoices returns pdf_url ───────────────────────────────────────────

@pytest.mark.django_db
class TestListInvoicesIncludesPdfUrl:
    def test_each_invoice_has_pdf_url(self, tenant_client, tenant_user):
        generate_invoice(tenant_user.tenant_profile, 2026, 5)
        resp = tenant_client.get('/api/admin/billing/invoices/')
        assert resp.status_code == 200
        body = resp.json()
        assert body, 'expected at least one invoice'
        for row in body:
            assert 'pdf_url' in row
            assert 'download_url' in row
            assert '/pdf/' in row['pdf_url']
            assert '/html/' in row['download_url']


# ─── email_invoice attaches PDF + uses shell ─────────────────────────────────

@pytest.mark.django_db
class TestEmailInvoiceShellAndPdf:
    def test_pdf_attached_and_shell_used(self, tenant_user):
        invoice = generate_invoice(tenant_user.tenant_profile, 2026, 5)
        invoice.recipient_email_at_issue = 'kavindu@example.com'
        invoice.save()

        with patch('users.invoice_service.render_invoice_pdf', return_value=b'%PDF-attach'):
            ok = email_invoice(
                invoice,
                pdf_url='https://example.com/pdf',
                view_html_url='https://example.com/view',
                conversations_url='https://example.com/inbox',
            )
        assert ok is True
        # One outbound email was sent
        assert len(mail.outbox) == 1
        sent = mail.outbox[0]
        # Subject is the new format
        assert invoice.invoice_number in sent.subject
        # The HTML alternative includes the email-shell-only marker
        html_part = sent.alternatives[0][0]
        assert 'Download PDF' in html_part
        assert 'Conversations' in html_part
        # PDF is attached as a real file
        attachments = sent.attachments
        assert any(
            a[0].endswith('.pdf') and a[2] == 'application/pdf' for a in attachments
        ), f'No PDF attachment found in {attachments!r}'

    def test_email_still_sends_when_pdf_fails(self, tenant_user):
        """If WeasyPrint is misconfigured, the customer still gets the email."""
        invoice = generate_invoice(tenant_user.tenant_profile, 2026, 5)
        invoice.recipient_email_at_issue = 'kavindu@example.com'
        invoice.save()

        with patch(
            'users.invoice_service.render_invoice_pdf',
            side_effect=RuntimeError('no libpango'),
        ):
            ok = email_invoice(
                invoice,
                pdf_url='https://example.com/pdf',
                view_html_url='https://example.com/view',
            )
        assert ok is True
        assert len(mail.outbox) == 1
        # No PDF attached but shell HTML is still present
        sent = mail.outbox[0]
        html_part = sent.alternatives[0][0]
        assert 'View Online' in html_part
        assert not any(a[0].endswith('.pdf') for a in sent.attachments)


# ─── PortalInbox API: date_from / date_to filters ────────────────────────────

@pytest.mark.django_db
class TestSessionsDateFilter:
    def test_date_from_to_supported(self, tenant_client, client_obj):
        """The backend endpoint that PortalInbox calls must accept the
        query params our deep-link uses."""
        resp = tenant_client.get(
            f'/api/admin/clients/{client_obj.id}/sessions/'
            f'?date_from=2026-05-01&date_to=2026-05-31&limit=50'
        )
        assert resp.status_code == 200
