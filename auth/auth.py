"""Auth facade.

Two modes:
  - CATALYST_ENABLED=true  → delegate to Catalyst User Management (prod, staging)
  - CATALYST_ENABLED=false → local JWT stub (local dev, unit tests, CI)

Routes only ever depend on `get_current_user` / `require_*` — they don't know
which mode is active. That's the point.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from config import get_settings
from models import Role, TokenPayload, User

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)


# --- local JWT stub (dev-only) --------------------------------------------

def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(user_id: str, role: Role) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expiry_minutes)
    payload = {"sub": user_id, "role": role.value, "exp": int(expire.timestamp())}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def _decode_local_token(token: str) -> TokenPayload:
    try:
        raw = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return TokenPayload(**raw)
    except (JWTError, ValueError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid or expired token",
        ) from e


async def _local_get_current_user(token: str | None) -> User:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing token",
        )
    payload = _decode_local_token(token)
    return User(
        id=payload.sub,
        # Synthetic email for the local dev stub. Must be a valid (non-reserved)
        # domain — EmailStr rejects the .test TLD, which would 500 every request.
        email=f"{payload.sub}@ksp.gov.in",
        role=payload.role,
    )


# --- facade ---------------------------------------------------------------

async def get_current_user(
    request: Request,
    token: str | None = Depends(oauth2_scheme),
) -> User:
    if settings.catalyst_enabled:
        # Catalyst path — verified server-side via the SDK.
        from auth.catalyst_auth import get_user_from_catalyst
        return await get_user_from_catalyst(request)
    return await _local_get_current_user(token)


def require_roles(*allowed: Role):
    async def _guard(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"role '{user.role}' not permitted",
            )
        return user

    return _guard


require_officer = require_roles(Role.OFFICER, Role.SENIOR_OFFICER, Role.ADMIN)
require_senior = require_roles(Role.SENIOR_OFFICER, Role.ADMIN)
