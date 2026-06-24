from django.db import models
from pgvector.django import VectorField, HnswIndex
from users.models import Client

class DocumentChunk(models.Model):
    id = models.BigAutoField(primary_key=True)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='documents', null=True, blank=True)
    content = models.TextField()
    embedding = VectorField(dimensions=1024)
    source_url = models.URLField(max_length=1000)
    product_id = models.CharField(max_length=100, null=True, blank=True)
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            # ANN index for RAG: without it every chat turn does a full
            # sequential scan computing cosine distance for every chunk. HNSW
            # gives sub-linear nearest-neighbour lookups (cosine opclass).
            HnswIndex(
                name='docchunk_embedding_hnsw',
                fields=['embedding'],
                m=16,
                ef_construction=64,
                opclasses=['vector_cosine_ops'],
            ),
            models.Index(fields=['client'], name='docchunk_client_idx'),
        ]

    def __str__(self):
        return f"Chunk {self.id} from {self.source_url}"


class WebhookEvent(models.Model):
    """
    Audit log of every incoming sync webhook (Shopify/WooCommerce/WordPress).

    Powers two things in the portal:
      1) the "Webhook activity" list under Settings → Knowledge so tenants
         can verify their CMS is actually pushing changes to us
      2) the superadmin diagnostic view — see who's wired up real-time sync
         vs who is still relying on the daily periodic crawl

    Created in views.py when a webhook arrives, then updated to DONE / FAILED
    by the re_embed_* Celery task once the embedding work finishes.
    """
    SOURCE_CHOICES = [
        ('shopify',     'Shopify'),
        ('woocommerce', 'WooCommerce'),
        ('wordpress',   'WordPress'),
    ]
    STATUS_CHOICES = [
        ('queued', 'Queued'),
        ('done',   'Done'),
        ('failed', 'Failed'),
    ]

    id           = models.BigAutoField(primary_key=True)
    client       = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='webhook_events')
    source       = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    # Free-form event label from the CMS: e.g. 'product.updated', 'post.created'
    event_type   = models.CharField(max_length=60, blank=True)
    # CMS-side id of the resource (product_id / post_id)
    resource_id  = models.CharField(max_length=64, blank=True, db_index=True)
    resource_title = models.CharField(max_length=300, blank=True)
    status       = models.CharField(max_length=20, choices=STATUS_CHOICES, default='queued')
    error_message = models.TextField(blank=True)
    duration_ms  = models.IntegerField(null=True, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes  = [models.Index(fields=['client', '-created_at'])]

    def __str__(self):
        return f'{self.source} {self.event_type} {self.resource_id} → {self.status}'
