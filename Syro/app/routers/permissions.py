"""Router pour la gestion des permissions et niveaux d'accès."""

from fastapi import APIRouter, Depends, HTTPException, status
import sqlite3
from typing import Optional

from ..dependencies import get_current_user, get_current_org, get_db
from ..schemas import (
    AccessLevel,
    QualityLevel,
    UserPermissions,
    UserPermissionsUpdate,
    DocumentShare,
)
from ..services.permissions_service import (
    get_user_permissions,
    can_user_access_document,
    get_access_level_name,
    get_quality_level_name,
)

router = APIRouter(prefix="/permissions", tags=["permissions"])

@router.get("/access-levels", response_model=list[AccessLevel])
def list_access_levels(db: sqlite3.Connection = Depends(get_db)):
    """Liste tous les niveaux d'accès disponibles."""
    rows = db.execute(
        "SELECT id, name, description, priority FROM document_access_levels ORDER BY priority"
    ).fetchall()
    return [AccessLevel(**dict(row)) for row in rows]

@router.get("/quality-levels", response_model=list[QualityLevel])
def list_quality_levels(db: sqlite3.Connection = Depends(get_db)):
    """Liste tous les niveaux de qualité disponibles."""
    rows = db.execute(
        "SELECT id, name, description, priority FROM document_quality_levels ORDER BY priority"
    ).fetchall()
    return [QualityLevel(**dict(row)) for row in rows]

@router.get("/me", response_model=UserPermissions)
def get_my_permissions(
    user = Depends(get_current_user),
    org = Depends(get_current_org),
    db: sqlite3.Connection = Depends(get_db),
):
    """Obtenir les permissions de l'utilisateur connecté."""
    permissions = get_user_permissions(user["id"], org["id"], db)
    if not permissions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permissions not found"
        )
    
    return UserPermissions(
        user_id=user["id"],
        organization_id=org["id"],
        **permissions
    )

@router.get("/users/{user_id}", response_model=UserPermissions)
def get_user_permissions_endpoint(
    user_id: int,
    user = Depends(get_current_user),
    org = Depends(get_current_org),
    db: sqlite3.Connection = Depends(get_db),
):
    """
    Obtenir les permissions d'un utilisateur (nécessite admin/owner).
    """
    # Vérifier que l'utilisateur est admin ou owner
    if user["role"] not in ["admin", "owner"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and owners can view user permissions"
        )
    
    # Vérifier que l'utilisateur appartient à la même organisation
    target_user = db.execute(
        "SELECT organization_id FROM users WHERE id = ?",
        (user_id,)
    ).fetchone()
    
    if not target_user or target_user["organization_id"] != org["id"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in this organization"
        )
    
    permissions = get_user_permissions(user_id, org["id"], db)
    if not permissions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permissions not found"
        )
    
    return UserPermissions(
        user_id=user_id,
        organization_id=org["id"],
        **permissions
    )

@router.put("/users/{user_id}")
def update_user_permissions(
    user_id: int,
    payload: UserPermissionsUpdate,
    user = Depends(get_current_user),
    org = Depends(get_current_org),
    db: sqlite3.Connection = Depends(get_db),
):
    """
    Mettre à jour les permissions d'un utilisateur (nécessite admin/owner).
    """
    # Vérifier que l'utilisateur est admin ou owner
    if user["role"] not in ["admin", "owner"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and owners can update user permissions"
        )
    
    # Vérifier que l'utilisateur appartient à la même organisation
    target_user = db.execute(
        "SELECT organization_id FROM users WHERE id = ?",
        (user_id,)
    ).fetchone()
    
    if not target_user or target_user["organization_id"] != org["id"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in this organization"
        )
    
    # Vérifier si des permissions existent déjà
    existing = db.execute(
        "SELECT id FROM user_permissions WHERE user_id = ? AND organization_id = ?",
        (user_id, org["id"])
    ).fetchone()
    
    updates = []
    params = []
    
    if payload.max_access_level_id is not None:
        updates.append("max_access_level_id = ?")
        params.append(payload.max_access_level_id)
    if payload.min_quality_level_id is not None:
        updates.append("min_quality_level_id = ?")
        params.append(payload.min_quality_level_id)
    if payload.can_upload_documents is not None:
        updates.append("can_upload_documents = ?")
        params.append(payload.can_upload_documents)
    if payload.can_delete_documents is not None:
        updates.append("can_delete_documents = ?")
        params.append(payload.can_delete_documents)
    if payload.can_manage_users is not None:
        updates.append("can_manage_users = ?")
        params.append(payload.can_manage_users)
    if payload.can_view_analytics is not None:
        updates.append("can_view_analytics = ?")
        params.append(payload.can_view_analytics)
    if payload.can_export_data is not None:
        updates.append("can_export_data = ?")
        params.append(payload.can_export_data)
    
    if existing:
        if updates:
            params.extend([user_id, org["id"]])
            db.execute(
                f"UPDATE user_permissions SET {', '.join(updates)} WHERE user_id = ? AND organization_id = ?",
                params,
            )
            db.commit()
    else:
        if updates:
            insert_cols = ["user_id", "organization_id"] + [col.split(" = ")[0] for col in updates]
            insert_vals = [user_id, org["id"]] + params
            placeholders = ", ".join(["?"] * len(insert_vals))
            db.execute(
                f"INSERT INTO user_permissions ({', '.join(insert_cols)}) VALUES ({placeholders})",
                insert_vals,
            )
            db.commit()
        else:
            # No payload provided — nothing to do
            return {"message": "No fields to update"}

    updated = get_user_permissions(user_id, org["id"], db)
    if not updated:
        return {"message": "Permissions updated successfully"}
    return UserPermissions(user_id=user_id, organization_id=org["id"], **updated)

@router.get("/documents/{document_id}/can-access")
def check_document_access(
    document_id: int,
    user = Depends(get_current_user),
    org = Depends(get_current_org),
    db: sqlite3.Connection = Depends(get_db),
):
    """
    Vérifier si l'utilisateur peut accéder à un document.
    """
    can_access = can_user_access_document(user["id"], org["id"], document_id, db)
    
    if can_access:
        # Récupérer les informations du document
        doc = db.execute(
            """
            SELECT 
                id, filename, access_level_id, quality_level_id,
                created_by_user_id
            FROM documents
            WHERE id = ?
            """,
            (document_id,)
        ).fetchone()
        
        if doc:
            return {
                "can_access": True,
                "access_level": get_access_level_name(doc["access_level_id"] or 1, db),
                "quality_level": get_quality_level_name(doc["quality_level_id"] or 1, db),
                "is_owner": doc["created_by_user_id"] == user["id"],
            }
    
    return {"can_access": False}

