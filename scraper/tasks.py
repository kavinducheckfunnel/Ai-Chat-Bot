from celery import shared_task


@shared_task(bind=True, max_retries=2)
def scrape_client_website(self, client_id):
    """Async task to crawl a client's website and ingest document chunks."""
    from users.models import Client
    from scraper.ingestion import fetch_wordpress_data, ingest_documents

    try:
        client = Client.objects.get(pk=client_id)
    except Client.DoesNotExist:
        return

    try:
        if client.platform == 'WORDPRESS':
            documents = fetch_wordpress_data(client.domain_url)
        else:
            # Generic crawl fallback
            documents = fetch_wordpress_data(client.domain_url)

        count = ingest_documents(client, documents)

        client.ingestion_status = 'DONE'
        client.total_pages_ingested = count
        client.save(update_fields=['ingestion_status', 'total_pages_ingested'])

    except Exception as exc:
        client.ingestion_status = 'FAILED'
        client.save(update_fields=['ingestion_status'])
        raise self.retry(exc=exc, countdown=60)
