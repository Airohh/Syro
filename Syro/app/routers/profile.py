"""Router pour le profil utilisateur avec statistiques."""

from fastapi import APIRouter, Depends
import sqlite3

from ..dependencies import get_current_user, get_current_org
from ..db import get_db
from ..schemas import ProfileStats, UserProfileUpdate
from ..services.stats_service import (
    get_user_stats,
    get_documents_by_org,
)
from ..services.permissions_service import filter_documents_by_permissions

router = APIRouter(prefix="/profile", tags=["profile"])

@router.get("/stats", response_model=ProfileStats)
def get_profile_stats(
    user = Depends(get_current_user),
    org = Depends(get_current_org),
    db: sqlite3.Connection = Depends(get_db),
):
    """
    Obtenir les statistiques complètes du profil utilisateur/organisation.
    
    Returns:
        Statistiques complètes (documents, stockage, utilisation)
    """
    stats = get_user_stats(user["id"], org["id"])
    return ProfileStats(**stats)

@router.get("/documents")
def get_profile_documents(
    limit: int = 50,
    offset: int = 0,
    domain: str | None = None,
    user = Depends(get_current_user),
    org = Depends(get_current_org),
    db: sqlite3.Connection = Depends(get_db),
):
    """
    Obtenir la liste des documents de l'organisation (filtrés par permissions).
    
    Args:
        limit: Nombre maximum de documents à retourner
        offset: Offset pour la pagination
        domain: Filtrer par domaine (optionnel)
    
    Returns:
        Liste des documents avec leurs métadonnées (filtrés selon les permissions)
    """
    try:
        documents = get_documents_by_org(org["id"], limit, offset, domain, db)
        # Filtrer par permissions de l'utilisateur
        filtered_documents = filter_documents_by_permissions(
            user["id"], org["id"], documents, db
        )
        return {
            "documents": filtered_documents,
            "total": len(filtered_documents),
            "limit": limit,
            "offset": offset,
        }
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Erreur lors de la récupération des documents: {e}", exc_info=True)
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération des documents: {str(e)}"
        )

@router.get("/me")
def get_my_profile(
    user = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db),
):
    """Obtenir le profil de l'utilisateur connecté."""
    user_row = db.execute(
        """
        SELECT 
            id, organization_id, email, role, status,
            first_name, last_name, avatar_url, bio, phone,
            preferences, last_login, created_at, updated_at
        FROM users
        WHERE id = ?
        """,
        (user["id"],)
    ).fetchone()
    
    if not user_row:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    return dict(user_row)

@router.put("/me", response_model=dict)
def update_my_profile(
    payload: UserProfileUpdate,
    user = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db),
):
    """Mettre à jour le profil de l'utilisateur connecté."""
    updates = []
    params = []
    
    if payload.first_name is not None:
        updates.append("first_name = ?")
        params.append(payload.first_name)
    if payload.last_name is not None:
        updates.append("last_name = ?")
        params.append(payload.last_name)
    if payload.avatar_url is not None:
        updates.append("avatar_url = ?")
        params.append(payload.avatar_url)
    if payload.bio is not None:
        updates.append("bio = ?")
        params.append(payload.bio)
    if payload.phone is not None:
        updates.append("phone = ?")
        params.append(payload.phone)
    if payload.preferences is not None:
        import json
        updates.append("preferences = ?")
        params.append(json.dumps(payload.preferences))
    
    if not updates:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    
    updates.append("updated_at = CURRENT_TIMESTAMP")
    params.append(user["id"])
    
    db.execute(
        f"UPDATE users SET {', '.join(updates)} WHERE id = ?",
        params
    )
    db.commit()
    
    # Retourner le profil mis à jour
    return get_my_profile(user, db)

