import requests
import json
from bs4 import BeautifulSoup
from langchain.text_splitter import RecursiveCharacterTextSplitter
from .models import DocumentChunk
from .embeddings import batch_embed_texts

def clean_html(html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    return soup.get_text(separator=" ", strip=True)

def fetch_wordpress_data(site_url):
    """
    Fetches posts or products from the WordPress REST API.
    Handles pagination.
    """
    api_url = f"{site_url.rstrip('/')}/wp-json/wp/v2/posts"
    all_posts = []
    page = 1
    per_page = 100
    
    while True:
        try:
            response = requests.get(api_url, params={'per_page': per_page, 'page': page}, timeout=10)
            if response.status_code != 200:
                print(f"Failed to fetch from {api_url}: {response.status_code}")
                break
            
            data = response.json()
            if not data:
                break
                
            all_posts.extend(data)
            page += 1
        except Exception as e:
            print(f"Error fetching data: {e}")
            break
            
    return all_posts

def process_and_store_website_data(site_url):
    posts = fetch_wordpress_data(site_url)
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=100,
        separators=["\n\n", "\n", " ", ""]
    )
    
    chunks_to_embed = []
    metadata_list = []
    
    for post in posts:
        title = post.get('title', {}).get('rendered', '')
        content_html = post.get('content', {}).get('rendered', '')
        content_text = clean_html(content_html)
        link = post.get('link', '')
        post_id = post.get('id')
        
        full_text = f"Title: {title}\n\n{content_text}"
        
        split_texts = text_splitter.split_text(full_text)
        for text in split_texts:
            chunks_to_embed.append(text)
            metadata_list.append({
                'source_url': link,
                'product_id': post_id,
                'metadata': {
                    'title': title,
                    'type': 'post'
                }
            })
            
    if chunks_to_embed:
        # Batch size handling (e.g. 100 max per request usually for APIs)
        batch_size = 100
        all_embeddings = []
        for i in range(0, len(chunks_to_embed), batch_size):
            batch_texts = chunks_to_embed[i:i+batch_size]
            batch_embs = batch_embed_texts(batch_texts)
            all_embeddings.extend(batch_embs)
            
        # Bulk create DocumentChunks
        docs_to_create = []
        for i in range(len(chunks_to_embed)):
            emb = all_embeddings[i]
            # Since we set pgvector dimensions=1536 but gemini might return 768 by default
            # Actually, let's pad vectors to 1536 if gemini returns 768. 
            # Or pass task_type="RETRIEVAL_DOCUMENT" etc. Wait, we should just let it be stored.
            if len(emb) < 1536:
                emb = emb + [0.0] * (1536 - len(emb))
            elif len(emb) > 1536:
                emb = emb[:1536]
                
            meta_info = metadata_list[i]
            docs_to_create.append(
                DocumentChunk(
                    content=chunks_to_embed[i],
                    embedding=emb,
                    source_url=meta_info['source_url'],
                    product_id=meta_info['product_id'],
                    metadata=meta_info['metadata']
                )
            )
            
        DocumentChunk.objects.bulk_create(docs_to_create)
        print(f"Successfully processed and stored {len(docs_to_create)} chunks.")
    else:
        print("No content to process.")
