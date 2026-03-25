from django.core.management.base import BaseCommand
from users.models import Client
from scraper.ingestion import auto_scrape, ingest_documents, clean_html


class Command(BaseCommand):
    help = 'Re-scrape and re-embed all content for a client by domain URL'

    def add_arguments(self, parser):
        parser.add_argument('domain', type=str, help='Client domain URL (e.g. https://theaitips.com)')

    def handle(self, *args, **options):
        domain = options['domain'].rstrip('/')

        try:
            client = Client.objects.get(domain_url__icontains=domain.replace('https://', '').replace('http://', ''))
        except Client.MultipleObjectsReturned:
            clients = Client.objects.filter(domain_url__icontains=domain.replace('https://', '').replace('http://', ''))
            self.stdout.write(self.style.WARNING(f'Multiple clients found:'))
            for c in clients:
                self.stdout.write(f'  {c.pk} — {c.name} ({c.domain_url})')
            self.stdout.write('\nRe-run with the exact UUID: python3 manage.py rescrape_client_by_id <uuid>')
            return
        except Client.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'No client found with domain containing: {domain}'))
            return

        self.stdout.write(f'Client: {client.name} ({client.domain_url}) — platform: {client.platform}')
        self.stdout.write('Scraping...')

        documents = auto_scrape(client)
        self.stdout.write(f'Fetched {len(documents)} pages/posts. Now embedding...')

        count = ingest_documents(client, documents)

        client.ingestion_status = 'DONE'
        client.total_pages_ingested = count
        client.save(update_fields=['ingestion_status', 'total_pages_ingested'])

        self.stdout.write(self.style.SUCCESS(f'Done. {count} chunks stored for {client.name}.'))
