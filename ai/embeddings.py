"""
ai/embeddings.py — Local sentence-transformer embeddings (no API cost)
"""

import logging
from functools import lru_cache
from config import config

log = logging.getLogger("embeddings")


@lru_cache(maxsize=1)
def _get_model():
    from sentence_transformers import SentenceTransformer
    log.info(f"Loading embedding model: {config.EMBEDDING_MODEL}")
    return SentenceTransformer(config.EMBEDDING_MODEL)


def preload_model() -> None:
    """Eagerly load the embedding model (call from a thread at startup).

    The first call to SentenceTransformer() downloads / loads weights and
    can block for several seconds.  By running this in an executor during
    setup_hook() the event loop stays responsive for incoming interactions.
    """
    _get_model()


def embed(texts: list[str]) -> list[list[float]]:
    """Embed a list of strings, return list of float vectors."""
    model = _get_model()
    return model.encode(texts, convert_to_numpy=True).tolist()


def embed_one(text: str) -> list[float]:
    return embed([text])[0]
