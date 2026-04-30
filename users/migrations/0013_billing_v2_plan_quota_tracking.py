from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0012_plan_features_audit_overrides'),
    ]

    operations = [
        # ── Plan: advanced feature flags ──────────────────────────────────────
        migrations.AddField(
            model_name='plan',
            name='allow_real_time_inventory',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='plan',
            name='allow_advanced_reports',
            field=models.BooleanField(default=False),
        ),

        # ── Plan: message-based usage limits ──────────────────────────────────
        migrations.AddField(
            model_name='plan',
            name='max_messages_per_month',
            field=models.IntegerField(default=500),
        ),
        migrations.AddField(
            model_name='plan',
            name='max_images_per_month',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='plan',
            name='max_voice_per_month',
            field=models.IntegerField(default=0),
        ),

        # ── Plan: dashboard & channels ─────────────────────────────────────────
        migrations.AddField(
            model_name='plan',
            name='max_dashboard_metrics',
            field=models.IntegerField(default=3),
        ),
        migrations.AddField(
            model_name='plan',
            name='max_social_channels',
            field=models.IntegerField(default=0),
        ),

        # ── Plan: data retention ──────────────────────────────────────────────
        migrations.AddField(
            model_name='plan',
            name='data_retention_days',
            field=models.IntegerField(default=30),
        ),

        # ── Plan: annual billing ──────────────────────────────────────────────
        migrations.AddField(
            model_name='plan',
            name='stripe_price_id_annual',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),

        # ── TenantProfile: billing interval & cycle ────────────────────────────
        migrations.AddField(
            model_name='tenantprofile',
            name='billing_interval',
            field=models.CharField(
                choices=[('monthly', 'Monthly'), ('annual', 'Annual')],
                default='monthly',
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name='tenantprofile',
            name='billing_cycle_anchor',
            field=models.DateField(blank=True, null=True),
        ),

        # ── TenantProfile: per-resource usage counters ────────────────────────
        migrations.AddField(
            model_name='tenantprofile',
            name='messages_this_month',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='tenantprofile',
            name='images_this_month',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='tenantprofile',
            name='voice_this_month',
            field=models.IntegerField(default=0),
        ),

        # ── TenantProfile: add-on top-ups ─────────────────────────────────────
        migrations.AddField(
            model_name='tenantprofile',
            name='addon_messages',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='tenantprofile',
            name='addon_images',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='tenantprofile',
            name='addon_voice',
            field=models.IntegerField(default=0),
        ),
    ]
