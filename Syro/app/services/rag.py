"""RAG service with hybrid search and Qdrant integration."""

from __future__ import annotations

import logging
import time
from typing import Any, Sequence

import numpy as np

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
            
            qdrant_chunk_id = f"{organization_id}_{document_id}_{chunk_id}"
            
            chunk_metadata = {
                "chunk_index": chunk_index,
                "header": chunk_info.get("header", ""),
                "level": chunk_info.get("level", 0),
                **(metadata or {}),
            }
            
            try:
                vector_store.add_chunk(
                    chunk_id=qdrant_chunk_id,
                    organization_id=organization_id,
                    document_id=document_id,
                    text=chunk_text,
                    metadata=chunk_metadata,
                    domain=detected_domain,
                )
            except VectorStoreError as e:
                logger.error(
                    "Failed to index chunk %s (doc %d) in Qdrant — SQLite/Qdrant out of sync: %s",
                    qdrant_chunk_id, document_id, e,
                )
    
    bm25_search.mark_for_rebuild(organization_id)
    
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

def retrieve_chunks(
    organization_id: int,
    query: str,
    top_k: int | None = None,
    filters: dict[str, Any] | None = None,
    use_hybrid: bool = True,
    domain: str | None = None,
) -> Sequence[str]:
    if top_k is None:
        top_k = settings.rerank_top_k
    
    if use_hybrid:
        results = hybrid_search(
            organization_id=organization_id,
            query=query,
            top_k=top_k,
            filters=filters,
            domain=domain,
        )
        return [r["text"] for r in results]
    else:
        try:
            query_vector = get_embedding_vector(query)
        except Exception as e:
            logger.warning("Embedding failed, vector-only retrieval unavailable: %s", e)
            return []
        vector_store = VectorStore()
        try:
            results = vector_store.search(
                query_vector=query_vector,
                organization_id=organization_id,
                top_k=top_k,
                filters=filters,
                domain=domain,
            )
            return [r["text"] for r in results]
        except VectorStoreError:
            return []

def retrieve_chunks_with_metadata(
    organization_id: int,
    query: str,
    top_k: int | None = None,
    filters: dict[str, Any] | None = None,
    use_hybrid: bool = True,
    domain: str | None = None,
) -> list[dict[str, Any]]:
    if top_k is None:
        top_k = settings.rerank_top_k
    
    if use_hybrid:
        return hybrid_search(
            organization_id=organization_id,
            query=query,
            top_k=top_k,
            filters=filters,
            domain=domain,
        )
    else:
        try:
            query_vector = get_embedding_vector(query)
        except Exception as e:
            logger.warning("Embedding failed, vector-only retrieval unavailable: %s", e)
            return []
        vector_store = VectorStore()
        try:
            return vector_store.search(
                query_vector=query_vector,
                organization_id=organization_id,
                top_k=top_k,
                filters=filters,
                domain=domain,
            )
        except VectorStoreError:
            return []
