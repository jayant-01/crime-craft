"""Case service.

Thin layer that owns role-based redaction. All persistence goes through the
datastore module so we don't care whether we're on Catalyst or in-memory.
"""

from __future__ import annotations

from models import Case, PublicCaseView, Role
from services.datastore import case_repo


def redact_for_role(case: Case, role: Role) -> Case | PublicCaseView:
    """Single chokepoint for field-level redaction. Add fields here, not in routes."""
    if role == Role.PUBLIC:
        return PublicCaseView(
            case_id=case.case_id,
            crime_type=case.crime_type,
            locality=case.locality,
            occurred_on=case.occurred_on,
            status=case.status,
        )
    return case


def list_cases(role: Role, limit: int = 50, offset: int = 0) -> list[Case | PublicCaseView]:
    return [redact_for_role(c, role) for c in case_repo().list(limit=limit, offset=offset)]


def get_case(case_id: str, role: Role) -> Case | PublicCaseView | None:
    found = case_repo().get(case_id)
    return None if found is None else redact_for_role(found, role)


def upsert_case(case: Case) -> None:
    """Used by the ingest pipeline (Phase 1)."""
    case_repo().upsert(case)
