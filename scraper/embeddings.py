import os
from langchain_aws import BedrockEmbeddings

def get_embeddings_model():
    return BedrockEmbeddings(
        model_id="cohere.embed-english-v3",
        region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
    )

def batch_embed_texts(texts):
    if not texts:
        return []
    embedder = get_embeddings_model()
    # Ensure we return lists of floats
    return embedder.embed_documents(texts)
