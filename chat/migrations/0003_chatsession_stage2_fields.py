from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0002_chatsession_client'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Use raw SQL with IF NOT EXISTS to safely handle columns that may already exist
        migrations.RunSQL(
            sql="""
                ALTER TABLE chat_chatsession
                    ADD COLUMN IF NOT EXISTS kanban_state VARCHAR(20) NOT NULL DEFAULT 'NEW',
                    ADD COLUMN IF NOT EXISTS heat_score DOUBLE PRECISION NOT NULL DEFAULT 0.0,
                    ADD COLUMN IF NOT EXISTS takeover_active BOOLEAN NOT NULL DEFAULT FALSE,
                    ADD COLUMN IF NOT EXISTS closing_triggered BOOLEAN NOT NULL DEFAULT FALSE,
                    ADD COLUMN IF NOT EXISTS afk_nudge_sent BOOLEAN NOT NULL DEFAULT FALSE,
                    ADD COLUMN IF NOT EXISTS last_visitor_message_at TIMESTAMP WITH TIME ZONE;

                -- taken_over_by FK (only add if column doesn't exist)
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name='chat_chatsession' AND column_name='taken_over_by_id'
                    ) THEN
                        ALTER TABLE chat_chatsession
                            ADD COLUMN taken_over_by_id INTEGER REFERENCES auth_user(id) ON DELETE SET NULL;
                    END IF;
                END $$;
            """,
            reverse_sql="""
                ALTER TABLE chat_chatsession
                    DROP COLUMN IF EXISTS kanban_state,
                    DROP COLUMN IF EXISTS heat_score,
                    DROP COLUMN IF EXISTS takeover_active,
                    DROP COLUMN IF EXISTS closing_triggered,
                    DROP COLUMN IF EXISTS afk_nudge_sent,
                    DROP COLUMN IF EXISTS last_visitor_message_at,
                    DROP COLUMN IF EXISTS taken_over_by_id;
            """,
        ),

        # Tell Django's migration state about all the fields
        migrations.AddField(
            model_name='chatsession',
            name='kanban_state',
            field=models.CharField(
                choices=[('NEW','New'),('ENGAGED','Engaged'),('HOT_LEAD','Hot Lead'),('CONVERTED','Converted'),('LOST','Lost')],
                default='NEW', max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='chatsession',
            name='heat_score',
            field=models.FloatField(default=0.0),
        ),
        migrations.AddField(
            model_name='chatsession',
            name='takeover_active',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='chatsession',
            name='taken_over_by',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='takeover_sessions',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='chatsession',
            name='closing_triggered',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='chatsession',
            name='afk_nudge_sent',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='chatsession',
            name='last_visitor_message_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
