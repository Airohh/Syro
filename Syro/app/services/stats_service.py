"""Service de statistiques pour le profil utilisateur/organisation."""

from __future__ import annotations
import os

from datetime import datetime, timedelta
from typing import Any

import sqlite3

from ..db import db_session

def get_user_stats(user_id: int, organization_id: int) -> dict[str, Any]:
    """Stats utilisateur/organisation."""
    with db_session() as db:
        doc_stats = get_document_stats_by_org(organization_id, db)
        storage_stats = get_storage_stats(organization_id, db)
        usage_stats = get_usage_stats(organization_id, db)
        
        return {
            "documents": doc_stats,
            "storage": storage_stats,
            "usage": usage_stats,
        }

def get_documents_by_org(
    organization_id: int,
    limit: int = 50,
    offset: int = 0,
    domain: str | None = None,
    db: sqlite3.Connection | None = None
) -> list[dict[str, Any]]:
    """Obtenir la liste des documents d'une organisation avec pagination."""
    if db is None:
        with db_session() as db:
            return get_documents_by_org(organization_id, limit, offset, domain, db)
    
    query = """
        SELECT 
            id, organization_id, filename, storage_path, mime_type,
            status, tags, version, ingestion_status, ingestion_error,
            chunk_count, source_type, created_at, updated_at,
            created_by_user_id, access_level_id, quality_level_id
        FROM documents
        WHERE organization_id = ? AND status = 'active'
    """
    params = [organization_id]
    
    if domain:
        query += " AND (tags LIKE ? OR source_type = ?)"
        params.extend([f"%{domain}%", domain])
    
    query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    rows = db.execute(query, params).fetchall()
    return [dict(row) for row in rows]

def get_document_stats_by_org(organization_id: int, db: sqlite3.Connection | None = None) -> dict[str, Any]:
    """Stats documents par org."""
    if db is None:
        with db_session() as db:
            return get_document_stats_by_org(organization_id, db)
    
    # Total documents
    total_row = db.execute(
        "SELECT COUNT(*) FROM documents WHERE organization_id = ? AND status = 'active'",
        (organization_id,)
    ).fetchone()
    total = total_row[0] if total_row else 0
    
    # Documents par domaine
    domain_rows = db.execute(
        "SELECT source_type, COUNT(*) FROM documents WHERE organization_id = ? AND status = 'active' GROUP BY source_type",
        (organization_id,)
    ).fetchall()
    by_domain = {row[0] or 'general': row[1] for row in domain_rows}
    
    # Stats temporelles
    seven_days_ago = (datetime.now() - timedelta(days=7)).isoformat()
    thirty_days_ago = (datetime.now() - timedelta(days=30)).isoformat()
    
    last_7_days = db.execute(
        "SELECT COUNT(*) FROM documents WHERE organization_id = ? AND status = 'active' AND created_at >= ?",
        (organization_id, seven_days_ago)
    ).fetchone()[0] or 0
    
    last_30_days = db.execute(
        "SELECT COUNT(*) FROM documents WHERE organization_id = ? AND status = 'active' AND created_at >= ?",
        (organization_id, thirty_days_ago)
    ).fetchone()[0] or 0
    
    pending = db.execute(
        "SELECT COUNT(*) FROM documents WHERE organization_id = ? AND ingestion_status = 'queued'",
        (organization_id,)
    ).fetchone()[0] or 0
    
    failed = db.execute(
        "SELECT COUNT(*) FROM documents WHERE organization_id = ? AND ingestion_status = 'failed'",
        (organization_id,)
    ).fetchone()[0] or 0
    
    return {
        "total": total,
        "by_domain": by_domain,
        "last_7_days": last_7_days,
        "last_30_days": last_30_days,
        "pending": pending,
        "failed": failed,
    }

def get_storage_stats(organization_id: int, db: sqlite3.Connection | None = None) -> dict[str, Any]:
    """Stats stockage."""
    if db is None:
        with db_session() as db:
            return get_storage_stats(organization_id, db)
    
    rows = db.execute(
        "SELECT storage_path FROM documents WHERE organization_id = ? AND status = 'active'",
        (organization_id,)
    ).fetchall()
    
    total_bytes = 0
    for row in rows:
        if row[0] and os.path.exists(row[0]):
            try:
                total_bytes += os.path.getsize(row[0])
            except:
                pass
    if total_bytes == 0:
        total_bytes = len(rows) * 100 * 1024
    
    return {
        "total_bytes": total_bytes,
        "total_mb": round(total_bytes / (1024 * 1024), 2),
        "total_gb": round(total_bytes / (1024 * 1024 * 1024), 2),
    }

def get_usage_stats(organization_id: int, db: sqlite3.Connection | None = None) -> dict[str, Any]:
    """Stats utilisation."""
    if db is None:
        with db_session() as db:
            return get_usage_stats(organization_id, db)
    
    # Conversations
    conversations = db.execute(
        "SELECT COUNT(DISTINCT conversation_id) FROM messages WHERE organization_id = ?",
        (organization_id,)
    ).fetchone()[0] or 0
    
    # Messages
    messages = db.execute(
        "SELECT COUNT(*) FROM messages WHERE organization_id = ?",
        (organization_id,)
    ).fetchone()[0] or 0
    
    # Conversations récentes (7 jours)
    seven_days_ago = (datetime.now() - timedelta(days=7)).isoformat()
    recent_conversations = db.execute(
        "SELECT COUNT(DISTINCT conversation_id) FROM messages WHERE organization_id = ? AND created_at >= ?",
        (organization_id, seven_days_ago)
    ).fetchone()[0] or 0
    
    return {
        "conversations": conversations,
        "messages": messages,
        "recent_conversations_7d": recent_conversations,
    }