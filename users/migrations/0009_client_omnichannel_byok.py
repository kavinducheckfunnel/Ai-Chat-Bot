from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0008_client_widget_feature_toggles'),
    ]

    operations = [
        # BYOK
        migrations.AddField(
            model_name='client',
            name='ai_api_key',
            field=models.CharField(blank=True, max_length=500, null=True),
        ),
        migrations.AddField(
            model_name='client',
            name='ai_model',
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
        migrations.AddField(
            model_name='client',
            name='ai_provider',
            field=models.CharField(
                choices=[('openrouter', 'OpenRouter'), ('openai', 'OpenAI'), ('anthropic', 'Anthropic')],
                default='openrouter',
                max_length=20,
            ),
        ),
        # WhatsApp
        migrations.AddField(
            model_name='client',
            name='whatsapp_phone_number_id',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='client',
            name='whatsapp_access_token',
            field=models.CharField(blank=True, max_length=500, null=True),
        ),
        migrations.AddField(
            model_name='client',
            name='whatsapp_verify_token',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='client',
            name='whatsapp_enabled',
            field=models.BooleanField(default=False),
        ),
        # Messenger
        migrations.AddField(
            model_name='client',
            name='messenger_page_id',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='client',
            name='messenger_page_access_token',
            field=models.CharField(blank=True, max_length=500, null=True),
        ),
        migrations.AddField(
            model_name='client',
            name='messenger_verify_token',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='client',
            name='messenger_enabled',
            field=models.BooleanField(default=False),
        ),
        # HubSpot
        migrations.AddField(
            model_name='client',
            name='hubspot_api_key',
            field=models.CharField(blank=True, max_length=500, null=True),
        ),
    ]
