from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0009_client_omnichannel_byok'),
    ]

    operations = [
        # Plan gets a Stripe price ID
        migrations.AddField(
            model_name='plan',
            name='stripe_price_id',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        # TenantProfile gets Stripe billing fields
        migrations.AddField(
            model_name='tenantprofile',
            name='stripe_customer_id',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='tenantprofile',
            name='stripe_subscription_id',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='tenantprofile',
            name='stripe_subscription_status',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='tenantprofile',
            name='trial_ends_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
