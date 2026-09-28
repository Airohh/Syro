"""Ingestion de documents : enregistrement, extraction, classement, indexation.

Le domaine d'un document est stocké dans `documents.domain` : c'est la seule
source de vérité, lue par Qdrant (payload) comme par BM25.
"""

from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
import time
from pathlib import Path
from typing import Sequence

from ..db import db_session
from ..domains import normalize_domain
from .domain_detector import classify_text
from .file_extractor import extract_text_from_bytes
from .rag import index_document

logger = logging.getLogger(__name__)


def checksum_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def parse_tags(raw: str | Sequence[str] | None) -> list[str]:
    if not raw:
        return []
    items = raw.split(",") if isinstance(raw, str) else raw
    return list(dict.fromkeys(t.strip() for t in items if t and t.strip()))


def create_document_entry(
    db: sqlite3.Connection,
    *,
    organization_id: int,
    filename: str,
    storage_path: str,
    mime_type: str | None,
    checksum: str,
    tags: Sequence[str] | None,
    source_type: str,
    domain: str | None = None,
    created_by_user_id: int | None = None,
    access_level_id: int = 1,  # public
    quality_level_id: int = 1,  # draft
) -> tuple[int, int]:
    """Crée la ligne `documents` (statut queued). Retourne (id, version)."""
    row = db.execute(
        "SELECT MAX(version) FROM documents WHERE organization_id = ? AND filename = ?",
        (organization_id, filename),
    ).fetchone()
    version = (row[0] or 0) + 1
    tag_list = parse_tags(tags)
    cur = db.execute(
        """INSERT INTO documents
        (organization_id, filename, storage_path, mime_type, checksum, tags, domain,
         version, source_type, ingestion_status, created_by_user_id,
         access_level_id, quality_level_id, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'queued', ?, ?, ?, CURRENT_TIMESTAMP)""",
        (
            organization_id,
            filename,
            storage_path,
            mime_type,
            checksum,
            json.dumps(tag_list) if tag_list else None,
            normalize_domain(domain),
            version,
            source_type,
            created_by_user_id,
            access_level_id,
            quality_level_id,
        ),
    )
    return cur.lastrowid, version


def _set_status(document_id: int, status: str, **fields) -> None:
    sets = ["ingestion_status = ?", "updated_at = CURRENT_TIMESTAMP"]
    values: list = [status]
    for key, value in fields.items():
        sets.append(f"{key} = ?")
        values.append(value)
    with db_session() as conn:
        conn.execute(
            f"UPDATE documents SET {', '.join(sets)} WHERE id = ?",
            (*values, document_id),
        )


def run_ingestion(document_id: int) -> int:
    """Extraction → domaine (fourni ou détecté) → indexation. Retourne le nb de chunks.

    Lève en cas d'échec ; le statut est géré par `ingest_document`.
    """
    with db_session() as conn:
        doc = conn.execute(
            "SELECT organization_id, filename, storage_path, mime_type, domain "
            "FROM documents WHERE id = ?",
            (document_id,),
        ).fetchone()
    if not doc:
        raise ValueError(f"Document {document_id} introuvable")

    path = Path(doc["storage_path"])
    text = extract_text_from_bytes(path.read_bytes(), doc["filename"], doc["mime_type"])
    if not text.strip():
        raise ValueError("Document vide après extraction")

    domain = doc["domain"] or classify_text(text)["domain"]
    if domain != doc["domain"]:
        with db_session() as conn:
            conn.execute(
                "UPDATE documents SET domain = ? WHERE id = ?", (domain, document_id)
            )

    return index_document(
        document_id,
        doc["organization_id"],
        text,
        domain=domain,
        filename=doc["filename"],
    )


def ingest_document(document_id: int) -> int:
    """Ingestion avec suivi de statut (processing → complete | failed)."""
    start = time.time()
    _set_status(document_id, "processing", ingestion_error=None)
    try:
        chunk_count = run_ingestion(document_id)
    except Exception as exc:
        _set_status(document_id, "failed", ingestion_error=str(exc)[:500])
        raise
    _set_status(document_id, "complete", chunk_count=chunk_count)

    try:
        from .mlops_tracker import get_mlops_tracker

        tracker = get_mlops_tracker()
        if tracker.enabled:
            with db_session() as conn:
                org_id = conn.execute(
                    "SELECT organization_id FROM documents WHERE id = ?", (document_id,)
                ).fetchone()[0]
            tracker.log_document_ingestion(
                document_id=document_id,
                organization_id=org_id,
                num_chunks=chunk_count,
                ingestion_time_ms=(time.time() - start) * 1000,
                document_size_chars=0,
                metadata=None,
            )
    except Exception as exc:  # le tracking ne doit jamais casser l'ingestion
        logger.debug("MLflow ingestion tracking skipped: %s", exc)
    return chunk_count


def process_document(document_id: int) -> None:
    """Variante BackgroundTasks (sans Celery) : l'erreur est déjà en base."""
    try:
        ingest_document(document_id)
    except Exception as exc:
        logger.error("Ingestion failed for document %s: %s", document_id, exc)
