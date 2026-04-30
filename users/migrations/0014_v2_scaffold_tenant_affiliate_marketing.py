from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0013_billing_v2_plan_quota_tracking'),
    ]

    operations = [
        migrations.AddField(
            model_name='tenantprofile',
            name='affiliate_code',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='tenantprofile',
            name='marketing_messages_enabled',
            field=models.BooleanField(default=False),
        ),
    ]
