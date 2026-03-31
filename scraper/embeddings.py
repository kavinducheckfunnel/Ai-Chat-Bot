from sentence_transformers import SentenceTransformer

_model = None


def _get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer('BAAI/bge-large-en-v1.5')
    return _model


class LocalEmbeddings:
    """BAAI/bge-large-en-v1.5 — 1024 dims, runs locally, zero API cost."""

    def embed_query(self, text: str) -> list:
        model = _get_model()
        return model.encode(text, normalize_embeddings=True).tolist()

    def embed_documents(self, texts: list) -> list:
        model = _get_model()
        return model.encode(texts, normalize_embeddings=True).tolist()


def get_embeddings_model():
    return LocalEmbeddings()


def batch_embed_texts(texts):
    if not texts:
        return []
    embedder = get_embeddings_model()
    return embedder.embed_documents(texts)
