"""
tests/conftest.py — Shared pytest fixtures and helpers.
"""

import pytest
import numpy as np


# ── Fake embedding vector (384-dim, all-MiniLM-L6-v2 output dim) ─────────────

EMBED_DIM = 384


def fake_vector(seed: int = 0) -> list[float]:
    rng = np.random.default_rng(seed)
    return rng.random(EMBED_DIM).tolist()


def fake_matrix(n: int) -> list[list[float]]:
    return [fake_vector(i) for i in range(n)]


# ── Minimal config stub ───────────────────────────────────────────────────────

class _Config:
    GROQ_API_KEY      = "test-groq-key"
    GEMINI_API_KEY    = "test-gemini-key"
    LLM_PROVIDER      = "groq"
    LLM_MODEL         = "llama-3.3-70b-versatile"
    EMBEDDING_MODEL   = "all-MiniLM-L6-v2"
    CHROMA_PERSIST_DIR = "/tmp/test_chroma"


@pytest.fixture
def mock_config(monkeypatch):
    """Patch config module with a lightweight stub."""
    import config as cfg_module
    monkeypatch.setattr(cfg_module, "config", _Config())
    return _Config()
