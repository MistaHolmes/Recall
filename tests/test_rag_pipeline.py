"""
tests/test_rag_pipeline.py — Unit tests for ai/rag_pipeline.py
Mocks: PyPDF2.PdfReader, chromadb.PersistentClient, ai.embeddings.embed / embed_one
so no file I/O, no model load, and no vector DB on disk are needed.
"""

import pytest
from unittest.mock import MagicMock, patch, call
from conftest import fake_vector, fake_matrix


# ── Shared fixtures ───────────────────────────────────────────────────────────

GUILD_ID  = 123456789
FILENAME  = "test_doc.pdf"
FILE_PATH = "/tmp/test_doc.pdf"


def _make_pdf_reader(pages: list[str]):
    """Build a mock PdfReader with one MockPage per string in `pages`."""
    reader = MagicMock()
    mock_pages = []
    for text in pages:
        page = MagicMock()
        page.extract_text.return_value = text
        mock_pages.append(page)
    reader.pages = mock_pages
    return reader


def _make_chroma_collection(count: int = 0):
    col = MagicMock()
    col.count.return_value = count
    return col


def _make_chroma_client(collection: MagicMock):
    client = MagicMock()
    client.get_or_create_collection.return_value = collection
    return client


# ── ingest_pdf() ──────────────────────────────────────────────────────────────

class TestIngestPdf:
    def _run_ingest(self, pages: list[str], chunk_count_per_page: int = 1):
        """Helper that patches all I/O and runs ingest_pdf()."""
        collection = _make_chroma_collection()
        chroma_client = _make_chroma_client(collection)

        pdf_reader = _make_pdf_reader(pages)
        n_total = len(pages) * chunk_count_per_page
        fake_embeddings = fake_matrix(n_total)

        with patch("ai.rag_pipeline._client", chroma_client), \
             patch("ai.rag_pipeline.PdfReader", return_value=pdf_reader), \
             patch("ai.rag_pipeline.embed", return_value=fake_embeddings) as mock_embed, \
             patch("ai.rag_pipeline._splitter") as mock_splitter:

            # Each page produces `chunk_count_per_page` chunks equal to the page text
            mock_splitter.split_text.side_effect = lambda t: [t] * chunk_count_per_page

            from ai.rag_pipeline import ingest_pdf
            count = ingest_pdf(GUILD_ID, FILE_PATH, FILENAME)

        return count, collection, mock_embed

    def test_returns_chunk_count(self):
        count, _, _ = self._run_ingest(["Page one text", "Page two text"])
        assert count == 2   # 2 pages × 1 chunk each

    def test_upsert_called_once(self):
        _, collection, _ = self._run_ingest(["Page one", "Page two"])
        collection.upsert.assert_called_once()

    def test_upsert_receives_correct_number_of_docs(self):
        _, collection, _ = self._run_ingest(["P1", "P2", "P3"])
        kwargs = collection.upsert.call_args[1]
        assert len(kwargs["documents"]) == 3

    def test_metadata_contains_filename_and_page(self):
        _, collection, _ = self._run_ingest(["Page A"])
        kwargs = collection.upsert.call_args[1]
        meta = kwargs["metadatas"][0]
        assert meta["filename"] == FILENAME
        assert meta["page"] == 1
        assert meta["guild_id"] == GUILD_ID

    def test_chunk_ids_are_unique(self):
        _, collection, _ = self._run_ingest(["A", "B", "C"])
        kwargs = collection.upsert.call_args[1]
        ids = kwargs["ids"]
        assert len(ids) == len(set(ids)), "chunk IDs must be unique"

    def test_skips_empty_pages(self):
        count, collection, _ = self._run_ingest(["Good content", "", "   "])
        # Only one page has real text
        kwargs = collection.upsert.call_args[1]
        assert len(kwargs["documents"]) == 1

    def test_embed_called_with_all_chunks(self):
        _, _, mock_embed = self._run_ingest(["Chunk one", "Chunk two"])
        args = mock_embed.call_args[0][0]
        assert len(args) == 2

    def test_returns_zero_for_empty_pdf(self):
        count, collection, _ = self._run_ingest(["", "  "])
        assert count == 0
        collection.upsert.assert_not_called()


# ── query() ───────────────────────────────────────────────────────────────────

class TestQuery:
    def _make_query_results(self, docs, pages, filename=FILENAME):
        metas = [{"filename": filename, "page": p} for p in pages]
        return {
            "documents": [docs],
            "metadatas": [metas],
            "distances": [[0.1] * len(docs)],
        }

    def test_raises_when_collection_empty(self):
        collection = _make_chroma_collection(count=0)
        chroma_client = _make_chroma_client(collection)

        with patch("ai.rag_pipeline._client", chroma_client), \
             patch("ai.rag_pipeline.embed_one", return_value=fake_vector()):
            from ai.rag_pipeline import query
            with pytest.raises(RuntimeError, match="No course materials"):
                query(GUILD_ID, "some question")

    def test_returns_context_and_citations(self):
        collection = _make_chroma_collection(count=3)
        chroma_client = _make_chroma_client(collection)
        collection.query.return_value = self._make_query_results(
            ["chunk A", "chunk B"], [4, 11]
        )

        with patch("ai.rag_pipeline._client", chroma_client), \
             patch("ai.rag_pipeline.embed_one", return_value=fake_vector()):
            from ai.rag_pipeline import query
            result = query(GUILD_ID, "what is HPA?")

        assert "context" in result
        assert "citations" in result

    def test_context_includes_source_label(self):
        collection = _make_chroma_collection(count=2)
        chroma_client = _make_chroma_client(collection)
        collection.query.return_value = self._make_query_results(
            ["relevant text"], [7]
        )

        with patch("ai.rag_pipeline._client", chroma_client), \
             patch("ai.rag_pipeline.embed_one", return_value=fake_vector()):
            from ai.rag_pipeline import query
            result = query(GUILD_ID, "question")

        assert FILENAME in result["context"]
        assert "p.7" in result["context"]

    def test_citations_deduplicated(self):
        """Two chunks from the same page should produce only one citation entry."""
        collection = _make_chroma_collection(count=4)
        chroma_client = _make_chroma_client(collection)
        collection.query.return_value = self._make_query_results(
            ["chunk1", "chunk2"], [5, 5]   # same page for both
        )

        with patch("ai.rag_pipeline._client", chroma_client), \
             patch("ai.rag_pipeline.embed_one", return_value=fake_vector()):
            from ai.rag_pipeline import query
            result = query(GUILD_ID, "q")

        assert len(result["citations"]) == 1

    def test_embed_one_called_with_question(self):
        collection = _make_chroma_collection(count=1)
        chroma_client = _make_chroma_client(collection)
        collection.query.return_value = self._make_query_results(["text"], [1])

        with patch("ai.rag_pipeline._client", chroma_client), \
             patch("ai.rag_pipeline.embed_one", return_value=fake_vector()) as mock_emb:
            from ai.rag_pipeline import query
            query(GUILD_ID, "my question")

        mock_emb.assert_called_once_with("my question")
