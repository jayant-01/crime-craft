"""Datastore abstraction.

Catalyst Datastore has a table API ("ROWS"): you fetch a Table object by name,
then call .insert_row / .get_row / .get_paged_rows / .execute_zcql_query.

We hide that behind a thin repository interface so:
  - routes never touch the SDK
  - tests can swap in an in-memory implementation
  - if we ever outgrow Catalyst Datastore (unlikely for 1100 cases), we swap once

Tables (defined in catalyst/datastore-schema.json):
  - Cases
  - AuditLog
  - CaseEmbeddings (Phase 1)
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Protocol

from config import get_settings
from models import Case, CaseStatus
from services.catalyst_client import get_catalyst, is_enabled as catalyst_enabled

_settings = get_settings()


class CaseRepository(Protocol):
    def list(self, limit: int = 50, offset: int = 0) -> list[Case]: ...
    def get(self, case_id: str) -> Case | None: ...
    def upsert(self, case: Case) -> None: ...


class AuditRepository(Protocol):
    def record(
        self,
        *,
        actor_id: str | None,
        actor_role: str | None,
        method: str,
        path: str,
        status_code: int,
        latency_ms: float,
        reason: str | None = None,
    ) -> None: ...


# --- in-memory implementations (local dev / tests) ------------------------

class InMemoryCaseRepo:
    _SEED: list[Case] = [
        Case(
            case_id="FIR-2025-0001",
            crime_type="theft",
            locality="HSR Layout",
            street_address="27th Main, Sector 2",
            occurred_on=date(2025, 11, 14),
            status=CaseStatus.UNDER_INVESTIGATION,
            mo_details="forced entry via balcony",
            victim_names=["REDACTED"],
            suspect_names=["REDACTED"],
            phone_numbers=[],
            narrative="Theft reported by resident; CCTV under review.",
        ),
    ]

    def __init__(self) -> None:
        self._rows: dict[str, Case] = {c.case_id: c for c in self._SEED}

    def list(self, limit: int = 50, offset: int = 0) -> list[Case]:
        return list(self._rows.values())[offset : offset + limit]

    def get(self, case_id: str) -> Case | None:
        return self._rows.get(case_id)

    def upsert(self, case: Case) -> None:
        self._rows[case.case_id] = case


class InMemoryAuditRepo:
    def __init__(self) -> None:
        self._rows: list[dict[str, Any]] = []

    def record(self, **kwargs: Any) -> None:
        self._rows.append({"ts": datetime.utcnow().isoformat(), **kwargs})

    def all(self) -> list[dict[str, Any]]:  # test helper
        return list(self._rows)


# --- Catalyst implementations ---------------------------------------------

class CatalystCaseRepo:
    TABLE = "Cases"

    def _table(self):
        return get_catalyst().datastore().table(self.TABLE)

    def list(self, limit: int = 50, offset: int = 0) -> list[Case]:
        rows = self._table().get_paged_rows(max_rows=limit, next_token=None)
        items = rows.get("data", []) if isinstance(rows, dict) else rows
        return [self._row_to_case(r) for r in items[offset : offset + limit]]

    def get(self, case_id: str) -> Case | None:
        ds = get_catalyst().datastore()
        # Cases table is keyed on case_id (column), not ROWID — use ZCQL.
        rows = ds.execute_zcql_query(f"SELECT * FROM {self.TABLE} WHERE case_id = '{case_id}'")
        if not rows:
            return None
        return self._row_to_case(rows[0].get(self.TABLE, rows[0]))

    def upsert(self, case: Case) -> None:
        self._table().insert_row(self._case_to_row(case))

    @staticmethod
    def _case_to_row(case: Case) -> dict[str, Any]:
        return {
            "case_id": case.case_id,
            "crime_type": case.crime_type,
            "locality": case.locality,
            "street_address": case.street_address,
            "occurred_on": case.occurred_on.isoformat(),
            "status": case.status.value,
            "mo_details": case.mo_details,
            "victim_names": ",".join(case.victim_names),
            "suspect_names": ",".join(case.suspect_names),
            "phone_numbers": ",".join(case.phone_numbers),
            "narrative": case.narrative,
        }

    @staticmethod
    def _row_to_case(row: dict[str, Any]) -> Case:
        return Case(
            case_id=row["case_id"],
            crime_type=row["crime_type"],
            locality=row["locality"],
            street_address=row.get("street_address"),
            occurred_on=date.fromisoformat(row["occurred_on"]),
            status=CaseStatus(row["status"]),
            mo_details=row.get("mo_details"),
            victim_names=[s for s in (row.get("victim_names") or "").split(",") if s],
            suspect_names=[s for s in (row.get("suspect_names") or "").split(",") if s],
            phone_numbers=[s for s in (row.get("phone_numbers") or "").split(",") if s],
            narrative=row.get("narrative"),
        )


class CatalystAuditRepo:
    TABLE = "AuditLog"

    def record(self, **kwargs: Any) -> None:
        row = {"ts": datetime.utcnow().isoformat(), **kwargs}
        try:
            get_catalyst().datastore().table(self.TABLE).insert_row(row)
        except Exception:
            # Audit must never break a request — log to stderr as last resort.
            import logging
            logging.getLogger("audit").exception("audit write failed: %s", row)


# --- factory --------------------------------------------------------------

_case_repo: CaseRepository | None = None
_audit_repo: AuditRepository | None = None


def case_repo() -> CaseRepository:
    global _case_repo
    if _case_repo is None:
        _case_repo = CatalystCaseRepo() if catalyst_enabled() else InMemoryCaseRepo()
    return _case_repo


def audit_repo() -> AuditRepository:
    global _audit_repo
    if _audit_repo is None:
        _audit_repo = CatalystAuditRepo() if catalyst_enabled() else InMemoryAuditRepo()
    return _audit_repo


def reset_for_tests() -> None:
    global _case_repo, _audit_repo
    _case_repo = None
    _audit_repo = None
