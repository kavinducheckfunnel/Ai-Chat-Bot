from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0032_client_active_offers'),
    ]

    operations = [
        migrations.AddField(
            model_name='client',
            name='idle_message',
            field=models.CharField(blank=True, default='', max_length=200),
        ),
        migrations.AddField(
            model_name='client',
            name='exit_message',
            field=models.CharField(blank=True, default='', max_length=200),
        ),
    ]
