from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0010_stripe_billing'),
    ]

    operations = [
        # Telegram Bot
        migrations.AddField(
            model_name='client',
            name='telegram_bot_token',
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
        migrations.AddField(
            model_name='client',
            name='telegram_enabled',
            field=models.BooleanField(default=False),
        ),
        # Slack webhook
        migrations.AddField(
            model_name='client',
            name='slack_webhook_url',
            field=models.CharField(blank=True, max_length=500, null=True),
        ),
        # Outbound webhook (Zapier / n8n)
        migrations.AddField(
            model_name='client',
            name='outbound_webhook_url',
            field=models.CharField(blank=True, max_length=500, null=True),
        ),
        migrations.AddField(
            model_name='client',
            name='outbound_webhook_events',
            field=models.CharField(default='hot_lead,lead_captured,new_session', max_length=200),
        ),
        # Canned responses
        migrations.AddField(
            model_name='client',
            name='canned_responses',
            field=models.JSONField(blank=True, default=list),
        ),
    ]
