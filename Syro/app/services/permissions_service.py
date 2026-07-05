"""
Service de gestion des permissions d'accès aux documents.
Gère les niveaux d'accès (confidentialité) et de qualité des documents.
"""

import sqlite3
from ..db import db_session


def get_user_permissions(
    user_id: int, organization_id: int, db: sqlite3.Connection | None = None
) -> dict | None:
    """
    Récupère les permissions d'un utilisateur dans une organisation.

    Returns:
        Dict avec les permissions ou None si pas de permissions spécifiques
    """
    if db is None:
        with db_session() as db:
            return get_user_permissions(user_id, organization_id, db)

    row = db.execute(
        """
        SELECT 
            max_access_level_id,
            min_quality_level_id,
            can_upload_documents,
            can_delete_documents,
            can_manage_users,
            can_view_analytics,
            can_export_data
        FROM user_permissions
        WHERE user_id = ? AND organization_id = ?
        """,
        (user_id, organization_id),
    ).fetchone()

    if row:
        return dict(row)

    # Permissions par défaut basées sur le rôle
    user = db.execute(
        "SELECT role FROM users WHERE id = ? AND organization_id = ?",
        (user_id, organization_id),
    ).fetchone()

    if not user:
        return None

    role = user["role"]

    # Permissions par défaut selon le rôle
    default_permissions = {
        "owner": {
            "max_access_level_id": 4,  # Accès à tous les niveaux
            "min_quality_level_id": 1,  # Peut voir même les brouillons
            "can_upload_documents": True,
            "can_delete_documents": True,
            "can_manage_users": True,
            "can_view_analytics": True,
            "can_export_data": True,
        },
        "admin": {
            "max_access_level_id": 3,  # Accès jusqu'à confidential
            "min_quality_level_id": 1,
            "can_upload_documents": True,
            "can_delete_documents": True,
            "can_manage_users": True,
            "can_view_analytics": True,
            "can_export_data": True,
        },
        "member": {
            "max_access_level_id": 2,  # Accès jusqu'à internal
            "min_quality_level_id": 2,  # Seulement documents reviewed+
            "can_upload_documents": True,
            "can_delete_documents": False,
            "can_manage_users": False,
            "can_view_analytics": True,
            "can_export_data": False,
        },
    }

    return default_permissions.get(role, default_permissions["member"])


def can_user_access_document(
    user_id: int,
    organization_id: int,
    document_id: int,
    db: sqlite3.Connection | None = None,
) -> bool:
    """
    Vérifie si un utilisateur peut accéder à un document spécifique.

    Prend en compte:
    - Les permissions de l'utilisateur (niveau d'accès max)
    - Le niveau d'accès du document
    - Le niveau de qualité du document
    - Les partages directs (document_shares)
    """
    if db is None:
        with db_session() as db:
            return can_user_access_document(user_id, organization_id, document_id, db)

    # Récupérer le document
    doc = db.execute(
        """
        SELECT 
            access_level_id,
            quality_level_id,
            organization_id,
            created_by_user_id
        FROM documents
        WHERE id = ?
        """,
        (document_id,),
    ).fetchone()

    if not doc:
        return False

    # Vérifier que le document appartient à l'organisation
    if doc["organization_id"] != organization_id:
        return False

    # Si l'utilisateur est le créateur, il a toujours accès
    if doc["created_by_user_id"] == user_id:
        return True

    # Vérifier les partages directs
    share = db.execute(
        """
        SELECT id FROM document_shares
        WHERE document_id = ? AND shared_with_user_id = ?
        AND (expires_at IS NULL OR expires_at > datetime('now'))
        """,
        (document_id, user_id),
    ).fetchone()

    if share:
        return True

    # Récupérer les permissions de l'utilisateur
    permissions = get_user_permissions(user_id, organization_id, db)
    if not permissions:
        return False

    # Vérifier le niveau d'accès
    doc_access_level = doc["access_level_id"] or 1
    user_max_access = permissions.get("max_access_level_id", 1)

    if doc_access_level > user_max_access:
        return False

    # Vérifier le niveau de qualité
    doc_quality_level = doc["quality_level_id"] or 1
    user_min_quality = permissions.get("min_quality_level_id", 1)

    if doc_quality_level < user_min_quality:
        return False

    return True


def filter_documents_by_permissions(
    user_id: int,
    organization_id: int,
    documents: list[dict],
    db: sqlite3.Connection | None = None,
) -> list[dict]:
    """
    Filtre une liste de documents selon les permissions de l'utilisateur.

    Returns:
        Liste filtrée des documents accessibles
    """
    if db is None:
        with db_session() as db:
            return filter_documents_by_permissions(
                user_id, organization_id, documents, db
            )

    if not documents:
        return []

    permissions = get_user_permissions(user_id, organization_id, db)
    if not permissions:
        return []

    user_max_access = permissions.get("max_access_level_id", 1)
    user_min_quality = permissions.get("min_quality_level_id", 1)

    # Batch-load all shared document IDs in a single query (fixes N+1)
    doc_ids = [doc["id"] for doc in documents]
    placeholders = ",".join("?" * len(doc_ids))
    shared_rows = db.execute(
        f"""
        SELECT document_id FROM document_shares
        WHERE document_id IN ({placeholders})
          AND shared_with_user_id = ?
          AND (expires_at IS NULL OR expires_at > datetime('now'))
        """,
        (*doc_ids, user_id),
    ).fetchall()
    shared_doc_ids = {row["document_id"] for row in shared_rows}

    filtered = []
    for doc in documents:
        doc_id = doc["id"]
        doc_access_level = doc.get("access_level_id") or 1
        doc_quality_level = doc.get("quality_level_id") or 1

        # Creator always has access
        if doc.get("created_by_user_id") == user_id:
            filtered.append(doc)
            continue

        # Explicit share overrides access-level restrictions
        if doc_id in shared_doc_ids:
            filtered.append(doc)
            continue

        # Apply permission-level gates
        if doc_access_level > user_max_access:
            continue
        if doc_quality_level < user_min_quality:
            continue

        filtered.append(doc)

    return filtered


def get_access_level_name(
    access_level_id: int, db: sqlite3.Connection | None = None
) -> str:
    """Récupère le nom d'un niveau d'accès."""
    if db is None:
        with db_session() as db:
            return get_access_level_name(access_level_id, db)

    row = db.execute(
        "SELECT name FROM document_access_levels WHERE id = ?", (access_level_id,)
    ).fetchone()

    return row["name"] if row else "unknown"


def get_quality_level_name(
    quality_level_id: int, db: sqlite3.Connection | None = None
) -> str:
    """Récupère le nom d'un niveau de qualité."""
    if db is None:
        with db_session() as db:
            return get_quality_level_name(quality_level_id, db)

    row = db.execute(
        "SELECT name FROM document_quality_levels WHERE id = ?", (quality_level_id,)
    ).fetchone()

    return row["name"] if row else "unknown"
