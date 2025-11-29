from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterable, Sequence

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

def compute_next_version(db: sqlite3.Connection, organization_id: int, filename: str) -> int:
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

def queue_ingestion(background_tasks: BackgroundTasks, document_id: int, organization_id: int, storage_path: str, mime_type: str | None, domain: str | None = None) -> None:
    background_tasks.add_task(process_document, document_id, organization_id, storage_path, mime_type, domain)

def process_document(document_id: int, organization_id: int, storage_path: str, mime_type: str | None, domain: str | None = None) -> None:
    path = Path(storage_path)
    try:
        content_bytes = path.read_bytes()
        text = extract_text_from_bytes(content_bytes, path.name, mime_type)
        if not text.strip():
            raise ValueError("Document vide après extraction")
        
        # Extract metadata from document
        with db_session() as conn:
            doc_row = conn.execute(
                "SELECT filename, source_type, tags FROM documents WHERE id = ?",
                (document_id,),
            ).fetchone()
            
            if doc_row:
                source_type = doc_row["source_type"] or "unknown"
                tags_json = doc_row["tags"]
                try:
                    tags = json.loads(tags_json) if tags_json else []
                except (json.JSONDecodeError, TypeError):
                    tags = []
                
                # Infer document type and theme from filename/tags
                metadata = {
                    "source_type": source_type,
                    "tags": tags,
                }
                
                # If domain is forced, use it instead of auto-detection
                if domain:
                    metadata["domain"] = domain
                
                # Try to infer type (snowflake, airflow, etc.) from filename/tags
                filename_lower = doc_row["filename"].lower()
                if any(keyword in filename_lower for keyword in ["snowflake", "snow"]):
                    metadata["type"] = "snowflake"
                elif any(keyword in filename_lower for keyword in ["airflow", "dag"]):
                    metadata["type"] = "airflow"
                elif any(keyword in filename_lower for keyword in ["databricks", "spark"]):
                    metadata["type"] = "databricks"
                elif any(keyword in filename_lower for keyword in ["azure", "synapse"]):
                    metadata["type"] = "azure"
                elif any(keyword in filename_lower for keyword in ["terraform", "tf"]):
                    metadata["type"] = "terraform"
                elif any(keyword in filename_lower for keyword in ["sql", "query"]):
                    metadata["type"] = "sql"
                else:
                    metadata["type"] = "general"
                
                # Infer difficulty (simple heuristic)
                if any(tag.lower() in ["beginner", "intro", "basics"] for tag in tags):
                    metadata["difficulty"] = "beginner"
                elif any(tag.lower() in ["advanced", "expert", "complex"] for tag in tags):
                    metadata["difficulty"] = "expert"
                else:
                    metadata["difficulty"] = "intermediate"
            else:
                metadata = {}
        
        chunk_count = index_document_content(document_id, organization_id, text, metadata=metadata)
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
