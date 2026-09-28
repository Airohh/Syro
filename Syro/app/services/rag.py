"""Indexation (chunks → SQLite + Qdrant) et point d'entrée du retrieval."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from ..config import settings
from ..db import db_session
from .bm25_search import bm25_search
from .chunker import chunk_text_hierarchical
from .hybrid_search import hybrid_search
from .llm import get_document_embeddings
from .vector_store import VectorStore, VectorStoreError

if TYPE_CHECKING:
    import numpy as np

logger = logging.getLogger(__name__)


def index_document(
    document_id: int,
    organization_id: int,
    text: str,
    *,
    domain: str,
    filename: str,
) -> int:
    """Découpe, embedde et indexe un document. Tout-ou-rien.

    Les embeddings sont calculés AVANT d'ouvrir la transaction SQLite (étape
    lente, réseau). Ensuite, dans une même transaction : remplacement des
    chunks SQLite + upsert Qdrant. Si Qdrant échoue, la transaction est
    annulée et l'exception remonte → le document passe en `failed` (et le
    worker Celery retente) au lieu d'être marqué `complete` sans vecteurs.
    """
    chunks = chunk_text_hierarchical(
        text,
        chunk_size=settings.chunk_size_tokens,
        overlap=settings.chunk_overlap_tokens,
    )
    if not chunks:
        raise ValueError("Aucun chunk produit (document vide ?)")

    embeddings = get_document_embeddings([c["text"] for c in chunks])
    store = VectorStore()

    try:
        with db_session() as conn:
            conn.execute("DELETE FROM doc_chunks WHERE document_id = ?", (document_id,))
            points = []
            for chunk in chunks:
                cur = conn.execute(
                    "INSERT INTO doc_chunks (document_id, chunk_index, text) VALUES (?, ?, ?)",
                    (document_id, chunk["index"], chunk["text"]),
                )
                points.append(
                    {
                        "id": cur.lastrowid,
                        "text": chunk["text"],
                        "payload": {
                            "organization_id": organization_id,
                            "document_id": document_id,
                            "domain": domain,
                            "filename": filename,
                            "chunk_index": chunk["index"],
                            "header": chunk.get("header", ""),
                        },
                    }
                )
            store.delete_document(document_id)
            store.upsert_chunks(points, embeddings)
    except VectorStoreError:
        # Transaction SQLite annulée ; on retire d'éventuels points partiels.
        try:
            store.delete_document(document_id)
        except VectorStoreError:
            pass
        raise

    bm25_search.mark_for_rebuild(organization_id)
    if settings.enable_semantic_cache:
        from .semantic_cache import semantic_cache

        semantic_cache.invalidate_organization(organization_id)
    return len(chunks)


def retrieve_chunks_with_metadata(
    organization_id: int,
    query: str,
    top_k: int | None = None,
    filters: dict[str, Any] | None = None,
    domain: str | None = None,
    allowed_document_ids: frozenset[int] | None = None,
    history: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Retrieval complet : cache sémantique → (décomposition | CRAG | hybride).

    `domain` None ou "general" = recherche dans tous les documents autorisés.
    """
    if top_k is None:
        top_k = settings.rerank_top_k

    query_embedding: np.ndarray | None = None
    cache_version = None
    if settings.enable_semantic_cache:
        try:
            from .llm import get_embedding_vector
            from .semantic_cache import semantic_cache

            query_embedding = get_embedding_vector(query)
            cache_version = bm25_search.content_fingerprint(organization_id)
            cached, _ = semantic_cache.lookup_retrieval(
                organization_id,
                query,
                query_embedding,
                domain=domain,
                allowed_document_ids=allowed_document_ids,
                filters=filters,
                history=history,
                version=cache_version,
            )
            if cached is not None:
                return cached[:top_k]
        except Exception as exc:
            logger.debug("Semantic cache lookup skipped: %s", exc)

    kwargs = dict(
        organization_id=organization_id,
        query=query,
        top_k=top_k,
        filters=filters,
        domain=domain,
        allowed_document_ids=allowed_document_ids,
        history=history,
        query_embedding=query_embedding,
    )
    if settings.enable_query_decomposition:
        from .decompose import retrieve_decomposed

        results = retrieve_decomposed(**kwargs)
    elif settings.enable_crag:
        from .crag import retrieve_with_crag

        results = retrieve_with_crag(**kwargs)
    else:
        results = hybrid_search(**kwargs)

    if query_embedding is not None and results:
        try:
            from .semantic_cache import semantic_cache

            semantic_cache.store_retrieval(
                organization_id,
                query,
                query_embedding,
                results,
                domain=domain,
                allowed_document_ids=allowed_document_ids,
                filters=filters,
                history=history,
                version=cache_version,
            )
        except Exception as exc:
            logger.debug("Semantic cache store skipped: %s", exc)
    return results
