"""
vector_store.py â€” ChromaDB integration for YOWON AI.

Stores project context documents as vector embeddings so agents can
retrieve semantically-relevant snippets rather than reading the entire
raw context every time.

Collections:
  - yowon_projects  (one document per project)
"""

from __future__ import annotations


import chromadb
from chromadb.config import Settings

from config import CHROMA_DIR, CHROMA_COLLECTION_NAME


# â”€â”€ Singleton client â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
_client = None


def _get_client():
    global _client
    if _client is None:
        from config import CHROMA_HOST, CHROMA_PORT
        if CHROMA_HOST:
            _client = chromadb.HttpClient(
                host=CHROMA_HOST,
                port=CHROMA_PORT,
                settings=Settings(anonymized_telemetry=False),
            )
        else:
            _client = chromadb.PersistentClient(
                path=str(CHROMA_DIR),
                settings=Settings(anonymized_telemetry=False),
            )
    return _client


def _get_collection():
    """Return (or create) the main YOWON AI collection."""
    client = _get_client()
    return client.get_or_create_collection(
        name=CHROMA_COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


# â”€â”€ Public API â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def store_project_context(project_id: str, text: str, metadata: dict | None = None) -> None:
    """
    Upsert a project's context text into ChromaDB.

    Args:
        project_id: UUID string used as the document ID.
        text:       Full flattened project context (from parser.context_to_text).
        metadata:   Optional dict of scalar fields to attach.
    """
    collection = _get_collection()
    collection.upsert(
        ids=[project_id],
        documents=[text],
        metadatas=[metadata or {"project_id": project_id}],
    )


def retrieve_context(project_id: str, query: str, n_results: int = 3) -> list[str]:
    """
    Retrieve the most relevant chunks for a query from this project's context.

    Because each project is stored as a single document, this queries across
    all projects and returns the top matches (useful for cross-project comparison
    in future iterations).

    Args:
        project_id: Used to filter results to this project.
        query:      Natural-language query string.
        n_results:  Number of results to return.

    Returns:
        List of relevant text snippets.
    """
    collection = _get_collection()
    try:
        results = collection.query(
            query_texts=[query],
            n_results=min(n_results, collection.count()),
            where={"project_id": project_id} if project_id else None,
        )
        return results.get("documents", [[]])[0]
    except Exception:
        return []


def delete_project_context(project_id: str) -> None:
    """Remove a project's vectors from ChromaDB."""
    collection = _get_collection()
    try:
        collection.delete(ids=[project_id])
    except Exception:
        pass