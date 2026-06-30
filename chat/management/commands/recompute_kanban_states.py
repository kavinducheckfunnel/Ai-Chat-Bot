"""
Recompute every session's kanban_state from its actual metrics (heat / intent /
urgency / messages) so the Leads board reflects reality instead of leaving
everyone stuck in NEW.

This is a one-time correction for sessions created before the auto-promoter
covered the full ladder. Terminal / advanced stages (CONVERTED, LOST,
READY_TO_BUY) are preserved. The dashboard "Lead Pipeline" reads the same
kanban_state, so it stays in sync with the board after this runs.

Usage:
  python manage.py recompute_kanban_states                 # all clients
  python manage.py recompute_kanban_states --client <uuid> # one client
  python manage.py recompute_kanban_states --dry-run       # report only
"""
from collections import Counter

from django.core.management.base import BaseCommand

from chat.models import ChatSession
from chat.ai_service import compute_kanban_stage, _recompute_heat_score


class Command(BaseCommand):
    help = "Move every lead to its correct kanban stage based on its metrics."

    def add_arguments(self, parser):
        parser.add_argument('--client', dest='client', default=None,
                            help='Limit to one client id (UUID).')
        parser.add_argument('--dry-run', action='store_true',
                            help='Report the changes without writing them.')

    def handle(self, *args, **opts):
        qs = ChatSession.objects.all()
        if opts.get('client'):
            qs = qs.filter(client_id=opts['client'])

        before = Counter()
        after = Counter()
        to_update = []
        for s in qs.only(
            'session_id', 'kanban_state', 'conversation_state', 'message_count',
            'current_intent_ema', 'current_budget_ema', 'current_urgency_ema',
            'heat_score',
        ).iterator():
            cur = (s.kanban_state or 'NEW')
            new = compute_kanban_stage(s)
            before[cur] += 1
            after[new] += 1
            # Keep heat_score in sync with the EMAs while we're here.
            new_heat = _recompute_heat_score(s)
            if new != cur or abs((s.heat_score or 0) - new_heat) > 0.05:
                s.kanban_state = new
                s.heat_score = new_heat
                to_update.append(s)

        self.stdout.write(f'Sessions scanned: {sum(before.values())}')
        self.stdout.write(f'Before: {dict(before)}')
        self.stdout.write(f'After:  {dict(after)}')
        self.stdout.write(f'Changed: {len(to_update)}')

        if opts.get('dry_run'):
            self.stdout.write(self.style.WARNING('Dry run — no changes written.'))
            return

        # Bulk update in chunks to keep memory + query size sane.
        for i in range(0, len(to_update), 500):
            ChatSession.objects.bulk_update(
                to_update[i:i + 500], ['kanban_state', 'heat_score']
            )
        self.stdout.write(self.style.SUCCESS(f'Updated {len(to_update)} sessions.'))
