from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0009_chatsession_channel'),
    ]

    operations = [
        # Conversation tags (tenant-applied labels)
        migrations.AddField(
            model_name='chatsession',
            name='tags',
            field=models.JSONField(blank=True, default=list),
        ),
        # Extend channel choices to include Telegram
        migrations.AlterField(
            model_name='chatsession',
            name='channel',
            field=models.CharField(
                choices=[
                    ('website', 'Website'),
                    ('whatsapp', 'WhatsApp'),
                    ('messenger', 'Messenger'),
                    ('telegram', 'Telegram'),
                ],
                default='website',
                max_length=20,
            ),
        ),
    ]
