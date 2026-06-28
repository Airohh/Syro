"""RAG service with hybrid search and Qdrant integration."""

from __future__ import annotations

import logging
import time
from typing import Any, Sequence

from ..db import db_session
from ..config import settings

logger = logging.getLogger(__name__)
from .llm import get_embedding_vector
from .vector_store import VectorStore, VectorStoreError
from .hybrid_search import hybrid_search
from .chunker import chunk_text_hierarchical
from .bm25_search import bm25_search
from .mlops_tracker import get_mlops_tracker
from .domain_detector import detect_domain_from_document

def index_document_content(
    document_id: int,
    organization_id: int,
    text_content: str,
    metadata: dict[str, Any] | None = None,
) -> int:
    start_time = time.time()
    
    detected_domain = detect_domain_from_document(text_content)
    if metadata and "domain" in metadata:
        detected_domain = metadata["domain"]
    
    chunk_data = chunk_text_hierarchical(
        text_content,
        chunk_size=400,
        overlap=60,
        respect_headers=True,
    )
    
    vector_store = VectorStore()
    
    try:
        vector_store.delete_chunks_by_document(document_id, domain=detected_domain)
    except VectorStoreError as e:
        logger.warning("Could not delete existing chunks for doc %d: %s", document_id, e)
    
    chunk_payloads: list[dict[str, Any]] = []
    with db_session() as conn:
        conn.execute("DELETE FROM doc_chunks WHERE document_id = ?", (document_id,))

        for chunk_info in chunk_data:
            chunk_text = chunk_info["text"]
            chunk_index = chunk_info["index"]

            chunk_cur = conn.execute(
                "INSERT INTO doc_chunks (document_id, chunk_index, text) VALUES (?, ?, ?)",
                (document_id, chunk_index, chunk_text),
            )
            chunk_id = chunk_cur.lastrowid

            chunk_payloads.append({
                "chunk_id": f"{organization_id}_{document_id}_{chunk_id}",
                "text": chunk_text,
                "metadata": {
                    "chunk_index": chunk_index,
                    "header": chunk_info.get("header", ""),
                    "level": chunk_info.get("level", 0),
                    **(metadata or {}),
                },
            })

    # Indexation Qdrant en un seul lot (embeddings + upsert groupés) après le
    # commit SQLite. En cas d'échec Qdrant, SQLite garde les chunks : on logue
    # le désync (même contrat qu'avant, mais tout-ou-rien côté Qdrant).
    if chunk_payloads:
        try:
            vector_store.add_chunks_batch(
                chunk_payloads,
                organization_id=organization_id,
                document_id=document_id,
                domain=detected_domain,
            )
        except VectorStoreError as e:
            logger.error(
                "Failed to batch-index doc %d (%d chunks) in Qdrant — SQLite/Qdrant out of sync: %s",
                document_id, len(chunk_payloads), e,
            )

    bm25_search.mark_for_rebuild(organization_id)

    if settings.enable_semantic_cache:
        from .semantic_cache import semantic_cache

        semantic_cache.invalidate_domain(organization_id, detected_domain)
    
    tracker = get_mlops_tracker()
    if tracker.enabled:
        ingestion_time_ms = (time.time() - start_time) * 1000
        tracker.log_document_ingestion(
            document_id=document_id,
            organization_id=organization_id,
            num_chunks=len(chunk_data),
            ingestion_time_ms=ingestion_time_ms,
            document_size_chars=len(text_content),
            metadata=metadata,
        )
    
    return len(chunk_data)

def retrieve_chunks_with_metadata(
    organization_id: int,
    query: str,
    top_k: int | None = None,
    filters: dict[str, Any] | None = None,
    use_hybrid: bool = True,
    domain: str | None = None,
    allowed_document_ids: frozenset[int] | None = None,
    history: list[str] | None = None,
) -> list[dict[str, Any]]:
    if top_k is None:
        top_k = settings.rerank_top_k

    query_embedding: np.ndarray | None = None
    if settings.enable_semantic_cache and use_hybrid:
        try:
            from .llm import get_embedding_vector
            from .semantic_cache import semantic_cache

            query_embedding = get_embedding_vector(query)
            cached, status = semantic_cache.lookup_retrieval(
                organization_id,
                query,
                query_embedding,
                domain=domain,
                allowed_document_ids=allowed_document_ids,
                filters=filters,
                history=history,
            )
            if cached is not None:
                return cached[:top_k]
        except Exception as exc:
            logger.debug("Semantic cache lookup skipped: %s", exc)

    if use_hybrid:
        if settings.enable_query_decomposition:
            from .decompose import retrieve_decomposed

            results = retrieve_decomposed(
                organization_id=organization_id,
                query=query,
                top_k=top_k,
                filters=filters,
                domain=domain,
                allowed_document_ids=allowed_document_ids,
                history=history,
                query_embedding=query_embedding,
            )
        elif settings.enable_crag:
            from .crag import retrieve_with_crag

            results = retrieve_with_crag(
                organization_id=organization_id,
                query=query,
                top_k=top_k,
                filters=filters,
                domain=domain,
                allowed_document_ids=allowed_document_ids,
                history=history,
                query_embedding=query_embedding,
            )
        else:
            results = hybrid_search(
                organization_id=organization_id,
                query=query,
                top_k=top_k,
                filters=filters,
                domain=domain,
                allowed_document_ids=allowed_document_ids,
                history=history,
                query_embedding=query_embedding,
            )

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
                )
            except Exception as exc:
                logger.debug("Semantic cache store skipped: %s", exc)
        return results

    # Vector-only : embedding requis. En échec → pas de fallback BM25 ici.
    try:
        query_vector = get_embedding_vector(query)
    except Exception as e:
        logger.warning("Embedding failed, vector-only retrieval unavailable: %s", e)
        return []
    try:
        return VectorStore().search(
            query_vector=query_vector,
            organization_id=organization_id,
            top_k=top_k,
            filters=filters,
            domain=domain,
            allowed_document_ids=allowed_document_ids,
        )
    except VectorStoreError:
        return []

def retrieve_chunks(
    organization_id: int,
    query: str,
    top_k: int | None = None,
    filters: dict[str, Any] | None = None,
    use_hybrid: bool = True,
    domain: str | None = None,
    allowed_document_ids: frozenset[int] | None = None,
    history: list[str] | None = None,
) -> Sequence[str]:
    """Projection texte-seul de retrieve_chunks_with_metadata."""
    results = retrieve_chunks_with_metadata(
        organization_id=organization_id,
        query=query,
        top_k=top_k,
        filters=filters,
        use_hybrid=use_hybrid,
        domain=domain,
        allowed_document_ids=allowed_document_ids,
        history=history,
    )
    return [r["text"] for r in results]
