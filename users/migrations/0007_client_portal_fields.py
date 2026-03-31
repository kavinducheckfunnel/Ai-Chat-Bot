from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0006_client_notification_email'),
    ]

    operations = [
        migrations.AddField(
            model_name='client',
            name='chatbot_theme',
            field=models.CharField(
                choices=[('dark', 'Dark'), ('light', 'Light')],
                default='dark',
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name='client',
            name='primary_goal',
            field=models.CharField(
                choices=[('sales', 'Grow Sales'), ('support', 'Automate Support'), ('leads', 'Generate Leads')],
                default='leads',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='client',
            name='onboarding_complete',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='tenantprofile',
            name='onboarding_complete',
            field=models.BooleanField(default=False),
        ),
    ]
