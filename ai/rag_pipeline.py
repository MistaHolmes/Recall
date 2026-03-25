"""
ai/rag_pipeline.py — PDF ingestion + ChromaDB retrieval
"""

import logging
import hashlib
import chromadb
from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter
from PyPDF2 import PdfReader
from ai.embeddings import embed, embed_one
from config import config

log = logging.getLogger("rag")

_client = chromadb.PersistentClient(path=config.CHROMA_PERSIST_DIR)

CHUNK_SIZE = 512
CHUNK_OVERLAP = 64
TOP_K = 5

_splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
    separators=[r"Section \d+", r"Article \d+", "\n\n", "\n", " ", ""],
)


def _collection(guild_id: int):
    return _client.get_or_create_collection(
        name=f"guild_{guild_id}",
        metadata={"hnsw:space": "cosine"},
    )


def ingest_pdf(guild_id: int, file_path: str, filename: str) -> int:
    """
    Ingest a PDF into ChromaDB for the given guild.
    Returns the number of chunks stored.
    """
    reader = PdfReader(file_path)
    col = _collection(guild_id)

    all_docs, all_ids, all_meta, all_embeddings = [], [], [], []

    for page_num, page in enumerate(reader.pages, start=1):
        text = page.extract_text()
        if not text or not text.strip():
            log.warning(f"Skipping empty page {page_num} in {filename}")
            continue

        chunks = _splitter.split_text(text)
        for i, chunk in enumerate(chunks):
            chunk_id = hashlib.md5(f"{filename}_p{page_num}_{i}".encode()).hexdigest()
            all_docs.append(chunk)
            all_ids.append(chunk_id)
            all_meta.append({"filename": filename, "page": page_num, "guild_id": guild_id})

    if not all_docs:
        return 0

    # Embed all chunks in one batch
    all_embeddings = embed(all_docs)

    col.upsert(
        documents=all_docs,
        ids=all_ids,
        metadatas=all_meta,
        embeddings=all_embeddings,
    )

    log.info(f"Ingested {len(all_docs)} chunks from {filename} into guild {guild_id}")
    return len(all_docs)


def query(guild_id: int, question: str) -> dict:
    """
    Query ChromaDB with a question, return answer context and citations.
    Raises RuntimeError if no materials have been uploaded.
    """
    col = _collection(guild_id)
    if col.count() == 0:
        raise RuntimeError("No course materials uploaded yet. Use /upload to add a PDF.")

    q_embedding = embed_one(question)
    results = col.query(
        query_embeddings=[q_embedding],
        n_results=min(TOP_K, col.count()),
        include=["documents", "metadatas", "distances"],
    )

    docs = results["documents"][0]
    metas = results["metadatas"][0]

    context_parts = []
    citations = []
    seen = set()

    for doc, meta in zip(docs, metas):
        context_parts.append(f"[Source: {meta['filename']} p.{meta['page']}]\n{doc}")
        cite = f"{meta['filename']} (p.{meta['page']})"
        if cite not in seen:
            citations.append(cite)
            seen.add(cite)

    return {
        "context": "\n\n---\n\n".join(context_parts),
        "citations": citations,
    }


def list_files(guild_id: int) -> list[str]:
    """Return unique filenames ingested for this guild."""
    col = _collection(guild_id)
    if col.count() == 0:
        return []
    results = col.get(include=["metadatas"])
    seen = set()
    files = []
    for m in results["metadatas"]:
        if m["filename"] not in seen:
            files.append(m["filename"])
            seen.add(m["filename"])
    return files


def delete_guild_collection(guild_id: int):
    """Remove all stored material for a guild."""
    try:
        _client.delete_collection(f"guild_{guild_id}")
    except Exception:
        pass
