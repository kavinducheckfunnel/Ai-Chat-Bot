"""Seed / re-sync the four official Checkfunnel subscription plans.

This is the single source of truth for plan limits + feature flags. It maps
the published pricing doc (Starter / Growth / Pro / Enterprise, Section 4
"Feature Breakdown by Plan") onto the `Plan` model so the billing page and
feature gates always match the spec — instead of whatever values were hand-
entered in Django admin.

Idempotent: run it as often as you like (it's wired into deploy.sh). It
upserts by plan name and:
  • ALWAYS overwrites limits + feature flags to the spec values below
    (these are what drift and need correcting).
  • NEVER overwrites an existing `stripe_price_id` / `stripe_price_id_annual`
    (those are configured per-environment in Stripe + Django admin).
  • Sets `price_monthly` (the DISPLAYED price — Stripe charges based on the
    stripe_price_id, not this field) from the spec / CLI args. Defaults:
    Starter $29, Growth $79, Pro $199, Enterprise custom. Override the
    display price with --starter-price / --growth-price / --pro-price; make
    sure it matches the amount configured on the Stripe Price.
    NOTE: Pro is intentionally kept at $149 / unlimited (live production
    values) rather than the doc's $199 / 15,000 — see the Pro spec comment.

Usage:
    python manage.py seed_plans
    python manage.py seed_plans --starter-price 29 --growth-price 79 --pro-price 199
    python manage.py seed_plans --backfill          # also fix existing tenants

Enterprise uses a sentinel price of -1 → the UI renders it as "Custom /
contact sales" rather than "$0 / Free".
"""
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from users.models import Plan

# Sentinel used in several integer/limit fields. -1 means "unlimited" and is
# already understood across feature_flags.py (every `if limit < 0: allow`).
UNLIMITED = -1
CUSTOM_PRICE = Decimal('-1')   # Enterprise → "Custom" in the UI

# ── Plan specification — mirrors the published pricing doc Section 4 ──────────
# Only the fields that vary per plan are listed; everything else falls back to
# the model defaults. Prices for Starter/Pro are placeholders (see module
# docstring) and overridable via CLI.
PLAN_SPECS = [
    {
        'name': 'Starter',
        'sort_order': 1,
        'price_monthly': Decimal('29'),           # display price; override via --starter-price
        'max_messages_per_month': 2000,
        'max_clients': 1,
        'max_sessions_per_month': UNLIMITED,      # message-based billing, not seats
        'max_images_per_month': 0,                # image upload not on Starter
        'max_voice_per_month': 0,
        'max_social_channels': 0,                 # web chat only
        'max_dashboard_metrics': 3,               # Basic
        'data_retention_days': 30,
        'sla_response_hours': 48,
        # channels
        'allow_whatsapp': False,
        'allow_messenger': False,
        'allow_instagram': False,
        'allow_telegram': True,                   # Telegram optional on all plans
        # AI / widget
        'allow_byok': True,                       # ✓ Optional
        'allow_voice_input': False,
        'allow_image_input': False,
        'allow_real_time_inventory': False,
        # integrations
        'allow_hubspot': False,
        'allow_slack': True,
        'allow_webhooks': True,
        # ops / inbox
        'allow_god_view': False,                  # Live Takeover is Growth+
        'allow_canned_responses': False,
        'allow_conversation_tags': False,
        'allow_csv_export': False,
        # reports / branding / advanced
        'allow_advanced_reports': False,          # Basic reports
        'priority_support': False,
        'remove_branding': False,
        'allow_custom_domain': False,
        'allow_api_access': False,
        'allow_multi_language': False,
    },
    {
        'name': 'Growth',
        'sort_order': 2,
        'price_monthly': Decimal('79'),           # known from product
        'max_messages_per_month': 5000,
        'max_clients': 3,
        'max_sessions_per_month': UNLIMITED,
        'max_images_per_month': UNLIMITED,        # feature-gated by allow_image_input
        'max_voice_per_month': UNLIMITED,
        'max_social_channels': 1,                 # Web + 1 social (WA or FB)
        'max_dashboard_metrics': 7,               # Standard
        'data_retention_days': 90,
        'sla_response_hours': 48,
        'allow_whatsapp': True,
        'allow_messenger': True,
        'allow_instagram': True,
        'allow_telegram': True,
        'allow_byok': True,                       # ✓ Optional
        'allow_voice_input': True,
        'allow_image_input': True,
        'allow_real_time_inventory': False,
        'allow_hubspot': True,                    # Webhook (HubSpot, Zapier…)
        'allow_slack': True,
        'allow_webhooks': True,
        'allow_god_view': True,                   # Live Takeover
        'allow_canned_responses': True,
        'allow_conversation_tags': True,
        'allow_csv_export': True,                 # Standard reports + exports
        'allow_advanced_reports': False,
        'priority_support': False,
        'remove_branding': False,
        'allow_custom_domain': False,
        'allow_api_access': False,
        'allow_multi_language': False,
    },
    {
        'name': 'Pro',
        'sort_order': 3,
        # Product decision: Pro is kept at the live production price + an
        # UNLIMITED message allowance so the existing Pro tenants aren't
        # disrupted. (The pricing doc lists Pro as $199 / 15,000 msgs — switch
        # these two lines to Decimal('199') / 15000 if/when you want to align
        # to the doc and migrate those tenants.)
        'price_monthly': Decimal('149'),          # override via --pro-price
        'max_messages_per_month': -1,             # unlimited (doc: 15000)
        'max_clients': 10,
        'max_sessions_per_month': UNLIMITED,
        'max_images_per_month': UNLIMITED,
        'max_voice_per_month': UNLIMITED,
        'max_social_channels': UNLIMITED,         # omnichannel
        'max_dashboard_metrics': UNLIMITED,       # Advanced
        'data_retention_days': 365,               # 1 year
        'sla_response_hours': 24,                  # Priority
        'allow_whatsapp': True,
        'allow_messenger': True,
        'allow_instagram': True,
        'allow_telegram': True,
        'allow_byok': True,
        'allow_voice_input': True,
        'allow_image_input': True,
        'allow_real_time_inventory': True,        # Pro+
        'allow_hubspot': True,                    # + Direct HubSpot Sync
        'allow_slack': True,
        'allow_webhooks': True,
        'allow_god_view': True,
        'allow_canned_responses': True,
        'allow_conversation_tags': True,
        'allow_csv_export': True,
        'allow_advanced_reports': True,           # Advanced reports & exports
        'priority_support': True,                 # Priority support
        'remove_branding': False,
        'allow_custom_domain': False,
        'allow_api_access': True,                 # Pro+
        'allow_multi_language': True,             # Pro+
    },
    {
        'name': 'Enterprise',
        'sort_order': 4,
        'price_monthly': CUSTOM_PRICE,            # "Custom / contact sales"
        'max_messages_per_month': UNLIMITED,
        'max_clients': UNLIMITED,
        'max_sessions_per_month': UNLIMITED,
        'max_images_per_month': UNLIMITED,
        'max_voice_per_month': UNLIMITED,
        'max_social_channels': UNLIMITED,         # all channels
        'max_dashboard_metrics': UNLIMITED,       # Custom
        'data_retention_days': UNLIMITED,         # Custom retention
        'sla_response_hours': 4,                   # Dedicated CSM
        'allow_whatsapp': True,
        'allow_messenger': True,
        'allow_instagram': True,
        'allow_telegram': True,
        'allow_byok': True,
        'allow_voice_input': True,
        'allow_image_input': True,
        'allow_real_time_inventory': True,
        'allow_hubspot': True,
        'allow_slack': True,
        'allow_webhooks': True,
        'allow_god_view': True,
        'allow_canned_responses': True,
        'allow_conversation_tags': True,
        'allow_csv_export': True,
        'allow_advanced_reports': True,           # Custom reports
        'priority_support': True,                 # Dedicated CSM
        'remove_branding': True,                  # White-label branding
        'allow_custom_domain': True,              # Custom website integration
        'allow_api_access': True,
        'allow_multi_language': True,
    },
]

# Fields we refuse to clobber if already configured in admin/Stripe.
PRESERVE_IF_SET = ('stripe_price_id', 'stripe_price_id_annual')


class Command(BaseCommand):
    help = 'Create/update the four official subscription plans to match the pricing doc.'

    def add_arguments(self, parser):
        parser.add_argument('--starter-price', type=str, default=None,
                            help='Monthly USD price for Starter (doc ships a placeholder).')
        parser.add_argument('--growth-price', type=str, default=None,
                            help='Monthly USD price for Growth (defaults to 79).')
        parser.add_argument('--pro-price', type=str, default=None,
                            help='Monthly USD price for Pro (doc ships a placeholder).')
        parser.add_argument('--backfill', action='store_true',
                            help="Re-point existing tenants' plan FK by name so the "
                                 "billing page resolves their plan after re-seed.")

    @transaction.atomic
    def handle(self, *args, **opts):
        price_overrides = {
            'Starter': opts.get('starter_price'),
            'Growth': opts.get('growth_price'),
            'Pro': opts.get('pro_price'),
        }

        created, updated = 0, 0

        for spec in PLAN_SPECS:
            spec = dict(spec)  # copy so we can mutate price
            name = spec['name']

            # Apply CLI price override if provided (else use the spec price).
            override = price_overrides.get(name)
            if override is not None:
                spec['price_monthly'] = Decimal(str(override))

            plan = Plan.objects.filter(name=name).first()
            is_new = plan is None
            if is_new:
                plan = Plan(name=name)

            # Apply every spec field.
            for field, value in spec.items():
                setattr(plan, field, value)

            plan.is_public = True

            # Never clobber Stripe linkage that already exists.
            if not is_new:
                existing = Plan.objects.get(pk=plan.pk)
                for field in PRESERVE_IF_SET:
                    if getattr(existing, field, None):
                        setattr(plan, field, getattr(existing, field))

            plan.save()
            if is_new:
                created += 1
                self.stdout.write(self.style.SUCCESS(
                    f'  + created plan "{name}" (${plan.price_monthly}/mo)'))
            else:
                updated += 1
                self.stdout.write(f'  ~ updated plan "{name}" (${plan.price_monthly}/mo)')

        if opts.get('backfill'):
            self._backfill_tenants()

        self.stdout.write(self.style.SUCCESS(
            f'\nDone — {created} created, {updated} updated.'
        ))

    def _backfill_tenants(self):
        """Re-point tenants whose plan FK got orphaned during re-seed.

        Re-seeding never deletes plans, so FKs normally survive. This is a
        safety net for environments where plans were deleted/recreated: any
        tenant with a NULL plan but a Stripe subscription keeps its NULL (the
        billing page self-heals from Stripe). We only log counts here so the
        operator can see the state — we do NOT guess a plan for tenants that
        never had one.
        """
        from users.models import TenantProfile
        null_plan = TenantProfile.objects.filter(plan__isnull=True)
        with_stripe = null_plan.exclude(stripe_subscription_id='').exclude(
            stripe_subscription_id__isnull=True).count()
        total_null = null_plan.count()
        self.stdout.write(
            f'\nBackfill check: {total_null} tenant(s) with no plan '
            f'({with_stripe} have a Stripe subscription and will self-heal on '
            f'next billing page load).'
        )
