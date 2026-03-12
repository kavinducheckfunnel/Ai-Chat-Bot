from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from users.models import Client
from scraper.models import DocumentChunk
from scraper.embeddings import batch_embed_texts
from scraper.ingestion import process_single_wordpress_post

# --- REAL-TIME DATA SYNC PIPELINE ---

def regenerate_product_embedding(client, product_id, title, description, price, url):
    """
    Core AI Pipeline: When a webhook fires, this method takes the new live data,
    embeds it using Gemini, and swaps it atomically in the vector database
    so the AI stops hallucinating old prices.
    """
    content = f"Product: {title}\\nPrice: ${price}\\nDescription: {description}"
    
    # Check if we already have an existing chunk for this Product ID
    source_url_marker = url if url else f"product_{product_id}"
    
    # Delete old stale chunks related to this product for this tenant
    DocumentChunk.objects.filter(client=client, product_id=product_id).delete()
    
    # Generate fresh Gemini vector
    embeddings = batch_embed_texts([content])
    
    if embeddings and len(embeddings) > 0:
        # Save real-time updated knowledge back to DB
        DocumentChunk.objects.create(
            client=client,
            content=content,
            embedding=embeddings[0],
            source_url=source_url_marker,
            product_id=str(product_id)
        )
        return True
    return False


@api_view(['POST'])
@permission_classes([AllowAny])
def shopify_webhook(request, client_id):
    """
    Receives Shopify 'products/update' or 'products/create' webhook.
    """
    client = get_object_or_404(Client, id=client_id)
    
    # In production, verify Shopify HMAC header here
    
    data = request.data
    # Extract native Shopify fields
    product_id = data.get('id')
    title = data.get('title', '')
    description = data.get('body_html', '')
    
    # Grab price from first variant if available
    price = 0.0
    variants = data.get('variants', [])
    if variants:
        price = variants[0].get('price', 0.0)
        
    url = f"https://{client.domain_url}/products/{data.get('handle', '')}"
    
    if product_id and title:
        regenerate_product_embedding(client, product_id, title, description, price, url)
        return Response({"status": "synced"}, status=200)
    
    return Response({"status": "skipped - invalid payload"}, status=400)


@api_view(['POST'])
@permission_classes([AllowAny])
def woocommerce_webhook(request, client_id):
    """
    Receives WooCommerce 'product.updated' webhook.
    """
    client = get_object_or_404(Client, id=client_id)
    
    # In production, verify WooCommerce secret header here
    
    data = request.data
    product_id = data.get('id')
    title = data.get('name', '')
    description = data.get('description', '')
    price = data.get('price', 0.0)
    url = data.get('permalink', '')
    
    if product_id and title:
        regenerate_product_embedding(client, product_id, title, description, price, url)
        return Response({"status": "synced"}, status=200)
        
    return Response({"status": "skipped - invalid payload"}, status=400)


@api_view(['POST'])
@permission_classes([AllowAny])
def wordpress_webhook(request, client_id):
    """
    Receives WordPress Webhook on post creation/update.
    """
    client = get_object_or_404(Client, id=client_id)
    data = request.data
    
    # WordPress usually wraps the post data or sends it directly
    # Adjust based on exact WP webhook plugin payload
    post_data = data.get('post', data)
    
    if post_data and post_data.get('id'):
        result = process_single_wordpress_post(client, post_data)
        if result['status'] == 'success':
            return Response(result, status=200)
        return Response(result, status=400)
        
    return Response({"status": "error", "message": "Invalid WordPress payload"}, status=400)
