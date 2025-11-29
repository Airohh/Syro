from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
import sqlite3

from ..db import get_db
from ..schemas import Token
from ..security import verify_password, create_access_token
from ..dependencies import enforce_rate_limit
from ..security.rate_limiter import auth_rate_limiter

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login", response_model=Token)
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: sqlite3.Connection = Depends(get_db),
):
    # Log pour debug
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Login attempt for username: {form_data.username}")
    
    # Rate limiting pour l'authentification (utiliser l'IP car on n'a pas encore de user)
    client_ip = request.client.host if request.client else "unknown"
    key = f"auth:{client_ip}"
    
    allowed, remaining = auth_rate_limiter.allow(key)
    if not allowed:
        logger.warning(f"Rate limit exceeded for IP: {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Try again later.",
            headers={"X-RateLimit-Remaining": "0"}
        )
    
    logger.info(f"Looking up user: {form_data.username}")
    user = db.execute(
        "SELECT * FROM users WHERE email = ?",
        (form_data.username,),
    ).fetchone()
    
    if not user:
        logger.warning(f"User not found: {form_data.username}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    
    logger.info(f"User found, verifying password for user ID: {user['id']}")
    if not verify_password(form_data.password, user["password_hash"]):
        logger.warning(f"Invalid password for user: {form_data.username}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    org = db.execute("SELECT * FROM organizations WHERE id = ?", (user["organization_id"],)).fetchone()
    token = create_access_token(
        subject=str(user["id"]),
        extra={"org_status": org["status"]},
        user_data={
            "email": user["email"],
            "organization_id": user["organization_id"],
            "role": user["role"],
        }
    )
    return Token(access_token=token)
