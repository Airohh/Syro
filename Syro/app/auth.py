from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import jwt
from passlib.context import CryptContext

from .config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(
    subject: str,
    extra: Dict[str, Any] | None = None,
    user_data: Dict[str, Any] | None = None,
) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_exp_minutes
    )
    payload: Dict[str, Any] = {"sub": subject, "exp": expire}
    if extra:
        payload.update(extra)
    # Include user data in token for cross-domain authentication
    if user_data:
        payload.update(
            {
                "email": user_data.get("email"),
                "organization_id": user_data.get("organization_id"),
                "role": user_data.get("role"),
            }
        )
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def decode_token(token: str) -> Dict[str, Any]:
    return jwt.decode(token, settings.secret_key, algorithms=["HS256"])
