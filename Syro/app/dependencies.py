from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
import jwt
import sqlite3

from .db import get_db
# Import depuis app.security.py (ancien module - fichier, pas package)
import importlib.util
from pathlib import Path
_parent = Path(__file__).parent
_security_file = _parent / "security.py"
if _security_file.exists():
    spec = importlib.util.spec_from_file_location("app.security_module", _security_file)
    _security_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(_security_module)
    decode_token = _security_module.decode_token
else:
    # Fallback si le fichier n'existe pas
    from app.security import decode_token

# Import depuis app.security (nouveau package)
from .security.rate_limiter import chat_rate_limiter, doc_upload_rate_limiter, auth_rate_limiter

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_current_user(
    token: str = Depends(oauth2_scheme), db: sqlite3.Connection = Depends(get_db)
):
    try:
        payload = decode_token(token)
    except jwt.PyJWTError as exc:  # type: ignore[attr-defined]
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    # Try to find user in local database
    user = db.execute("SELECT * FROM users WHERE id = ?", (payload["sub"],)).fetchone()
    
    # If user not found locally but token is valid, accept it anyway
    # This allows tokens from other domains to work (shared SECRET_KEY)
    # The token itself is the proof of authentication
    if not user:
        # Token is valid (same SECRET_KEY), so create a minimal user object
        # This allows cross-domain authentication without requiring user in every DB
        from .config import settings
        # Check if SECRET_KEY matches (tokens are only valid if signed with same key)
        # Since decode_token already validated the signature, we can trust the payload
        user = {
            "id": payload["sub"],
            "email": payload.get("email", f"user_{payload['sub']}@cross-domain"),
            "organization_id": payload.get("organization_id", 1),
            "role": payload.get("role", "member"),
            "status": "active"
        }
    
    return user

def get_current_org(user = Depends(get_current_user), db: sqlite3.Connection = Depends(get_db)):
    org = db.execute("SELECT * FROM organizations WHERE id = ?", (user["organization_id"],)).fetchone()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    return org

def require_role(*roles: str):
    def dependency(user=Depends(get_current_user)):
        if user["role"] not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user

    return dependency

def require_active_org(min_credit: int = 1):
    def dependency(org=Depends(get_current_org)):
        if org["status"] != "active":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organization is paused")
        if org["credit_balance"] < min_credit:
            raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="Credit balance too low")
        return org

    return dependency

def enforce_rate_limit(scope: str):
    limiters = {
        "chat": chat_rate_limiter,
        "documents": doc_upload_rate_limiter,
        "auth": auth_rate_limiter,
    }
    limiter = limiters.get(scope, doc_upload_rate_limiter)

    # Pour l'authentification, on ne peut pas utiliser get_current_user car on n'a pas encore de token
    # On utilise l'IP du client comme clé
    if scope == "auth":
        def auth_dependency(request: Request):
            # Utiliser l'IP du client comme clé pour le rate limiting
            client_ip = request.client.host if request.client else "unknown"
            key = f"{scope}:{client_ip}"
            allowed, remaining = limiter.allow(key)
            if not allowed:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded. Try again later.",
                    headers={"X-RateLimit-Remaining": "0"}
                )
            return True
        return auth_dependency

    # Pour les autres scopes, utiliser get_current_user
    def dependency(user=Depends(get_current_user)):
        key = f"{scope}:{user['id']}"
        allowed, remaining = limiter.allow(key)
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Try again later.",
                headers={"X-RateLimit-Remaining": "0"}
            )
        return True

    return dependency