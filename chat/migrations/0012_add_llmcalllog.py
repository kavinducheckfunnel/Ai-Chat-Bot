from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('chat',  '0011_visitor_model'),
        ('users', '0017_client_last_scraped_at'),  # latest users tip
    ]

    operations = [
        migrations.CreateModel(
            name='LLMCallLog',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('model',    models.CharField(max_length=120)),
                ('provider', models.CharField(max_length=20)),
                ('is_byok',  models.BooleanField(default=False)),
                ('latency_ms',        models.IntegerField()),
                ('prompt_tokens',     models.IntegerField(blank=True, null=True)),
                ('completion_tokens', models.IntegerField(blank=True, null=True)),
                ('total_tokens',      models.IntegerField(blank=True, null=True)),
                ('cost_usd', models.DecimalField(decimal_places=6, default=0, max_digits=10)),
                ('status', models.CharField(
                    choices=[
                        ('ok',            'OK'),
                        ('rate_limited',  'Rate Limited'),
                        ('error',         'Error'),
                        ('fallback_used', 'Fallback Used'),
                    ],
                    default='ok',
                    max_length=20,
                )),
                ('fallback_from', models.CharField(blank=True, max_length=120)),
                ('error_message', models.TextField(blank=True)),
                ('prompt_hash',   models.CharField(blank=True, max_length=16)),
                ('created_at',    models.DateTimeField(auto_now_add=True)),
                ('client', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='llm_calls',
                    to='users.client',
                )),
                ('session', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='llm_calls',
                    to='chat.chatsession',
                )),
            ],
            options={
                'ordering': ['-created_at'],
                'indexes': [
                    models.Index(fields=['client', '-created_at'],   name='chat_llm_client_4f1b5c_idx'),
                    models.Index(fields=['status', '-created_at'],   name='chat_llm_status_8e2d11_idx'),
                    models.Index(fields=['model', '-created_at'],    name='chat_llm_model_2a9f43_idx'),
                    models.Index(fields=['is_byok', '-created_at'],  name='chat_llm_byok_7c44e9_idx'),
                ],
            },
        ),
    ]
