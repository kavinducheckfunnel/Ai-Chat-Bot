import requests
import json
from bs4 import BeautifulSoup
from langchain_text_splitters import RecursiveCharacterTextSplitter
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
            # Added headers because some sites block python requests User-Agent
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(api_url, params={'per_page': per_page, 'page': page}, headers=headers, timeout=10)
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

def process_and_store_website_data(site_url, client=None, dry_run=False):
    print(f"Starting crawl of: {site_url}")
    posts = fetch_wordpress_data(site_url)
    print(f"Found {len(posts)} posts/pages.")
    
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
        import time
        # Batch size handling
        batch_size = 1
        all_embeddings = []
        
        if dry_run:
            print(f"DRY RUN: Successfully scraped {len(chunks_to_embed)} chunks from {site_url}.")
            print("First chunk content sample:")
            print("---")
            print(chunks_to_embed[0])
            print("---")
            print("Skipping Gemini Embeddings due to pure-scraping test.")
            return

        print("Generating AWS Bedrock Embeddings...")
        for i in range(0, len(chunks_to_embed), batch_size):
            batch_texts = chunks_to_embed[i:i+batch_size]
            batch_embs = batch_embed_texts(batch_texts)
            all_embeddings.extend(batch_embs)
            print(f"Embedded chunk {i+1} out of {len(chunks_to_embed)}...")
            time.sleep(1.0)  # Avoid AWS Throttling limits
            
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
                    client=client,
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

def process_single_wordpress_post(client, post_data):
    """
    Ingest a single WordPress post from webhook payload.
    post_data should be a dict from the WP REST API representing one post.
    """
    post_id = post_data.get('id')
    if not post_id:
        return {"status": "error", "message": "No post ID provided"}
        
    # 1. Delete old chunks for this post to avoid duplicates on update
    DocumentChunk.objects.filter(client=client, product_id=str(post_id)).delete()
    
    # 2. Extract content
    title = post_data.get('title', {}).get('rendered', '')
    content_html = post_data.get('content', {}).get('rendered', '')
    content_text = clean_html(content_html)
    link = post_data.get('link', '')
    
    full_text = f"Title: {title}\n\n{content_text}"
    
    # 3. Split Text
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=100,
        separators=["\n\n", "\n", " ", ""]
    )
    split_texts = text_splitter.split_text(full_text)
    
    if not split_texts:
        return {"status": "ignored", "message": "Post had no text content"}
        
    # 4. Embed
    import time
    all_embeddings = []
    
    print(f"Generating Bedrock Embeddings for post {post_id}...")
    for text in split_texts:
        batch_embs = batch_embed_texts([text])
        all_embeddings.extend(batch_embs)
        time.sleep(1.0) # Avoid AWS limits
        
    # 5. Save
    docs_to_create = []
    for i, text in enumerate(split_texts):
        emb = all_embeddings[i]
        if len(emb) < 1536:
            emb = emb + [0.0] * (1536 - len(emb))
        elif len(emb) > 1536:
            emb = emb[:1536]
            
        docs_to_create.append(
            DocumentChunk(
                client=client,
                content=text,
                embedding=emb,
                source_url=link,
                product_id=str(post_id),
                metadata={'title': title, 'type': 'post'}
            )
        )
        
    DocumentChunk.objects.bulk_create(docs_to_create)
    return {"status": "success", "message": f"Ingested {len(docs_to_create)} chunks for post {post_id}"}
