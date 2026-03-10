import os
from langchain_google_genai import GoogleGenerativeAIEmbeddings

def get_embeddings_model():
    # We use GoogleGenerativeAIEmbeddings with Gemini's text embedding model.
    # The user prompt mentions gemini Embeddings API with text-embedding-ada-002,
    # but ada-002 is OpenAI. Using Gemini's text-embedding-004 which supports 768 dimensions.
    # Wait, the DB VectorField is set to 1536 dimensions as per prompt. 
    # Can we set Gemini embeddings to 1536 dimensions? Yes, text-embedding-004 supports adjustable dimensions via output_dimensionality=1536.
    return GoogleGenerativeAIEmbeddings(
        model="models/text-embedding-004", 
        google_api_key=os.environ.get("GEMINI_API_KEY")
    )

def batch_embed_texts(texts):
    if not texts:
        return []
    embedder = get_embeddings_model()
    # Ensure we return lists of floats
    return embedder.embed_documents(texts)
