# Generated for the invoice-branding feature.
#
# Snapshots the tenant's first-client logo URL + brand colour at issue time
# so historical invoices keep their branding even if the client later
# redesigns. See users.invoice_service.generate_invoice.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0025_invoice_model'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoice',
            name='brand_logo_url_at_issue',
            field=models.URLField(blank=True, default='', max_length=500),
        ),
        migrations.AddField(
            model_name='invoice',
            name='brand_color_at_issue',
            field=models.CharField(blank=True, default='', max_length=20),
        ),
    ]
