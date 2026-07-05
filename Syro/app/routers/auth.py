from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
import sqlite3

from ..db import get_db
from ..schemas import Token
from ..security import verify_password, create_access_token
from ..security.rate_limiter import auth_rate_limiter

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=Token)
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: sqlite3.Connection = Depends(get_db),
):
    import logging

    logger = logging.getLogger(__name__)

    client_ip = request.client.host if request.client else "unknown"
    key = f"auth:{client_ip}"

    allowed, remaining = auth_rate_limiter.allow(key)
    if not allowed:
        logger.warning("Rate limit exceeded for IP: %s", client_ip)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Try again later.",
            headers={"X-RateLimit-Remaining": "0"},
        )

    user = db.execute(
        "SELECT * FROM users WHERE email = ?",
        (form_data.username,),
    ).fetchone()

    if not user:
        logger.warning("Login failed: user not found (IP: %s)", client_ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )

    if not verify_password(form_data.password, user["password_hash"]):
        logger.warning("Login failed: bad password for user_id=%s", user["id"])
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )

    org = db.execute(
        "SELECT * FROM organizations WHERE id = ?", (user["organization_id"],)
    ).fetchone()
    if not org or org["status"] != "active":
        logger.warning(
            "Login denied: org_id=%s status=%s for user_id=%s",
            user["organization_id"],
            org["status"] if org else "missing",
            user["id"],
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Organization is not active"
        )

    logger.info(
        "Login successful: user_id=%s org_id=%s", user["id"], user["organization_id"]
    )
    token = create_access_token(
        subject=str(user["id"]),
        extra={"org_status": org["status"]},
        user_data={
            "email": user["email"],
            "organization_id": user["organization_id"],
            "role": user["role"],
        },
    )
    return Token(access_token=token)
