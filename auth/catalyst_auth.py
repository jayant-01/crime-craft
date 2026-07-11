"""Catalyst-backed auth provider.

Catalyst handles signup/login/MFA/tokens itself. Our job is just to:
  1. read the inbound Authorization header
  2. ask Catalyst "who is this?"
  3. map Catalyst's `user_type` (e.g. 'officer', 'senior_officer') onto our `Role` enum

Provision the user types in the Catalyst console (User Management → Types):
  - public           (default, self-signup)
  - officer          (admin invite, requires KSP officer_id custom attribute)
  - senior_officer   (admin invite, gated)
  - admin            (Crime Craft team)
"""

from __future__ import annotations

import logging

from fastapi import HTTPException, Request, status

from models import Role, User
from services.catalyst_client import get_catalyst

log = logging.getLogger("auth.catalyst")

_USER_TYPE_TO_ROLE: dict[str, Role] = {
    "public": Role.PUBLIC,
    "officer": Role.OFFICER,
    "senior_officer": Role.SENIOR_OFFICER,
    "admin": Role.ADMIN,
}


def _role_from_user_type(user_type: str | None) -> Role:
    if not user_type:
        return Role.PUBLIC
    return _USER_TYPE_TO_ROLE.get(user_type.lower(), Role.PUBLIC)


async def get_user_from_catalyst(request: Request) -> User:
    auth = request.headers.get("authorization")
    if not auth:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing authorization header",
        )

    try:
        app = get_catalyst(request_headers=dict(request.headers))
        current = app.user_management().get_current_user()
    except Exception as e:
        # Log the detail server-side; return a generic message to the client so
        # we don't leak SDK internals.
        log.warning("catalyst auth failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid or expired session",
        ) from e

    # `current` shape per Catalyst SDK: dict with user_id, email_id, user_type, etc.
    return User(
        id=str(current.get("user_id") or current.get("zuid")),
        # EmailStr requires a valid domain — use a valid placeholder if Catalyst
        # returns no email (otherwise User construction would 500).
        email=current.get("email_id") or current.get("email") or "unknown@ksp.gov.in",
        role=_role_from_user_type(current.get("user_type")),
        full_name=f"{current.get('first_name', '')} {current.get('last_name', '')}".strip() or None,
        officer_id=current.get("officer_id"),
    )
