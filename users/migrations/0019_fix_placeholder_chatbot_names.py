"""One-time rename: clients still using the placeholder 'test' or default
'AI Assistant' get renamed to '<Brand> Assistant' so the widget shows a
real brand name. Reversible: sets affected rows back to 'AI Assistant'.
"""
from django.db import migrations


PLACEHOLDERS = {'test', 'Test', 'TEST', 'AI Assistant', ''}


def fix_placeholders(apps, schema_editor):
    Client = apps.get_model('users', 'Client')
    for client in Client.objects.filter(chatbot_name__in=PLACEHOLDERS):
        if client.name:
            client.chatbot_name = f'{client.name} Assistant'
            client.save(update_fields=['chatbot_name'])


def revert(apps, schema_editor):
    # Not strictly the inverse, but keeps downward migration valid.
    Client = apps.get_model('users', 'Client')
    for client in Client.objects.all():
        if client.chatbot_name and client.chatbot_name.endswith(' Assistant'):
            client.chatbot_name = 'AI Assistant'
            client.save(update_fields=['chatbot_name'])


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0018_client_cta_mode'),
    ]

    operations = [
        migrations.RunPython(fix_placeholders, revert),
    ]
