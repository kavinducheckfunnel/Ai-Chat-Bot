"""Run the SEC-QA-REF-001 evaluation rubric against the live bot.

Scores 9 sales-enablement areas (Product Knowledge, Recommendation, Budget,
Urgency, Qualification, Lead Capture, Hot Lead, Behavior Triggers, Closing
Ability) with 4 prompts each. Per-prompt scoring is 0-10:

  10 → 0 banned phrases AND ≥1 good signal matched
   8 → 0 banned phrases AND ≥1 good signal matched (LLM hit a weaker signal)
   6 → 0 banned phrases but 0 good signals (acceptable, not impressive)
   3 → 1 banned phrase found (regression-grade fail)
   0 → multiple banned phrases or empty response

Aggregates per area, then overall.

Usage:
    python manage.py run_qa_evaluation --client-id <uuid>
    python manage.py run_qa_evaluation --client-id <uuid> --output report.md
"""

import json
import time
import uuid
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError


FIXTURE_PATH = Path(__file__).resolve().parent.parent.parent / 'qa_fixtures' / 'evaluation_v2_sec_qa_ref_001.json'


def score_response(reply, good_signals, bad_signals):
    """Return (score_0_to_10, matched_good, matched_bad)."""
    if not reply or not reply.strip():
        return 0, [], []
    reply_lower = reply.lower()
    matched_good = [s for s in good_signals if s.lower() in reply_lower]
    matched_bad = [s for s in bad_signals if s.lower() in reply_lower]
    if len(matched_bad) >= 2:
        return 0, matched_good, matched_bad
    if len(matched_bad) == 1:
        return 3, matched_good, matched_bad
    # No banned phrases — score on positive signal coverage
    if len(matched_good) >= 2:
        return 10, matched_good, matched_bad
    if len(matched_good) == 1:
        return 8, matched_good, matched_bad
    # Clean response with no positive signal match — bot is "polite but generic"
    return 6, matched_good, matched_bad


class Command(BaseCommand):
    help = 'Run the SEC-QA-REF-001 9-area sales-enablement evaluation against the live AI pipeline.'

    def add_arguments(self, parser):
        parser.add_argument('--client-id', required=True, help='UUID of the Client to test against')
        parser.add_argument('--output', default='', help='Write a Markdown report to this path')
        parser.add_argument('--area', default='', help='Restrict to one area key (e.g. urgency_understanding)')

    def handle(self, *args, **opts):
        from users.models import Client
        from chat.models import ChatSession
        from chat.ai_service import generate_ai_response

        try:
            client = Client.objects.get(pk=opts['client_id'])
        except Client.DoesNotExist:
            raise CommandError(f'Client {opts["client_id"]} not found')

        with open(FIXTURE_PATH) as f:
            rubric = json.load(f)

        areas = rubric['areas']
        if opts['area']:
            areas = [a for a in areas if a['key'] == opts['area']]
            if not areas:
                raise CommandError(f'No area matched key: {opts["area"]}')

        total_prompts = sum(len(a['prompts']) for a in areas)
        self.stdout.write(self.style.MIGRATE_HEADING(
            f'\nSEC-QA-REF-001 Evaluation against client "{client.name}" — '
            f'{len(areas)} area(s), {total_prompts} prompt(s)\n'
        ))

        results = {}
        t0 = time.time()
        for area in areas:
            area_key = area['key']
            self.stdout.write(self.style.HTTP_INFO(f'\n=== {area["label"]} (previous: {area["previous_score"]}) ==='))
            results[area_key] = {'label': area['label'], 'previous_score': area['previous_score'], 'prompts': []}

            for prompt in area['prompts']:
                session = ChatSession.objects.create(
                    session_id=uuid.uuid4(),
                    client=client,
                    visitor_id=f'qa_eval_{prompt["id"]}',
                    chat_history=[],
                )
                for turn in prompt.get('conversation', []):
                    session.chat_history.append({'role': turn['role'], 'message': turn['content']})
                session.save()

                try:
                    ai = generate_ai_response(session, prompt['message'], behavior_matrix={}) or {}
                    reply = ai.get('reply_text') or ''
                except Exception as e:
                    reply = ''
                    self.stdout.write(self.style.WARNING(f'  [{prompt["id"]}] ERROR: {e}'))
                finally:
                    try: session.delete()
                    except Exception: pass

                score, good, bad = score_response(reply, prompt['good_signals'], prompt['bad_signals'])
                tag = self.style.SUCCESS(f'{score:>4.1f}/10') if score >= 8 else (self.style.WARNING(f'{score:>4.1f}/10') if score >= 6 else self.style.ERROR(f'{score:>4.1f}/10'))
                self.stdout.write(f'  [{prompt["id"]}] {tag}  "{prompt["message"][:50]}"')
                if bad:
                    self.stdout.write(self.style.ERROR(f'         banned: {bad}'))
                results[area_key]['prompts'].append({
                    'id': prompt['id'],
                    'message': prompt['message'],
                    'reply': reply,
                    'score': score,
                    'matched_good': good,
                    'matched_bad': bad,
                })

            avg = sum(p['score'] for p in results[area_key]['prompts']) / max(1, len(results[area_key]['prompts']))
            results[area_key]['avg'] = avg
            self.stdout.write(self.style.MIGRATE_HEADING(f'  → {area["label"]} area avg: {avg:.1f}/10'))

        elapsed = time.time() - t0
        total = sum(r['avg'] * 10 for r in results.values()) / max(1, len(results))
        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_HEADING('═' * 60))
        self.stdout.write(self.style.MIGRATE_HEADING(f' OVERALL SALES ENABLEMENT SCORE: {total:.1f}/100   ({elapsed:.0f}s)'))
        self.stdout.write(self.style.MIGRATE_HEADING(f' (Previous SEC-QA-REF-001 baseline: 55/100)'))
        self.stdout.write(self.style.MIGRATE_HEADING('═' * 60))

        if opts['output']:
            _write_markdown(opts['output'], client, results, total, elapsed, rubric)
            self.stdout.write(self.style.SUCCESS(f'\nReport written to {opts["output"]}'))


def _write_markdown(path, client, results, total, elapsed, rubric):
    lines = []
    lines.append(f'# SEC-QA-REF-001 Evaluation Report — {client.name}')
    lines.append('')
    lines.append(f'**Overall: {total:.1f}/100**  ({elapsed:.0f}s, previous baseline 55/100)')
    lines.append('')
    lines.append('## Area scores')
    lines.append('')
    lines.append('| Area | Score | Previous | Delta |')
    lines.append('|---|---|---|---|')
    for area_key, r in results.items():
        prev_num = float(r['previous_score'].split('/')[0]) if '/' in r['previous_score'] else 0
        delta = r['avg'] - prev_num
        delta_str = f'+{delta:.1f}' if delta >= 0 else f'{delta:.1f}'
        lines.append(f'| {r["label"]} | {r["avg"]:.1f}/10 | {r["previous_score"]} | {delta_str} |')
    lines.append('')
    lines.append('## Per-prompt detail')
    lines.append('')
    for area_key, r in results.items():
        lines.append(f'### {r["label"]} — {r["avg"]:.1f}/10')
        lines.append('')
        for p in r['prompts']:
            mark = '✅' if p['score'] >= 8 else ('🟡' if p['score'] >= 6 else '🔴')
            lines.append(f'**{mark} `{p["id"]}` — {p["score"]:.1f}/10**')
            lines.append(f'- Visitor: "{p["message"]}"')
            lines.append(f'- Bot: > {p["reply"][:400]}{"..." if len(p["reply"]) > 400 else ""}')
            if p['matched_good']:
                lines.append(f'- ✅ Good signals: `{", ".join(p["matched_good"])}`')
            if p['matched_bad']:
                lines.append(f'- 🚨 Banned phrases: `{", ".join(p["matched_bad"])}`')
            lines.append('')
    with open(path, 'w') as f:
        f.write('\n'.join(lines))
