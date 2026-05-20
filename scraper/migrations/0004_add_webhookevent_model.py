from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0017_client_last_scraped_at'),  # latest tip of users app
        ('scraper', '0003_fix_vector_dim_and_product_id_type'),
    ]

    operations = [
        migrations.CreateModel(
            name='WebhookEvent',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('source', models.CharField(
                    choices=[
                        ('shopify', 'Shopify'),
                        ('woocommerce', 'WooCommerce'),
                        ('wordpress', 'WordPress'),
                    ],
                    max_length=20,
                )),
                ('event_type', models.CharField(blank=True, max_length=60)),
                ('resource_id', models.CharField(blank=True, db_index=True, max_length=64)),
                ('resource_title', models.CharField(blank=True, max_length=300)),
                ('status', models.CharField(
                    choices=[
                        ('queued', 'Queued'),
                        ('done', 'Done'),
                        ('failed', 'Failed'),
                    ],
                    default='queued',
                    max_length=20,
                )),
                ('error_message', models.TextField(blank=True)),
                ('duration_ms', models.IntegerField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('client', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='webhook_events',
                    to='users.client',
                )),
            ],
            options={
                'ordering': ['-created_at'],
                'indexes': [
                    models.Index(fields=['client', '-created_at'], name='scraper_web_client__1ce4a8_idx'),
                ],
            },
        ),
    ]
