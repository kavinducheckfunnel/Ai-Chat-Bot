from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0017_client_last_scraped_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='client',
            name='cta_mode',
            field=models.CharField(
                choices=[
                    ('ai',     'AI-generated from behavior'),
                    ('manual', 'Manual message'),
                    ('off',    'Off — no automated CTAs'),
                ],
                default='ai',
                max_length=10,
            ),
        ),
    ]
