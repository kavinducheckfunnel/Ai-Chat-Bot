# Generated for conversation memory feature (Phase 2).
#
# Adds the two fields that back chat.tasks.summarize_chat_session:
#   • conversation_summary    — rolling recap text
#   • summary_through_index   — pointer into chat_history for incremental updates

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0017_v2_architecture_stubs'),
    ]

    operations = [
        migrations.AddField(
            model_name='chatsession',
            name='conversation_summary',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='chatsession',
            name='summary_through_index',
            field=models.IntegerField(default=0),
        ),
    ]
