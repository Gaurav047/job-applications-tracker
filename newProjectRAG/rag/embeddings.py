"""Embedding client for the RAG layer.

Uses Voyage AI for real embeddings (Anthropic doesn't offer an embeddings
endpoint itself and recommends Voyage). Set RAG_FAKE_EMBEDDINGS=1 to use a
deterministic offline fallback instead — no network call, no API key —
which is what tests and local dev use by default.

Config is read from backend's own `settings` (backend/.env), not raw
os.environ: pydantic-settings parses .env itself without exporting those
values into the process environment, so a plain os.environ read would
never see VOYAGE_API_KEY when the app is started normally (e.g. via
uvicorn) — only when something has separately exported it into the shell.
"""
import hashlib
from functools import lru_cache

from rag import _pathlink  # noqa: F401
from app.core.config import settings

EMBEDDING_DIM = 1024
VOYAGE_MODEL = "voyage-3.5"


def _fake_embedding(text: str) -> list[float]:
    """Deterministic bag-of-words hashing embedding: texts sharing words
    end up closer in cosine distance than texts that don't. Good enough to
    exercise retrieval ordering in tests/offline dev — not a substitute
    for real embedding quality."""
    vector = [0.0] * EMBEDDING_DIM
    for word in text.lower().split():
        digest = hashlib.sha256(word.encode()).digest()
        index = int.from_bytes(digest[:4], "big") % EMBEDDING_DIM
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign
    norm = sum(v * v for v in vector) ** 0.5
    if norm == 0:
        return vector
    return [v / norm for v in vector]


@lru_cache
def _voyage_client():
    import voyageai

    return voyageai.Client(api_key=settings.voyage_api_key)


def _use_fake() -> bool:
    return settings.rag_fake_embeddings


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embeds a batch of documents (resume bullets, job posting chunks)."""
    if not texts:
        return []
    if _use_fake():
        return [_fake_embedding(t) for t in texts]
    result = _voyage_client().embed(texts, model=VOYAGE_MODEL, input_type="document")
    return result.embeddings


def embed_query(text: str) -> list[float]:
    """Embeds a search query. Voyage encodes queries and documents
    differently, so this is a separate call, not just embed_texts([text])[0]."""
    if _use_fake():
        return _fake_embedding(text)
    result = _voyage_client().embed([text], model=VOYAGE_MODEL, input_type="query")
    return result.embeddings[0]
