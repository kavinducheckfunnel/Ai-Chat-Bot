"""
Publish the current file `SYSTEM_PERSONA` as a new active PromptVersion.

The live bot reads the persona from the DB (PromptTemplate.active_version) and
only falls back to the file constant when no DB version exists. So a code change
to chat/prompts.py:SYSTEM_PERSONA does NOT take effect in production until the
DB's active version is updated — that's what this command does.

Idempotent + safe:
  • If the active version's body already matches the file → no-op.
  • If the active version was HAND-EDITED via the admin UI (is_default=False and
    body differs from file) → skip and warn, so we never silently clobber a
    deliberate manual edit. Use --force to override.
"""
from django.core.management.base import BaseCommand
from django.db.models import Max


class Command(BaseCommand):
    help = 'Publish chat/prompts.py SYSTEM_PERSONA as the active system_persona version.'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true',
                            help='Overwrite even a hand-edited (non-default) active version.')

    def handle(self, *args, **opts):
        from chat.models import PromptTemplate, PromptVersion
        from chat import prompts as prompts_module

        file_body = prompts_module.SYSTEM_PERSONA
        slug = 'system_persona'

        template = PromptTemplate.objects.filter(slug=slug).select_related('active_version').first()
        if template is None:
            self.stdout.write(self.style.WARNING(
                f'No PromptTemplate slug={slug} — bot is using the file default already. Nothing to do.'))
            return

        active = template.active_version
        if active is not None:
            if (active.body or '').strip() == (file_body or '').strip():
                self.stdout.write(self.style.SUCCESS('Active version already matches the file. No-op.'))
                return
            if not active.is_default and not opts['force']:
                self.stdout.write(self.style.WARNING(
                    'Active version was hand-edited via the admin UI (is_default=False). '
                    'Skipping to avoid clobbering it. Re-run with --force to override.'))
                return

        next_version = (PromptVersion.objects.filter(template=template)
                        .aggregate(m=Max('version'))['m'] or 0) + 1
        version = PromptVersion.objects.create(
            template=template,
            version=next_version,
            body=file_body,
            notes='Reseeded from file SYSTEM_PERSONA (email+phone lead capture wording).',
            is_default=False,
        )
        template.active_version = version
        template.save(update_fields=['active_version'])

        # Clear this process's cache + notify other workers (Daphne/Celery).
        try:
            from chat.prompt_service import bump_cache, publish_invalidate
            bump_cache(slug)
            publish_invalidate(slug)
        except Exception:
            pass

        self.stdout.write(self.style.SUCCESS(
            f'Published system_persona v{next_version} as active.'))
