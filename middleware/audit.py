"""Audit middleware.

Every request is logged with caller identity, route, status, latency. We avoid
parsing the token here (the auth layer does that) — but we *do* read whatever
the auth layer attached to `request.state` after running. To keep ordering
simple, we just log a placeholder and let the route handler enrich via
`record_access(...)` if it touched sensitive data.
"""

from __future__ import annotations

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from services.datastore import audit_repo

logger = logging.getLogger("audit")


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Auth dependency stashes the resolved user on request.state (if any).
        user = getattr(request.state, "user", None)
        actor_id = getattr(user, "id", None) if user else None
        actor_role = getattr(user, "role", None).value if user else None  # type: ignore[union-attr]

        record = {
            "actor_id": actor_id,
            "actor_role": actor_role,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "latency_ms": round(elapsed_ms, 2),
        }
        try:
            audit_repo().record(**record)
        except Exception:
            logger.exception("audit write failed")
        logger.info("audit %s", record)
        return response
