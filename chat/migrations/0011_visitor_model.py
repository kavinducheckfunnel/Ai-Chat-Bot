import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0017_client_last_scraped_at'),
        ('chat', '0010_chatsession_tags_telegram'),
    ]

    operations = [
        migrations.CreateModel(
            name='Visitor',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('visitor_uid', models.CharField(db_index=True, max_length=64)),
                ('first_seen', models.DateTimeField(auto_now_add=True)),
                ('last_seen', models.DateTimeField(auto_now=True)),
                ('total_sessions', models.IntegerField(default=0)),
                ('total_messages', models.IntegerField(default=0)),
                ('total_page_views', models.IntegerField(default=0)),
                ('total_time_seconds', models.IntegerField(default=0)),
                ('total_clicks', models.IntegerField(default=0)),
                ('total_atc_clicks', models.IntegerField(default=0)),
                ('intent_ema', models.FloatField(default=0)),
                ('budget_ema', models.FloatField(default=0)),
                ('urgency_ema', models.FloatField(default=0)),
                ('lead_email', models.EmailField(blank=True, max_length=254)),
                ('lead_phone', models.CharField(blank=True, max_length=50)),
                ('lead_name', models.CharField(blank=True, max_length=200)),
                ('device', models.CharField(blank=True, max_length=20)),
                ('os', models.CharField(blank=True, max_length=20)),
                ('browser', models.CharField(blank=True, max_length=20)),
                ('country', models.CharField(blank=True, max_length=100)),
                ('city', models.CharField(blank=True, max_length=100)),
                ('country_code', models.CharField(blank=True, max_length=10)),
                ('timezone', models.CharField(blank=True, max_length=64)),
                ('ip', models.CharField(blank=True, max_length=64)),
                ('top_interest_title', models.CharField(blank=True, max_length=300)),
                ('top_interest_url', models.CharField(blank=True, max_length=500)),
                ('client', models.ForeignKey(db_index=True, on_delete=django.db.models.deletion.CASCADE, related_name='visitors', to='users.client')),
            ],
        ),
        migrations.AddConstraint(
            model_name='visitor',
            constraint=models.UniqueConstraint(fields=('visitor_uid', 'client'), name='uniq_visitor_per_client'),
        ),
        migrations.AddIndex(
            model_name='visitor',
            index=models.Index(fields=['client', '-last_seen'], name='chat_visito_client__d51017_idx'),
        ),
        migrations.AddField(
            model_name='chatsession',
            name='visitor',
            field=models.ForeignKey(blank=True, db_index=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='sessions', to='chat.visitor'),
        ),
    ]
