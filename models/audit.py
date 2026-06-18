from datetime import datetime
from pydantic import BaseModel


class AuditEntry(BaseModel):
    ts: datetime
    actor_id: str | None
    actor_role: str | None
    method: str
    path: str
    status_code: int
    latency_ms: float
    reason: str | None = None
    client_ip: str | None = None
