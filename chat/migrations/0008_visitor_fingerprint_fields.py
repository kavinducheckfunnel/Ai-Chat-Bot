from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0007_chatsession_chat_history_archive'),
    ]

    operations = [
        migrations.AddField(
            model_name='chatsession',
            name='visitor_ip',
            field=models.GenericIPAddressField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='chatsession',
            name='visitor_country',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='chatsession',
            name='visitor_city',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='chatsession',
            name='visitor_country_code',
            field=models.CharField(blank=True, max_length=10, null=True),
        ),
        migrations.AddField(
            model_name='chatsession',
            name='visitor_device',
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
        migrations.AddField(
            model_name='chatsession',
            name='visitor_os',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='chatsession',
            name='visitor_browser',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='chatsession',
            name='visitor_referrer',
            field=models.URLField(blank=True, max_length=2000, null=True),
        ),
        migrations.AddField(
            model_name='chatsession',
            name='visitor_timezone',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='chatsession',
            name='page_visits',
            field=models.JSONField(default=list),
        ),
    ]
