from django.db import models
from pgvector.django import VectorField

class DocumentChunk(models.Model):
    id = models.BigAutoField(primary_key=True)
    content = models.TextField()
    embedding = VectorField(dimensions=1536)
    source_url = models.URLField(max_length=1000)
    product_id = models.IntegerField(null=True, blank=True)
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Chunk {self.id} from {self.source_url}"
