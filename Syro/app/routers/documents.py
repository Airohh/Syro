"""Documents : upload (fichier ou texte), liste, statut, suppression.

L'ingestion est asynchrone (worker Celery, ou tâche de fond sans Redis) :
l'upload renvoie `queued`, puis GET /documents/{id} donne le statut.
"""

from __future__ import annotations

import logging
import os
import sqlite3
import uuid

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Body,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)

from ..config import settings
from ..db import get_db
from ..dependencies import enforce_rate_limit, get_current_user, require_active_org
from ..domains import DOMAINS, normalize_domain
from ..schemas import (
    DocumentTextUpload,
    DocumentUploadResponse,
    DocumentUploadWithClassificationResponse,
)
from ..services.bm25_search import bm25_search
from ..services.celery_client import enqueue_document_ingestion
from ..services.domain_detector import classify_text
from ..services.file_extractor import (
    SUPPORTED_EXTENSIONS,
    detect_source_type,
    extract_text_from_bytes,
    is_supported,
)
from ..services.ingestion import checksum_bytes, create_document_entry, parse_tags
from ..services.permissions_service import get_user_permissions
from ..services.vector_store import VectorStore, VectorStoreError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])
domain_router = APIRouter(prefix="/domains/{domain}/documents", tags=["documents"])

_CLASSIFY_MAX_BYTES = 5 * 1024 * 1024  # au-delà, classement fait par le worker


def _validate_domain(domain: str | None) -> str | None:
    if not domain or domain == "general":
        return None
    normalized = normalize_domain(domain)
    if normalized is None:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown domain '{domain}'. Available: {list(DOMAINS)}",
        )
    return normalized


def _check_upload_permission(user, org, db: sqlite3.Connection) -> None:
    permissions = get_user_permissions(user["id"], org["id"], db)
    if permissions and not permissions.get("can_upload_documents", True):
        raise HTTPException(status_code=403, detail="Upload not allowed")


async def _read_upload(file: UploadFile) -> tuple[str, bytes]:
    filename = os.path.basename(file.filename or "document.txt")
    if not is_supported(filename):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type. Supported: {sorted(SUPPORTED_EXTENSIONS)}",
        )
    max_size = settings.max_file_size_mb * 1024 * 1024
    content = await file.read(max_size + 1)
    if len(content) > max_size:
        raise HTTPException(
            status_code=413,
            detail=f"File too large (max {settings.max_file_size_mb} MB).",
        )
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")
    return filename, content


def _save_and_enqueue(
    *,
    db: sqlite3.Connection,
    background_tasks: BackgroundTasks,
    org,
    user,
    filename: str,
    content: bytes,
    mime_type: str | None,
    tags: str | list[str] | None,
    domain: str | None,
    access_level_id: int = 1,
    quality_level_id: int = 1,
) -> tuple[int, int]:
    storage_path = settings.data_dir / str(org["id"]) / f"{uuid.uuid4()}_{filename}"
    storage_path.parent.mkdir(parents=True, exist_ok=True)
    storage_path.write_bytes(content)
    doc_id, version = create_document_entry(
        db,
        organization_id=org["id"],
        filename=filename,
        storage_path=str(storage_path),
        mime_type=mime_type,
        checksum=checksum_bytes(content),
        tags=parse_tags(tags),
        source_type=detect_source_type(filename, mime_type),
        domain=domain,
        created_by_user_id=user["id"],
        access_level_id=access_level_id,
        quality_level_id=quality_level_id,
    )
    # Commit AVANT la mise en file : le worker (autre processus) doit voir la ligne.
    db.commit()
    enqueue_document_ingestion(doc_id, background_tasks=background_tasks)
    return doc_id, version


@router.get("")
def list_documents(
    org=Depends(require_active_org(0)),
    db: sqlite3.Connection = Depends(get_db),
):
    docs = db.execute(
        """SELECT id, filename, mime_type, domain, ingestion_status, ingestion_error,
                  chunk_count, created_at, tags, source_type
           FROM documents WHERE organization_id = ? AND status = 'active'
           ORDER BY created_at DESC""",
        (org["id"],),
    ).fetchall()
    return {"documents": [dict(d) for d in docs]}


@router.get("/{document_id}")
def get_document_status(
    document_id: int,
    org=Depends(require_active_org(0)),
    db: sqlite3.Connection = Depends(get_db),
):
    doc = db.execute(
        """SELECT id, filename, domain, ingestion_status, ingestion_error, chunk_count
           FROM documents WHERE id = ? AND organization_id = ?""",
        (document_id, org["id"]),
    ).fetchone()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return {
        "document_id": doc["id"],
        "filename": doc["filename"],
        "domain": doc["domain"],
        "status": doc["ingestion_status"],
        "chunk_count": doc["chunk_count"] or 0,
        "error": doc["ingestion_error"],
    }


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: int,
    user=Depends(get_current_user),
    org=Depends(require_active_org(0)),
    db: sqlite3.Connection = Depends(get_db),
):
    """Supprime un document (SQLite + Qdrant). Permission `can_delete_documents`."""
    doc = db.execute(
        "SELECT id FROM documents WHERE id = ? AND organization_id = ?",
        (document_id, org["id"]),
    ).fetchone()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    permissions = get_user_permissions(user["id"], org["id"], db)
    if not permissions or not permissions.get("can_delete_documents"):
        raise HTTPException(
            status_code=403, detail="Permission 'can_delete_documents' required"
        )

    try:
        VectorStore().delete_document(document_id)
    except VectorStoreError as e:
        # Points orphelins inoffensifs : filtrés par org, jamais renvoyés sans
        # chunk SQLite correspondant côté BM25, et purgés à la réindexation.
        logger.warning("Qdrant cleanup failed for doc %d: %s", document_id, e)

    db.execute("DELETE FROM doc_chunks WHERE document_id = ?", (document_id,))
    db.execute("DELETE FROM documents WHERE id = ?", (document_id,))
    db.commit()
    bm25_search.mark_for_rebuild(org["id"])


@router.post("/text", response_model=DocumentUploadResponse)
def upload_text_document(
    background_tasks: BackgroundTasks,
    payload: DocumentTextUpload = Body(...),
    org=Depends(require_active_org(0)),
    user=Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db),
    _: bool = Depends(enforce_rate_limit("documents")),
):
    _check_upload_permission(user, org, db)
    content = payload.content.encode("utf-8")
    if len(content) > settings.max_text_size_mb * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail=f"Text too large (max {settings.max_text_size_mb} MB)",
        )
    title = os.path.basename(payload.title) or "note"
    filename = title if title.endswith((".txt", ".md")) else f"{title}.txt"
    doc_id, version = _save_and_enqueue(
        db=db,
        background_tasks=background_tasks,
        org=org,
        user=user,
        filename=filename,
        content=content,
        mime_type="text/plain",
        tags=payload.tags,
        domain=_validate_domain(payload.domain),
    )
    return DocumentUploadResponse(
        document_id=doc_id, version=version, status="queued", chunk_count=0
    )


@router.post("/files", response_model=DocumentUploadResponse)
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    tags: str | None = Form(None),
    domain: str | None = Form(None),
    org=Depends(require_active_org(0)),
    user=Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db),
    _: bool = Depends(enforce_rate_limit("documents")),
):
    """Upload d'un fichier. Sans `domain`, le worker le classe automatiquement."""
    _check_upload_permission(user, org, db)
    filename, content = await _read_upload(file)
    doc_id, version = _save_and_enqueue(
        db=db,
        background_tasks=background_tasks,
        org=org,
        user=user,
        filename=filename,
        content=content,
        mime_type=file.content_type,
        tags=tags,
        domain=_validate_domain(domain),
    )
    return DocumentUploadResponse(
        document_id=doc_id, version=version, status="queued", chunk_count=0
    )


@router.post(
    "/upload-with-classification",
    response_model=DocumentUploadWithClassificationResponse,
)
async def upload_file_with_classification(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    tags: str | None = Form(None),
    domain: str | None = Form(None),
    access_level_id: int | None = Form(None),
    quality_level_id: int | None = Form(None),
    org=Depends(require_active_org(0)),
    user=Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db),
    _: bool = Depends(enforce_rate_limit("documents")),
):
    """Upload + classement immédiat du domaine (renvoyé à l'UI).

    Le domaine détecté est ENREGISTRÉ sur le document : c'est celui utilisé
    pour l'indexation (plus de divergence UI / index).
    """
    _check_upload_permission(user, org, db)
    filename, content = await _read_upload(file)
    explicit = _validate_domain(domain)

    if explicit:
        classification = {"domain": explicit, "confidence": 1.0, "alternatives": []}
    elif len(content) <= _CLASSIFY_MAX_BYTES:
        try:
            text = extract_text_from_bytes(content, filename, file.content_type)
            classification = classify_text(text)
        except Exception as e:
            logger.warning("Classification failed for %s: %s", filename, e)
            classification = {
                "domain": "general",
                "confidence": 0.0,
                "alternatives": [],
            }
    else:
        classification = {
            "domain": "general",
            "confidence": 0.0,
            "alternatives": [],
            "note": "Gros fichier : classement fait pendant l'ingestion",
        }

    stored_domain = explicit or (
        classification["domain"] if classification.get("confidence") else None
    )
    doc_id, version = _save_and_enqueue(
        db=db,
        background_tasks=background_tasks,
        org=org,
        user=user,
        filename=filename,
        content=content,
        mime_type=file.content_type,
        tags=tags,
        domain=stored_domain,
        access_level_id=access_level_id or 1,
        quality_level_id=quality_level_id or 1,
    )
    return DocumentUploadWithClassificationResponse(
        document_id=doc_id,
        version=version,
        status="queued",
        chunk_count=0,
        classification=classification,
    )


@domain_router.get("/{document_id}/status")
def get_document_status_domain(
    domain: str,
    document_id: int,
    org=Depends(require_active_org(0)),
    db: sqlite3.Connection = Depends(get_db),
):
    """Alias historique de GET /documents/{id}."""
    return get_document_status(document_id, org=org, db=db)
