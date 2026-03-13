from django.db import models
from pgvector.django import VectorField
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

    def __str__(self):
        return f"Chunk {self.id} from {self.source_url}"
