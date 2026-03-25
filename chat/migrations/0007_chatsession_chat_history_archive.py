from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0006_email_notification_flags'),
    ]

    operations = [
        migrations.AddField(
            model_name='chatsession',
            name='chat_history_archive',
            field=models.JSONField(default=list),
        ),
    ]
