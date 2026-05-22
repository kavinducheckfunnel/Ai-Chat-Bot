"""Run the 25-example regression suite against the live bot.

For each example:
  1. Spin up a temporary ChatSession against a target client
  2. Replay any prior turns from `conversation` into chat_history
  3. Send the final visitor message via generate_ai_response()
  4. Score the response: pass if it contains at least one pass_signal
     AND zero fail_signals (banned phrases). Otherwise fail.

Usage:
    python manage.py run_qa_regression --client-id <uuid>
    python manage.py run_qa_regression --client-id <uuid> --category opening
    python manage.py run_qa_regression --client-id <uuid> --verbose
    python manage.py run_qa_regression --client-id <uuid> --output report.md

This is an EVALUATION harness, not a unit test. The scoring is intentionally
fuzzy (signal/anti-signal keyword presence) because the bot is generative;
exact-match assertions would always fail. The point is to track the trend —
"we used to pass 12/25, now we pass 19/25" — which is what tells you
prompt changes are working.
"""

import json
import os
import re
import time
import uuid
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError


FIXTURE_PATH = Path(__file__).resolve().parent.parent.parent / 'qa_fixtures' / 'training_examples_25.json'


class Command(BaseCommand):
    help = 'Run the 25-example sales bot regression suite against the live AI pipeline.'

    def add_arguments(self, parser):
        parser.add_argument('--client-id', required=True,
                            help='UUID of the Client to run examples against (the bot needs a KB to RAG)')
        parser.add_argument('--category', default='',
                            help='Filter to one category: opening|objection|closing|contact_capture|whatsapp|social_media|discovery')
        parser.add_argument('--verbose', action='store_true',
                            help='Print full response text for each example')
        parser.add_argument('--output', default='',
                            help='Write a Markdown report to this path')
        parser.add_argument('--only', default='',
                            help='Run only specific example IDs (comma-separated, e.g. T001,T004)')

    def handle(self, *args, **opts):
        # Lazy imports — Django not configured at module-load
        from users.models import Client
        from chat.models import ChatSession
        from chat.ai_service import generate_ai_response

        client_id = opts['client_id']
        try:
            client = Client.objects.get(pk=client_id)
        except Client.DoesNotExist:
            raise CommandError(f'Client {client_id} not found')

        if not FIXTURE_PATH.exists():
            raise CommandError(f'Fixture file missing: {FIXTURE_PATH}')
        with open(FIXTURE_PATH) as f:
            examples = json.load(f)

        # Filtering
        if opts['category']:
            examples = [e for e in examples if e['category'] == opts['category']]
        if opts['only']:
            wanted = {x.strip() for x in opts['only'].split(',') if x.strip()}
            examples = [e for e in examples if e['id'] in wanted]
        if not examples:
            raise CommandError('No examples matched the filters')

        self.stdout.write(self.style.MIGRATE_HEADING(
            f'\nRunning {len(examples)} regression example(s) against client "{client.name}"\n'
        ))

        results = []
        total_start = time.time()
        for i, ex in enumerate(examples, 1):
            self.stdout.write(f'[{i}/{len(examples)}] {ex["id"]} {ex["title"]}…')
            try:
                result = self._run_one(ex, client, generate_ai_response, ChatSession, verbose=opts['verbose'])
            except Exception as e:
                result = {'id': ex['id'], 'pass': False, 'response': '', 'matched': [], 'banned_hits': [], 'error': str(e)}
            results.append(result)
            tag = self.style.SUCCESS('PASS') if result['pass'] else self.style.ERROR('FAIL')
            self.stdout.write(f'   {tag}   pass_signals_matched={len(result["matched"])}  banned_hits={len(result["banned_hits"])}')
            if opts['verbose'] and result.get('response'):
                self.stdout.write(self.style.HTTP_INFO('   bot: ') + result['response'][:200])
            if result.get('error'):
                self.stdout.write(self.style.WARNING(f'   error: {result["error"]}'))

        elapsed = time.time() - total_start
        passed = sum(1 for r in results if r['pass'])
        total = len(results)
        pct = round(passed / total * 100, 1) if total else 0
        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_HEADING(f'RESULT: {passed}/{total} pass ({pct}%) in {elapsed:.1f}s'))

        # By-category summary
        by_cat = {}
        for r, e in zip(results, examples):
            by_cat.setdefault(e['category'], []).append(r['pass'])
        for cat, vals in sorted(by_cat.items()):
            cat_pass = sum(1 for v in vals if v)
            self.stdout.write(f'  {cat:20s} {cat_pass}/{len(vals)}')

        if opts['output']:
            self._write_markdown(opts['output'], client, results, examples, pct, elapsed)
            self.stdout.write(self.style.SUCCESS(f'Report written to {opts["output"]}'))

    def _run_one(self, ex, client, generate_ai_response, ChatSession, verbose=False):
        # Build a throwaway session that won't pollute prod data
        session = ChatSession.objects.create(
            session_id=uuid.uuid4(),
            client=client,
            visitor_id=f'qa_regression_{ex["id"]}',
            chat_history=[],
        )

        # Replay prior turns (everything except the LAST visitor message)
        prior = ex['conversation'][:-1] if ex['conversation'] else []
        for turn in prior:
            session.chat_history.append({'role': turn['role'], 'message': turn['content']})

        # The final turn must be from the visitor (the message we evaluate against)
        last = ex['conversation'][-1] if ex['conversation'] else None
        if not last or last.get('role') != 'visitor':
            session.delete()
            return {'id': ex['id'], 'pass': False, 'response': '', 'matched': [], 'banned_hits': [], 'error': 'last turn must be visitor'}

        session.save()

        try:
            ai_response = generate_ai_response(session, last['content'], behavior_matrix={})
            reply = (ai_response or {}).get('reply_text', '') or ''
        finally:
            # Best-effort cleanup so we don't accumulate test sessions
            try:
                session.delete()
            except Exception:
                pass

        reply_lower = reply.lower()

        # Pass signals: case-insensitive substring matching
        matched = [s for s in ex.get('pass_signals', []) if s.lower() in reply_lower]
        # Banned phrases: explicit fail_signals (case-insensitive)
        banned_hits = [s for s in ex.get('fail_signals', []) if s.lower() in reply_lower]

        # Pass criteria: must match >=1 pass_signal AND have 0 banned hits.
        # Single very-strong banned hit fails the example outright.
        passed = (len(matched) >= 1) and (len(banned_hits) == 0)

        return {
            'id': ex['id'],
            'category': ex['category'],
            'title': ex['title'],
            'technique': ex.get('technique', ''),
            'pass': passed,
            'response': reply,
            'matched': matched,
            'banned_hits': banned_hits,
        }

    def _write_markdown(self, path, client, results, examples, pct, elapsed):
        lines = []
        lines.append(f'# QA Regression Report — {client.name}')
        lines.append('')
        lines.append(f'**{sum(1 for r in results if r["pass"])}/{len(results)} pass ({pct}%)** in {elapsed:.1f}s')
        lines.append('')
        lines.append('## By category')
        lines.append('')
        by_cat = {}
        for r, e in zip(results, examples):
            by_cat.setdefault(e['category'], []).append(r['pass'])
        lines.append('| Category | Pass | Total |')
        lines.append('|---|---|---|')
        for cat, vals in sorted(by_cat.items()):
            lines.append(f'| {cat} | {sum(1 for v in vals if v)} | {len(vals)} |')
        lines.append('')
        lines.append('## Per-example')
        lines.append('')
        for r in results:
            mark = '✅' if r['pass'] else '❌'
            lines.append(f'### {mark} `{r["id"]}` {r["title"]}')
            lines.append(f'- Technique: `{r["technique"]}`')
            lines.append(f'- Bot reply: > {r["response"][:300]}{"..." if len(r["response"]) > 300 else ""}')
            if r['matched']:
                lines.append(f'- Pass signals matched: `{", ".join(r["matched"])}`')
            if r['banned_hits']:
                lines.append(f'- ⚠️ Banned phrases detected: `{", ".join(r["banned_hits"])}`')
            if r.get('error'):
                lines.append(f'- Error: `{r["error"]}`')
            lines.append('')
        with open(path, 'w') as f:
            f.write('\n'.join(lines))
