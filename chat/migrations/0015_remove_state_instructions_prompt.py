"""Remove the editable `state_instructions` prompt template.

We initially shipped two editable prompts; on reflection state instructions
are internal behavior plumbing (per-state playbook map) and shouldn't be
hot-edited in production. Reverted to a file-only constant. This migration
deletes the seeded row + version(s) so the editor lists only system_persona.
"""

from django.db import migrations, models


def delete_state_instructions(apps, schema_editor):
    PromptTemplate = apps.get_model('chat', 'PromptTemplate')
    # CASCADE on PromptVersion.template kills any saved versions too.
    PromptTemplate.objects.filter(slug='state_instructions').delete()


def reseed_state_instructions(apps, schema_editor):
    """Reverse: put it back as a v1 factory default if someone rolls back."""
    import json
    import uuid
    from chat import prompts as prompts_module

    PromptTemplate = apps.get_model('chat', 'PromptTemplate')
    PromptVersion  = apps.get_model('chat', 'PromptVersion')

    if PromptTemplate.objects.filter(slug='state_instructions').exists():
        return

    template = PromptTemplate.objects.create(
        id=uuid.uuid4(),
        slug='state_instructions',
        description='Per-state playbook map (RESEARCH/EVALUATION/OBJECTION/RECOVERY/READY_TO_BUY). Stored as JSON.',
    )
    version = PromptVersion.objects.create(
        id=uuid.uuid4(),
        template=template,
        version=1,
        body=json.dumps(prompts_module.STATE_INSTRUCTIONS, indent=2, ensure_ascii=False),
        notes='Factory default re-seeded by reverse migration.',
        is_default=True,
    )
    template.active_version = version
    template.save(update_fields=['active_version'])


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0014_prompt_templates'),
    ]

    operations = [
        migrations.RunPython(delete_state_instructions, reverse_code=reseed_state_instructions),
        migrations.AlterField(
            model_name='prompttemplate',
            name='slug',
            field=models.SlugField(
                max_length=64, unique=True,
                choices=[('system_persona', 'System Persona')],
            ),
        ),
    ]
