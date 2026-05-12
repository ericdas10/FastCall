from typing import List

from openai import OpenAI

from app.agent.config import agent_settings


_client: OpenAI | None = None


def get_openai() -> OpenAI:
    """Process-wide OpenAI client (lazy)."""
    global _client
    if _client is None:
        if not agent_settings.OPENAI_API_KEY:
            raise RuntimeError(
                "OPENAI_API_KEY is not set. Add it to the project .env file."
            )
        _client = OpenAI(api_key=agent_settings.OPENAI_API_KEY)
    return _client


def embed_texts(texts: List[str]) -> List[List[float]]:
    """Embed a batch of texts with the configured embedding model."""
    if not texts:
        return []
    client = get_openai()
    # The OpenAI embedding API tolerates relatively large batches; we keep
    # it simple here. Empty / whitespace-only inputs are replaced with a
    # single space to avoid API errors.
    cleaned = [t if (t and t.strip()) else " " for t in texts]
    resp = client.embeddings.create(
        model=agent_settings.embedding_model,
        input=cleaned,
    )
    return [d.embedding for d in resp.data]
