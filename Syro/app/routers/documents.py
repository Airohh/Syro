import sqlite3
import uuid

from fastapi import APIRouter, Body, Depends, UploadFile, File, Form, HTTPException, BackgroundTasks

from ..config import settings
from ..dependencies import require_active_org, enforce_rate_limit, get_current_user
from ..schemas import DocumentUploadResponse, DocumentTextUpload
from ..services.ingestion import (
    checksum_bytes,
    create_document_entry,
    parse_tags,
)
from ..services.celery_client import enqueue_document_ingestion
from ..services.file_extractor import detect_source_type, extract_text_from_bytes
from ..services.document_classifier import classify_document, should_ask_confirmation
from ..schemas import DocumentUploadWithClassificationResponse
from ..db import get_db
from ..security import (
    MAX_FILE_SIZE,
    MAX_TEXT_SIZE,
)

router = APIRouter(prefix="/documents", tags=["documents"])

# Router pour routes multi-domaines
domain_router = APIRouter(prefix="/domains/{domain}/documents", tags=["documents"])

@router.post("/text", response_model=DocumentUploadResponse)
def upload_text_document(
    payload: DocumentTextUpload = Body(...),
    org = Depends(require_active_org(0)),
    user = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    _: bool = Depends(enforce_rate_limit("documents")),
):
    title = payload.title
    content = payload.content
    tags = payload.tags
    
    # Valider le contenu texte
    if settings.enable_file_validation:
        max_size = settings.max_text_size_mb * 1024 * 1024
        if len(content.encode("utf-8")) > max_size:
            raise HTTPException(status_code=400, detail=f"Contenu texte trop volumineux (max {settings.max_text_size_mb} MB)")
    
    storage_path = settings.data_dir / str(org["id"]) / f"{uuid.uuid4()}.txt"
    storage_path.parent.mkdir(parents=True, exist_ok=True)
    storage_path.write_text(content, encoding="utf-8")
    doc_id, version = create_document_entry(
        db,
        organization_id=org["id"],
        filename=title,
        storage_path=str(storage_path),
        mime_type="text/plain",
        checksum=checksum_bytes(content.encode("utf-8")),
        tags=parse_tags(tags),
        source_type="text",
        created_by_user_id=user["id"],
        access_level_id=1,  # Par défaut: public
        quality_level_id=1,  # Par défaut: draft
    )
    # Enqueue dans Celery ou BackgroundTasks
    task_id = enqueue_document_ingestion(doc_id, org["id"], str(storage_path), "text/plain", domain=None, background_tasks=background_tasks)
    return DocumentUploadResponse(document_id=doc_id, version=version, status="queued", chunk_count=0)

@router.post("/files", response_model=DocumentUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    tags: str | None = None,
    org = Depends(require_active_org(0)),
    user = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    _: bool = Depends(enforce_rate_limit("documents")),
):
    try:
        content_bytes = await file.read()
        
        # Valider le fichier
        if settings.enable_file_validation:
            from ..security.upload_validator import validate_file_size
            validate_file_size(file, max_size=settings.max_file_size_mb * 1024 * 1024)
            sanitized_filename = file.filename or "unnamed"
        else:
            sanitized_filename = file.filename or "unnamed"
        
        sanitized_name = f"{uuid.uuid4()}_{sanitized_filename}"
        storage_path = settings.data_dir / str(org["id"]) / sanitized_name
        storage_path.parent.mkdir(parents=True, exist_ok=True)
        storage_path.write_bytes(content_bytes)
        source_type = detect_source_type(sanitized_filename, file.content_type)
        doc_id, version = create_document_entry(
            db,
            organization_id=org["id"],
            filename=sanitized_filename,
            storage_path=str(storage_path),
            mime_type=file.content_type,
            checksum=checksum_bytes(content_bytes),
            tags=parse_tags(tags),
            source_type=source_type,
            created_by_user_id=user["id"],
            access_level_id=1,  # Par défaut: public
            quality_level_id=1,  # Par défaut: draft
        )
        # Enqueue dans Celery ou BackgroundTasks
        # Si Celery/Redis n'est pas disponible, cela basculera automatiquement vers BackgroundTasks (non-bloquant)
        task_id = enqueue_document_ingestion(doc_id, org["id"], str(storage_path), file.content_type, domain=None, background_tasks=background_tasks)
        return DocumentUploadResponse(document_id=doc_id, version=version, status="queued", chunk_count=0)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Erreur lors de l'upload du fichier {file.filename}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de l'upload du fichier: {str(e)}"
        )

@router.post("/upload-with-classification", response_model=DocumentUploadWithClassificationResponse)
async def upload_file_with_classification(
    file: UploadFile = File(...),
    tags: str | None = Form(None),  # Utiliser Form() avec None comme défaut
    domain: str | None = Form(None),  # Utiliser Form() avec None comme défaut
    access_level_id: str | None = Form(None),  # Accepter string (FormData envoie des strings)
    quality_level_id: str | None = Form(None),  # Accepter string (FormData envoie des strings)
    org = Depends(require_active_org(0)),
    user = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    _: bool = Depends(enforce_rate_limit("documents")),
):
    """
    Upload un fichier avec classification automatique du domaine.
    
    Si un domaine est fourni, il sera utilisé directement.
    Sinon, le domaine sera détecté automatiquement à partir du contenu.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Log pour debug
    logger.info(f"Upload reçu - tags: {tags}, domain: {domain}, access_level_id: {access_level_id}, quality_level_id: {quality_level_id}")
    
    # Convertir les chaînes vides en None
    if tags == '':
        tags = None
    if domain == '':
        domain = None
    
    # Convertir access_level_id et quality_level_id en entiers
    # FormData envoie toujours des strings, donc on doit les convertir
    # Si None ou chaîne vide, utiliser les valeurs par défaut (1 = public/draft)
    if access_level_id is None or (isinstance(access_level_id, str) and not access_level_id.strip()):
        access_level_id = 1
    else:
        try:
            access_level_id = int(access_level_id)
        except (ValueError, TypeError):
            access_level_id = 1
    
    if quality_level_id is None or (isinstance(quality_level_id, str) and not quality_level_id.strip()):
        quality_level_id = 1
    else:
        try:
            quality_level_id = int(quality_level_id)
        except (ValueError, TypeError):
            quality_level_id = 1
    
    content_bytes = await file.read()
    
    # Valider le fichier
    if settings.enable_file_validation:
        from ..security.upload_validator import validate_file_size
        validate_file_size(file, max_size=settings.max_file_size_mb * 1024 * 1024)
        sanitized_filename = file.filename or "unnamed"
    else:
        sanitized_filename = file.filename or "unnamed"
    
    # Classification automatique si domaine non fourni
    # OPTIMISATION: Ne pas extraire le texte ici pour les gros fichiers (bloquant)
    # La classification se fera en arrière-plan si nécessaire
    detected_domain = domain
    classification_result = None
    
    if not domain:
        # Pour les gros fichiers PDF, on évite l'extraction synchrone
        # On utilisera "general" par défaut et la classification se fera en arrière-plan
        file_size_mb = len(content_bytes) / (1024 * 1024)
        if file_size_mb > 5:  # Si fichier > 5MB, ne pas extraire maintenant
            detected_domain = "general"
            classification_result = {
                "domain": "general",
                "confidence": 0.5,
                "alternatives": [],
                "note": "Classification différée pour gros fichier"
            }
        else:
            try:
                # Extraire le texte pour la classification (seulement pour petits fichiers)
                text = extract_text_from_bytes(content_bytes, file.filename, file.content_type)
                if text and text.strip():
                    classification_result = classify_document(
                        text=text,
                        filename=sanitized_filename,
                        mime_type=file.content_type
                    )
                    detected_domain = classification_result["domain"]
            except Exception as e:
                # Si la classification échoue, utiliser "general"
                detected_domain = "general"
                classification_result = {
                    "domain": "general",
                    "confidence": 0.3,
                    "alternatives": []
                }
    
    # Si pas de classification effectuée, créer un résultat par défaut
    if not classification_result:
        classification_result = {
            "domain": detected_domain or "general",
            "confidence": 1.0 if domain else 0.5,
            "alternatives": []
        }
    
    # Sauvegarder le fichier
    sanitized_name = f"{uuid.uuid4()}_{sanitized_filename}"
    storage_path = settings.data_dir / str(org["id"]) / sanitized_name
    storage_path.parent.mkdir(parents=True, exist_ok=True)
    storage_path.write_bytes(content_bytes)
    
    # Créer l'entrée document avec le domaine dans les tags
    tags_list = parse_tags(tags) or []
    if domain and domain != "general":
        tags_list.append(f"domain:{domain}")
    
    source_type = detect_source_type(sanitized_filename, file.content_type)
    doc_id, version = create_document_entry(
        db,
        organization_id=org["id"],
        filename=sanitized_filename,
        storage_path=str(storage_path),
        mime_type=file.content_type,
        checksum=checksum_bytes(content_bytes),
        tags=tags_list,
        source_type=source_type,
        created_by_user_id=user["id"],
        access_level_id=access_level_id or 1,
        quality_level_id=quality_level_id or 1,
    )
    
    # Enqueue dans Celery ou BackgroundTasks avec domaine forcé
    task_id = enqueue_document_ingestion(doc_id, org["id"], str(storage_path), file.content_type, domain=domain, background_tasks=background_tasks)
    
    return DocumentUploadWithClassificationResponse(
        document_id=doc_id,
        version=version,
        status="queued",
        chunk_count=0,
        classification=classification_result
    )

@domain_router.get("/{document_id}/status")
def get_document_status_domain(
    domain: str,
    document_id: int,
    org = Depends(require_active_org(0)),
    user = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db),
):
    """Récupérer le statut d'ingestion d'un document (route multi-domaines)."""
    doc = db.execute(
        "SELECT ingestion_status, ingestion_error, chunk_count FROM documents WHERE id = ? AND organization_id = ?",
        (document_id, org["id"]),
    ).fetchone()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document non trouvé")
    
    return {
        "document_id": document_id,
        "domain": domain,
        "status": doc["ingestion_status"],
        "chunk_count": doc["chunk_count"] or 0,
        "error": doc["ingestion_error"],
    }
