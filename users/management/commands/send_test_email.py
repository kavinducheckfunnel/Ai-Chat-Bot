"""Quick SMTP smoke-test.

Usage:
    python manage.py send_test_email recipient@example.com

If SMTP is misconfigured (wrong host/port/auth), this command exits non-zero
with the actual error — unlike the forgot-password view which used to swallow
failures silently. Run this after any infra change to verify mail still works.
"""
from django.core.management.base import BaseCommand, CommandError
from django.core.mail import EmailMultiAlternatives
from django.conf import settings


class Command(BaseCommand):
    help = 'Send a one-line test email via the configured SMTP backend.'

    def add_arguments(self, parser):
        parser.add_argument('to', help='Recipient email address')

    def handle(self, *args, **opts):
        to = opts['to']
        self.stdout.write(f'Sending test email to {to} via {settings.EMAIL_HOST}:{settings.EMAIL_PORT}…')
        try:
            msg = EmailMultiAlternatives(
                subject='Checkfunnel SMTP test',
                body='If you can read this, SMTP works.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[to],
            )
            msg.attach_alternative(
                '<p>If you can read this, <strong>SMTP works</strong>.</p>',
                'text/html',
            )
            msg.send(fail_silently=False)
        except Exception as e:
            raise CommandError(f'Email send failed: {e}')
        self.stdout.write(self.style.SUCCESS(f'OK — email queued to {to}'))
