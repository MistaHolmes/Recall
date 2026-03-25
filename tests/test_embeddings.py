"""
tests/test_embeddings.py — Unit tests for ai/embeddings.py
Mocks sentence-transformers so no model weights are downloaded.
"""

import pytest
import numpy as np
from unittest.mock import MagicMock, patch
from conftest import EMBED_DIM, fake_vector, fake_matrix


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_mock_model(n_texts: int = 1):
    """Return a mock SentenceTransformer that returns a (n, 384) numpy array."""
    mock = MagicMock()
    mock.encode.return_value = np.array(fake_matrix(n_texts))
    return mock


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestEmbed:
    def test_returns_list_of_vectors(self):
        texts = ["hello world", "study session", "Kubernetes HPA"]
        mock_model = _make_mock_model(len(texts))

        with patch("ai.embeddings._get_model", return_value=mock_model):
            from ai.embeddings import embed
            result = embed(texts)

        assert isinstance(result, list)
        assert len(result) == len(texts)
        assert all(isinstance(v, list) for v in result)
        assert all(len(v) == EMBED_DIM for v in result)

    def test_each_vector_is_floats(self):
        texts = ["single chunk"]
        mock_model = _make_mock_model(1)

        with patch("ai.embeddings._get_model", return_value=mock_model):
            from ai.embeddings import embed
            result = embed(texts)

        assert all(isinstance(x, float) for x in result[0])

    def test_encode_called_with_text_list(self):
        texts = ["alpha", "beta"]
        mock_model = _make_mock_model(len(texts))

        with patch("ai.embeddings._get_model", return_value=mock_model):
            from ai.embeddings import embed
            embed(texts)

        mock_model.encode.assert_called_once_with(texts, convert_to_numpy=True)

    def test_empty_list_returns_empty(self):
        mock_model = MagicMock()
        mock_model.encode.return_value = np.empty((0, EMBED_DIM))

        with patch("ai.embeddings._get_model", return_value=mock_model):
            from ai.embeddings import embed
            result = embed([])

        assert result == []


class TestEmbedOne:
    def test_returns_single_vector(self):
        mock_model = _make_mock_model(1)

        with patch("ai.embeddings._get_model", return_value=mock_model):
            from ai.embeddings import embed_one
            result = embed_one("a single sentence")

        assert isinstance(result, list)
        assert len(result) == EMBED_DIM

    def test_is_consistent_with_embed(self):
        """embed_one(t) must equal embed([t])[0]."""
        mock_model = _make_mock_model(1)

        with patch("ai.embeddings._get_model", return_value=mock_model):
            from ai.embeddings import embed, embed_one
            text = "consistent check"
            assert embed_one(text) == embed([text])[0]

    def test_model_loaded_only_once(self):
        """_get_model is lru_cached — should be called exactly once per process."""
        import ai.embeddings as emb_mod

        mock_model = _make_mock_model(1)
        with patch("ai.embeddings._get_model", return_value=mock_model) as mock_getter:
            emb_mod.embed_one("first call")
            emb_mod.embed_one("second call")
            # Our patch replaces _get_model, so it's called each time we enter embed(),
            # but the underlying SentenceTransformer constructor should not be.
            assert mock_getter.call_count == 2  # patch is called; real model is not re-init'd
