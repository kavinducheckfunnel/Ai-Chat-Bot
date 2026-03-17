import os
import json
import boto3


def _get_bedrock_client():
    return boto3.client(
        service_name='bedrock-runtime',
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
        region_name=os.environ.get("AWS_DEFAULT_REGION", "us-west-2"),
    )


class TitanEmbeddings:
    """Amazon Titan Embed Text v2 — 1024 dims, no Marketplace subscription needed."""

    def embed_query(self, text: str) -> list:
        client = _get_bedrock_client()
        body = json.dumps({"inputText": text, "dimensions": 1024, "normalize": True})
        resp = client.invoke_model(
            modelId="amazon.titan-embed-text-v2:0",
            body=body,
            contentType="application/json",
            accept="application/json",
        )
        return json.loads(resp['body'].read())['embedding']

    def embed_documents(self, texts: list) -> list:
        return [self.embed_query(t) for t in texts]


def get_embeddings_model():
    return TitanEmbeddings()


def batch_embed_texts(texts):
    if not texts:
        return []
    embedder = get_embeddings_model()
    return embedder.embed_documents(texts)
