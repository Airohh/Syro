"""Administration de SON organisation (jamais d'une autre).

Chaque endpoint est borné à l'organisation de l'appelant : un owner/admin
ne peut ni lister, ni créditer, ni créer des comptes ailleurs.
"""

import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from ..auth import hash_password
from ..dependencies import get_db, require_role
from ..schemas import Organization, OrganizationCreditUpdate, User, UserCreate

router = APIRouter(prefix="/admin", tags=["admin"])

# Rôles qu'un rôle donné a le droit d'attribuer (pas d'escalade de privilèges).
_ASSIGNABLE_ROLES = {"owner": {"admin", "member"}, "admin": {"member"}}


@router.get("/organization", response_model=Organization)
def get_my_organization(
    db: sqlite3.Connection = Depends(get_db),
    user=Depends(require_role("owner", "admin")),
):
    org = db.execute(
        "SELECT * FROM organizations WHERE id = ?", (user["organization_id"],)
    ).fetchone()
    return Organization(**dict(org))


@router.post("/organization/credits", response_model=Organization)
def adjust_credits(
    payload: OrganizationCreditUpdate,
    db: sqlite3.Connection = Depends(get_db),
    user=Depends(require_role("owner")),
):
    org_id = user["organization_id"]
    db.execute(
        "UPDATE organizations SET credit_balance = MAX(credit_balance + ?, 0) WHERE id = ?",
        (payload.amount, org_id),
    )
    db.commit()
    org = db.execute("SELECT * FROM organizations WHERE id = ?", (org_id,)).fetchone()
    return Organization(**dict(org))


@router.get("/users", response_model=list[User])
def list_users(
    db: sqlite3.Connection = Depends(get_db),
    user=Depends(require_role("owner", "admin")),
):
    rows = db.execute(
        "SELECT * FROM users WHERE organization_id = ?", (user["organization_id"],)
    ).fetchall()
    return [User(**dict(row)) for row in rows]


@router.post("/users", response_model=User)
def create_user(
    payload: UserCreate,
    db: sqlite3.Connection = Depends(get_db),
    user=Depends(require_role("owner", "admin")),
):
    if payload.role not in _ASSIGNABLE_ROLES[user["role"]]:
        raise HTTPException(
            status_code=403,
            detail=f"A {user['role']} cannot create a '{payload.role}' account",
        )
    org_id = user["organization_id"]
    org = db.execute(
        "SELECT max_members FROM organizations WHERE id = ?", (org_id,)
    ).fetchone()
    members = db.execute(
        "SELECT COUNT(*) FROM users WHERE organization_id = ?", (org_id,)
    ).fetchone()[0]
    if members >= org["max_members"]:
        raise HTTPException(status_code=400, detail="Max members reached")
    try:
        cur = db.execute(
            "INSERT INTO users (organization_id, email, password_hash, role) "
            "VALUES (?, ?, ?, ?)",
            (org_id, payload.email, hash_password(payload.password), payload.role),
        )
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=400, detail="Email already exists") from exc
    db.commit()
    row = db.execute("SELECT * FROM users WHERE id = ?", (cur.lastrowid,)).fetchone()
    return User(**dict(row))
