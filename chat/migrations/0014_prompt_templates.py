"""Add PromptTemplate + PromptVersion; seed both slots from file constants."""
import json
import uuid

from django.conf import settings
from django.db import migrations, models


def seed_prompt_templates(apps, schema_editor):
    """Seed `system_persona` and `state_instructions` from chat.prompts constants.

    Stored as the v1 "factory default" version. The active pointer points at v1
    so behavior is unchanged after migration (DB-backed lookup returns the same
    content the file already had).
    """
    # Local import — at migration time the chat.prompts module is importable.
    from chat import prompts as prompts_module

    PromptTemplate = apps.get_model('chat', 'PromptTemplate')
    PromptVersion  = apps.get_model('chat', 'PromptVersion')

    seeds = [
        {
            'slug': 'system_persona',
            'description': 'The persona block prepended to every chat request. Defines tone, sales playbook, and rules.',
            'body': prompts_module.SYSTEM_PERSONA,
        },
        {
            'slug': 'state_instructions',
            'description': 'Per-state playbook map (RESEARCH/EVALUATION/OBJECTION/RECOVERY/READY_TO_BUY). Stored as JSON.',
            'body': json.dumps(prompts_module.STATE_INSTRUCTIONS, indent=2, ensure_ascii=False),
        },
    ]

    for seed in seeds:
        template = PromptTemplate.objects.create(
            id=uuid.uuid4(),
            slug=seed['slug'],
            description=seed['description'],
        )
        version = PromptVersion.objects.create(
            id=uuid.uuid4(),
            template=template,
            version=1,
            body=seed['body'],
            notes='Factory default seeded from chat.prompts on first migration.',
            is_default=True,
        )
        template.active_version = version
        template.save(update_fields=['active_version'])


def unseed_prompt_templates(apps, schema_editor):
    PromptTemplate = apps.get_model('chat', 'PromptTemplate')
    PromptTemplate.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0013_chatsession_lead_capture_prompted'),
    ]

    operations = [
        migrations.CreateModel(
            name='PromptTemplate',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('slug', models.SlugField(
                    max_length=64, unique=True,
                    choices=[
                        ('system_persona', 'System Persona'),
                        ('state_instructions', 'State Instructions'),
                    ],
                )),
                ('description', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'ordering': ['slug']},
        ),
        migrations.CreateModel(
            name='PromptVersion',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('version', models.PositiveIntegerField()),
                ('body', models.TextField()),
                ('notes', models.CharField(blank=True, max_length=500)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('is_default', models.BooleanField(default=False)),
                ('created_by', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=models.SET_NULL,
                    related_name='prompt_versions',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('template', models.ForeignKey(
                    on_delete=models.CASCADE,
                    related_name='versions',
                    to='chat.prompttemplate',
                )),
            ],
            options={
                'ordering': ['-created_at'],
                'unique_together': {('template', 'version')},
                'indexes': [
                    models.Index(fields=['template', '-created_at'], name='chat_prompt_templat_5e5741_idx'),
                ],
            },
        ),
        migrations.AddField(
            model_name='prompttemplate',
            name='active_version',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=models.SET_NULL,
                related_name='active_for',
                to='chat.promptversion',
            ),
        ),
        migrations.RunPython(seed_prompt_templates, reverse_code=unseed_prompt_templates),
    ]
