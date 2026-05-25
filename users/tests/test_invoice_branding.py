"""
Tests for invoice branding: snapshot of the tenant's first-client
chatbot_logo_url + chatbot_color onto the Invoice at issue time, and
safe rendering of those values in the HTML template.
"""
import pytest

from users.invoice_service import (
    _safe_brand_color,
    _lighten_hex,
    _DEFAULT_BRAND_COLOR,
    _primary_client,
    generate_invoice,
    render_invoice_html,
)
from users.models import Client, Invoice


# ─── _safe_brand_color ───────────────────────────────────────────────────────

class TestSafeBrandColor:
    def test_valid_six_digit_hex_passes_through(self):
        assert _safe_brand_color('#ff0000') == '#ff0000'

    def test_valid_three_digit_hex_passes_through(self):
        assert _safe_brand_color('#f00') == '#f00'

    def test_valid_eight_digit_hex_with_alpha_passes(self):
        assert _safe_brand_color('#ff0000aa') == '#ff0000aa'

    def test_invalid_hex_returns_default(self):
        assert _safe_brand_color('not a color') == _DEFAULT_BRAND_COLOR
        assert _safe_brand_color('#xyz') == _DEFAULT_BRAND_COLOR
        assert _safe_brand_color('red') == _DEFAULT_BRAND_COLOR

    def test_blank_returns_default(self):
        assert _safe_brand_color('') == _DEFAULT_BRAND_COLOR
        assert _safe_brand_color(None) == _DEFAULT_BRAND_COLOR
        assert _safe_brand_color('   ') == _DEFAULT_BRAND_COLOR

    def test_no_injection_via_css(self):
        # Anything with quotes / semicolons / parens must NOT pass.
        evil = '#abc"; background:url(evil);//'
        assert _safe_brand_color(evil) == _DEFAULT_BRAND_COLOR


# ─── _lighten_hex ────────────────────────────────────────────────────────────

class TestLightenHex:
    def test_lighten_returns_six_digit_hex(self):
        out = _lighten_hex('#3b82f6', 0.20)
        assert out.startswith('#')
        assert len(out) == 7

    def test_lighten_with_short_hex_expands(self):
        out = _lighten_hex('#f00', 0.20)
        assert len(out) == 7

    def test_lighten_invalid_falls_back_to_default(self):
        out = _lighten_hex('nope', 0.20)
        assert out.startswith('#')
        assert len(out) == 7

    def test_amount_zero_returns_close_to_original(self):
        # Lightening by 0 should leave the colour numerically unchanged.
        assert _lighten_hex('#3b82f6', 0.0).lower() == '#3b82f6'

    def test_amount_one_returns_white(self):
        assert _lighten_hex('#3b82f6', 1.0).lower() == '#ffffff'


# ─── _primary_client ─────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestPrimaryClient:
    def test_no_clients_returns_none(self, tenant_user):
        assert _primary_client(tenant_user.tenant_profile) is None

    def test_picks_first_client_by_id(self, tenant_user, client_obj):
        # client_obj is already attached to tenant_user via fixture.
        result = _primary_client(tenant_user.tenant_profile)
        assert result is not None
        assert result.id == client_obj.id


# ─── generate_invoice branding snapshot ─────────────────────────────────────

@pytest.mark.django_db
class TestInvoiceBrandingSnapshot:
    def test_captures_logo_and_color_from_primary_client(self, tenant_user, client_obj):
        client_obj.chatbot_logo_url = 'https://cdn.example.com/logo.png'
        client_obj.chatbot_color = '#22c55e'
        client_obj.save()

        invoice = generate_invoice(tenant_user.tenant_profile, 2026, 5)
        assert invoice.brand_logo_url_at_issue == 'https://cdn.example.com/logo.png'
        assert invoice.brand_color_at_issue == '#22c55e'

    def test_branding_blank_when_no_client(self, tenant_user):
        invoice = generate_invoice(tenant_user.tenant_profile, 2026, 5)
        assert invoice.brand_logo_url_at_issue == ''
        assert invoice.brand_color_at_issue == ''

    def test_branding_is_frozen_after_issue(self, tenant_user, client_obj):
        client_obj.chatbot_logo_url = 'https://cdn.example.com/old.png'
        client_obj.chatbot_color = '#aabbcc'
        client_obj.save()

        invoice = generate_invoice(tenant_user.tenant_profile, 2026, 5)

        # Customer changes their brand later — historical invoice MUST NOT shift.
        client_obj.chatbot_logo_url = 'https://cdn.example.com/new.png'
        client_obj.chatbot_color = '#000000'
        client_obj.save()

        invoice.refresh_from_db()
        assert invoice.brand_logo_url_at_issue == 'https://cdn.example.com/old.png'
        assert invoice.brand_color_at_issue == '#aabbcc'

    def test_regenerate_with_force_refreshes_branding(self, tenant_user, client_obj):
        client_obj.chatbot_logo_url = 'https://cdn.example.com/v1.png'
        client_obj.chatbot_color = '#111111'
        client_obj.save()
        generate_invoice(tenant_user.tenant_profile, 2026, 5)

        client_obj.chatbot_logo_url = 'https://cdn.example.com/v2.png'
        client_obj.chatbot_color = '#222222'
        client_obj.save()
        invoice = generate_invoice(tenant_user.tenant_profile, 2026, 5, force=True)

        assert invoice.brand_logo_url_at_issue == 'https://cdn.example.com/v2.png'
        assert invoice.brand_color_at_issue == '#222222'


# ─── render_invoice_html branding render ────────────────────────────────────

@pytest.mark.django_db
class TestRenderInvoiceHtmlBranding:
    def test_logo_appears_when_present(self, tenant_user, client_obj):
        client_obj.chatbot_logo_url = 'https://cdn.example.com/logo.png'
        client_obj.chatbot_color = '#22c55e'
        client_obj.save()
        invoice = generate_invoice(tenant_user.tenant_profile, 2026, 5)

        html = render_invoice_html(invoice)
        assert 'https://cdn.example.com/logo.png' in html
        assert '#22c55e' in html  # used in the header gradient
        # Tenant name appears next to the logo
        assert invoice.company_name_at_issue in html

    def test_logo_omitted_when_missing(self, tenant_user, client_obj):
        client_obj.chatbot_logo_url = ''
        client_obj.chatbot_color = '#22c55e'
        client_obj.save()
        invoice = generate_invoice(tenant_user.tenant_profile, 2026, 5)

        html = render_invoice_html(invoice)
        assert '<img' not in html or 'cdn.example.com' not in html

    def test_invalid_color_falls_back_to_default_in_html(self, tenant_user, client_obj):
        # The DB stores whatever the tenant typed, but the rendered CSS
        # gradient must NEVER contain an unsanitised colour value.
        invoice = generate_invoice(tenant_user.tenant_profile, 2026, 5)
        invoice.brand_color_at_issue = 'not a color'
        invoice.save()

        html = render_invoice_html(invoice)
        assert _DEFAULT_BRAND_COLOR in html
        assert 'not a color' not in html

    def test_default_color_when_no_branding(self, tenant_user):
        # Tenant with no client at all.
        invoice = generate_invoice(tenant_user.tenant_profile, 2026, 5)
        html = render_invoice_html(invoice)
        assert _DEFAULT_BRAND_COLOR in html
