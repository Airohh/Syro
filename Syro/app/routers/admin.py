from fastapi import APIRouter, Depends, HTTPException
import sqlite3

from ..dependencies import get_db, require_role
from ..schemas import Organization, OrganizationCreate, OrganizationCreditUpdate, User, UserCreate
from ..security import hash_password

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/organizations", response_model=list[Organization])
def list_organizations(db: sqlite3.Connection = Depends(get_db), user=Depends(require_role("owner"))):
    rows = db.execute("SELECT * FROM organizations").fetchall()
    return [Organization(**dict(row)) for row in rows]

@router.post("/organizations", response_model=Organization)
def create_organization(payload: OrganizationCreate, db: sqlite3.Connection = Depends(get_db), user=Depends(require_role("owner"))):
    cur = db.execute(
        "INSERT INTO organizations (name, credit_balance, max_members) VALUES (?, ?, ?)",
        (payload.name, payload.credit_balance, payload.max_members),
    )
    org_id = cur.lastrowid
    org = db.execute("SELECT * FROM organizations WHERE id = ?", (org_id,)).fetchone()
    return Organization(**dict(org))

@router.post("/organizations/{org_id}/credits", response_model=Organization)
def adjust_credits(org_id: int, payload: OrganizationCreditUpdate, db: sqlite3.Connection = Depends(get_db), user=Depends(require_role("owner"))):
    db.execute(
        "UPDATE organizations SET credit_balance = MAX(credit_balance + ?, 0) WHERE id = ?",
        (payload.amount, org_id),
    )
    org = db.execute("SELECT * FROM organizations WHERE id = ?", (org_id,)).fetchone()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return Organization(**dict(org))

@router.post("/users", response_model=User)
def create_user(payload: UserCreate, db: sqlite3.Connection = Depends(get_db), user=Depends(require_role("owner", "admin"))):
    org = db.execute("SELECT * FROM organizations WHERE id = ?", (payload.organization_id,)).fetchone()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    member_count = db.execute(
        "SELECT COUNT(*) FROM users WHERE organization_id = ?",
        (payload.organization_id,),
    ).fetchone()[0]
    if member_count >= org["max_members"]:
        raise HTTPException(status_code=400, detail="Max members reached for this organization")
    try:
        cur = db.execute(
            "INSERT INTO users (organization_id, email, password_hash, role) VALUES (?, ?, ?, ?)",
            (payload.organization_id, payload.email, hash_password(payload.password), payload.role),
        )
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=400, detail="Email already exists") from exc
    user_row = db.execute("SELECT * FROM users WHERE id = ?", (cur.lastrowid,)).fetchone()
    return User(**dict(user_row))

@router.get("/organizations/{org_id}/users", response_model=list[User])
def list_users(org_id: int, db: sqlite3.Connection = Depends(get_db), user=Depends(require_role("owner", "admin"))):
    rows = db.execute("SELECT * FROM users WHERE organization_id = ?", (org_id,)).fetchall()
    return [User(**dict(row)) for row in rows]
