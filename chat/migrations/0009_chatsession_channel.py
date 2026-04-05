from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0008_visitor_fingerprint_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='chatsession',
            name='channel',
            field=models.CharField(
                choices=[('website', 'Website'), ('whatsapp', 'WhatsApp'), ('messenger', 'Messenger')],
                default='website',
                max_length=20,
            ),
        ),
    ]
