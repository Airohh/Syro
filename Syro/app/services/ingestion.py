from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Sequence

import sqlite3

from fastapi import BackgroundTasks

from ..db import db_session
from .file_extractor import extract_text_from_bytes
from .rag import index_document_content


def _serialize_tags(tags: Sequence[str] | None) -> str | None:
    if not tags:
        return None
    return json.dumps(list(dict.fromkeys([tag.strip() for tag in tags if tag.strip()])))


def parse_tags(raw: str | None) -> list[str] | None:
    if not raw:
        return None
    return [tag.strip() for tag in raw.split(",") if tag.strip()]


def compute_next_version(
    db: sqlite3.Connection, organization_id: int, filename: str
) -> int:
    row = db.execute(
        "SELECT MAX(version) FROM documents WHERE organization_id = ? AND filename = ?",
        (organization_id, filename),
    ).fetchone()
    current = row[0] if row and row[0] else 0
    return current + 1


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
    created_by_user_id: int | None = None,
    access_level_id: int | None = 1,  # Par défaut: public
    quality_level_id: int | None = 1,  # Par défaut: draft
) -> tuple[int, int]:
    version = compute_next_version(db, organization_id, filename)
    cur = db.execute(
        """INSERT INTO documents 
        (organization_id, filename, storage_path, mime_type, checksum, tags, version, source_type, 
         ingestion_status, created_by_user_id, access_level_id, quality_level_id, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'queued', ?, ?, ?, CURRENT_TIMESTAMP)""",
        (
            organization_id,
            filename,
            storage_path,
            mime_type,
            checksum,
            _serialize_tags(tags),
            version,
            source_type,
            created_by_user_id,
            access_level_id,
            quality_level_id,
        ),
    )
    return cur.lastrowid, version


def queue_ingestion(
    background_tasks: BackgroundTasks,
    document_id: int,
    organization_id: int,
    storage_path: str,
    mime_type: str | None,
    domain: str | None = None,
) -> None:
    background_tasks.add_task(
        process_document, document_id, organization_id, storage_path, mime_type, domain
    )


_TYPE_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("snowflake", ("snowflake", "snow")),
    ("airflow", ("airflow", "dag")),
    ("databricks", ("databricks", "spark")),
    ("azure", ("azure", "synapse")),
    ("terraform", ("terraform", "tf")),
    ("sql", ("sql", "query")),
]


def infer_metadata(
    filename: str, tags: list[str], source_type: str, domain: str | None = None
) -> dict:
    """Construit les métadonnées d'un chunk (type/difficulté) à partir du nom de
    fichier et des tags. Source unique partagée par le worker Celery et le
    fallback BackgroundTasks (évite la divergence d'inférence)."""
    metadata: dict = {"source_type": source_type, "tags": tags}
    if domain:
        metadata["domain"] = domain

    filename_lower = filename.lower()
    metadata["type"] = next(
        (
            label
            for label, keywords in _TYPE_KEYWORDS
            if any(k in filename_lower for k in keywords)
        ),
        "general",
    )

    lowered = {t.lower() for t in tags}
    if lowered & {"beginner", "intro", "basics"}:
        metadata["difficulty"] = "beginner"
    elif lowered & {"advanced", "expert", "complex"}:
        metadata["difficulty"] = "expert"
    else:
        metadata["difficulty"] = "intermediate"
    return metadata


def run_ingestion(
    document_id: int,
    organization_id: int,
    storage_path: str,
    mime_type: str | None,
    domain: str | None = None,
) -> int:
    """Cœur d'ingestion partagé (extract → métadonnées → index Qdrant).

    Lève en cas d'échec ; la gestion du statut/metrics/retry est laissée à
    l'appelant (worker Celery vs BackgroundTasks). Retourne le nombre de chunks.
    """
    path = Path(storage_path)
    content_bytes = path.read_bytes()
    text = extract_text_from_bytes(content_bytes, path.name, mime_type)
    if not text.strip():
        raise ValueError("Document vide après extraction")

    with db_session() as conn:
        doc_row = conn.execute(
            "SELECT filename, source_type, tags FROM documents WHERE id = ?",
            (document_id,),
        ).fetchone()
    if not doc_row:
        raise ValueError(f"Document {document_id} non trouvé dans la DB")

    try:
        tags = json.loads(doc_row["tags"]) if doc_row["tags"] else []
    except (json.JSONDecodeError, TypeError):
        tags = []
    metadata = infer_metadata(
        doc_row["filename"], tags, doc_row["source_type"] or "unknown", domain
    )

    return index_document_content(document_id, organization_id, text, metadata=metadata)


def process_document(
    document_id: int,
    organization_id: int,
    storage_path: str,
    mime_type: str | None,
    domain: str | None = None,
) -> None:
    """Fallback BackgroundTasks : ingestion synchrone + maj statut DB."""
    try:
        chunk_count = run_ingestion(
            document_id, organization_id, storage_path, mime_type, domain
        )
        with db_session() as conn:
            conn.execute(
                "UPDATE documents SET ingestion_status = 'complete', chunk_count = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (chunk_count, document_id),
            )
    except Exception as exc:  # pragma: no cover - background logging
        with db_session() as conn:
            conn.execute(
                "UPDATE documents SET ingestion_status = 'failed', ingestion_error = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (str(exc), document_id),
            )


def checksum_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()
