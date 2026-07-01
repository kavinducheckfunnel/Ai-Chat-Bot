from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0033_client_idle_message_client_exit_message'),
    ]

    operations = [
        migrations.AddField(
            model_name='client',
            name='notification_delay_seconds',
            field=models.IntegerField(default=0),
        ),
    ]
