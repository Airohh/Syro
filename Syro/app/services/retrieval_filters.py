"""Filtres de retrieval avant ANN — permissions + scope domaine (T2.4)."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from ..db import db_session
from .permissions_service import filter_documents_by_permissions


@dataclass(frozen=True)
class RetrievalScope:
    """Scope appliqué avant vector/BM25 (pas après rerank)."""

    allowed_document_ids: (
        frozenset[int] | None
    )  # None = pas de filtre doc (eval système)


def get_accessible_document_ids(
    user_id: int,
    organization_id: int,
    db: sqlite3.Connection | None = None,
) -> frozenset[int]:
    """IDs des documents dont les chunks peuvent être retournés pour cet utilisateur."""
    if db is None:
        with db_session() as conn:
            return get_accessible_document_ids(user_id, organization_id, conn)

    rows = db.execute(
        """
        SELECT
            id,
            access_level_id,
            quality_level_id,
            created_by_user_id,
            organization_id
        FROM documents
        WHERE organization_id = ? AND status = 'active'
        """,
        (organization_id,),
    ).fetchall()

    documents = [dict(row) for row in rows]
    allowed = filter_documents_by_permissions(user_id, organization_id, documents, db)
    return frozenset(doc["id"] for doc in allowed)


def build_retrieval_scope(
    user_id: int | None,
    organization_id: int,
) -> RetrievalScope:
    """Construit le scope retrieval. Sans user_id → pas de filtre permissions (eval)."""
    if user_id is None:
        return RetrievalScope(allowed_document_ids=None)
    return RetrievalScope(
        allowed_document_ids=get_accessible_document_ids(user_id, organization_id),
    )
