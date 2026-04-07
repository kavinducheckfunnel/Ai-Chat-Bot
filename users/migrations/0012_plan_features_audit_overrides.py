from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0011_client_notifications_telegram'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ── Plan: feature flags ────────────────────────────────────────────────
        migrations.AddField('plan', 'allow_whatsapp', models.BooleanField(default=False)),
        migrations.AddField('plan', 'allow_telegram', models.BooleanField(default=False)),
        migrations.AddField('plan', 'allow_messenger', models.BooleanField(default=False)),
        migrations.AddField('plan', 'allow_byok', models.BooleanField(default=False)),
        migrations.AddField('plan', 'max_knowledge_pages', models.IntegerField(default=20)),
        migrations.AddField('plan', 'max_ai_tokens_per_month', models.IntegerField(default=50000)),
        migrations.AddField('plan', 'allow_hubspot', models.BooleanField(default=False)),
        migrations.AddField('plan', 'allow_slack', models.BooleanField(default=False)),
        migrations.AddField('plan', 'allow_webhooks', models.BooleanField(default=False)),
        migrations.AddField('plan', 'allow_god_view', models.BooleanField(default=True)),
        migrations.AddField('plan', 'allow_canned_responses', models.BooleanField(default=False)),
        migrations.AddField('plan', 'max_canned_responses', models.IntegerField(default=0)),
        migrations.AddField('plan', 'allow_conversation_tags', models.BooleanField(default=False)),
        migrations.AddField('plan', 'allow_csv_export', models.BooleanField(default=False)),
        migrations.AddField('plan', 'allow_voice_input', models.BooleanField(default=False)),
        migrations.AddField('plan', 'allow_image_input', models.BooleanField(default=False)),
        migrations.AddField('plan', 'allow_fomo_triggers', models.BooleanField(default=True)),
        migrations.AddField('plan', 'remove_branding', models.BooleanField(default=False)),
        migrations.AddField('plan', 'allow_custom_domain', models.BooleanField(default=False)),
        migrations.AddField('plan', 'allow_custom_logo', models.BooleanField(default=True)),
        migrations.AddField('plan', 'allow_api_access', models.BooleanField(default=False)),
        migrations.AddField('plan', 'allow_multi_language', models.BooleanField(default=False)),
        migrations.AddField('plan', 'priority_support', models.BooleanField(default=False)),
        migrations.AddField('plan', 'sla_response_hours', models.IntegerField(default=48)),
        migrations.AddField('plan', 'is_public', models.BooleanField(default=True)),
        migrations.AddField('plan', 'sort_order', models.IntegerField(default=0)),

        # ── TenantFeatureOverride ──────────────────────────────────────────────
        migrations.CreateModel(
            name='TenantFeatureOverride',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False)),
                ('feature_name', models.CharField(max_length=100)),
                ('enabled', models.BooleanField(default=True)),
                ('reason', models.CharField(blank=True, max_length=255)),
                ('expires_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('granted_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='feature_overrides', to='users.tenantprofile')),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.AlterUniqueTogether(
            name='tenantfeatureoverride',
            unique_together={('tenant', 'feature_name')},
        ),

        # ── AuditLog ──────────────────────────────────────────────────────────
        migrations.CreateModel(
            name='AuditLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False)),
                ('action', models.CharField(max_length=50)),
                ('target_type', models.CharField(blank=True, max_length=50)),
                ('target_id', models.CharField(blank=True, max_length=100)),
                ('target_label', models.CharField(blank=True, max_length=255)),
                ('before_value', models.JSONField(blank=True, null=True)),
                ('after_value', models.JSONField(blank=True, null=True)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('notes', models.TextField(blank=True)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('actor', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='audit_actions', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-timestamp']},
        ),

        # ── PlatformAnnouncement ──────────────────────────────────────────────
        migrations.CreateModel(
            name='PlatformAnnouncement',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False)),
                ('title', models.CharField(max_length=200)),
                ('body', models.TextField()),
                ('cta_label', models.CharField(blank=True, max_length=100)),
                ('cta_url', models.CharField(blank=True, max_length=500)),
                ('announcement_type', models.CharField(default='info', max_length=20)),
                ('target', models.CharField(default='all', max_length=20)),
                ('is_active', models.BooleanField(default=True)),
                ('dismissible', models.BooleanField(default=True)),
                ('starts_at', models.DateTimeField(blank=True, null=True)),
                ('ends_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('dismissed_by', models.ManyToManyField(blank=True, related_name='dismissed_announcements', to=settings.AUTH_USER_MODEL)),
                ('target_tenant', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='users.tenantprofile')),
            ],
            options={'ordering': ['-created_at']},
        ),
    ]
