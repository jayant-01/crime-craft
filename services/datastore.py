"""Datastore abstraction.

Catalyst Datastore has a table API ("ROWS"): you fetch a Table object by name,
then call .insert_row / .get_row / .get_paged_rows / .execute_zcql_query.

We hide that behind a thin repository interface so:
  - routes never touch the SDK
  - tests can swap in an in-memory implementation
  - if we ever outgrow Catalyst Datastore (unlikely for 1100 cases), we swap once

Two case-repo backends:
  - InMemoryCaseRepo  — dev/tests/demo; flat synthetic `Case` rows (data/demo_cases.csv)
  - CatalystCaseRepo  — production; reads the real KSP FIR ER (CaseMaster + child +
    lookup tables, see catalyst/datastore-schema.json) and projects to `Case` via
    services.ksp_mapping. Read-only — KSP seed the ER directly.

Other tables (catalyst/datastore-schema.json): AuditLog, Conversations, CaseEmbeddings.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Protocol

from config import get_settings
from models import Case, CaseStatus
from services.catalyst_client import get_catalyst, datastore_enabled
from services.ksp_mapping import KspCaseBundle, Lookups, project_case

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
        client_ip: str | None = None,
    ) -> None: ...


# --- in-memory implementations (local dev / tests) ------------------------

def _load_demo_seed() -> list[Case]:
    """Load data/demo_cases.csv through the real normalize + scrub pipeline so
    the dev server boots with a corpus the dashboards can chart. Falls back to
    the single built-in case if the file is missing or unreadable."""
    from pathlib import Path

    csv_path = Path(__file__).resolve().parents[1] / "data" / "demo_cases.csv"
    if not csv_path.exists():
        return list(InMemoryCaseRepo._SEED)
    try:
        # Lazy import: services.ingest imports this module, so importing it at
        # module load would be circular. By call time everything is loaded.
        from services.ingest import load_rows, normalize_row, scrub_pii

        out: list[Case] = []
        for row in load_rows(csv_path):
            try:
                case, _ = scrub_pii(normalize_row(row))
                out.append(case)
            except Exception:
                continue  # skip a bad row, keep the rest
        return out or list(InMemoryCaseRepo._SEED)
    except Exception:
        return list(InMemoryCaseRepo._SEED)


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

    def __init__(self, seed: bool = True) -> None:
        # `seed=True` boots `make dev` with the demo corpus so the dashboards,
        # network graph and recidivism screens have data to chart; tests pass
        # `seed=False` for a clean slate (see reset_for_tests).
        cases = _load_demo_seed() if seed else []
        self._rows: dict[str, Case] = {c.case_id: c for c in cases}

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

def _zcql_literal(value: str) -> str:
    """Escape a value for safe interpolation inside a single-quoted ZCQL string
    literal (strip control chars, double single quotes) — prevents ZCQL injection
    via user-controlled ids."""
    cleaned = "".join(ch for ch in str(value) if ch >= " " and ch != "\x7f")
    return cleaned.replace("'", "''")


class CatalystCaseRepo:
    """Reads the **real KSP FIR ER** (CaseMaster + child + lookup tables — see
    catalyst/datastore-schema.json) that KSP seed in production, and projects each
    FIR into the app's flat `Case` model via services.ksp_mapping.

    Note: this reads across ~10 ER tables via ZCQL. The projection logic is unit-
    tested (tests/test_ksp_mapping.py); the ZCQL execution below is exercised only
    against a live Catalyst project — verify on first deploy.
    """

    _lookups_cache: Lookups | None = None

    # --- ZCQL helpers ---
    @staticmethod
    def _zcql(query: str) -> list[dict[str, Any]]:
        rows = get_catalyst().datastore().execute_zcql_query(query)
        return rows or []

    @staticmethod
    def _unwrap(row: dict[str, Any], table: str) -> dict[str, Any]:
        # ZCQL wraps each row under its table name (esp. for joins).
        return row.get(table, row)

    @staticmethod
    def _in_clause(ids: list[Any]) -> str:
        # CaseMasterIDs are integers — coerce so this can't be an injection vector.
        return ",".join(str(int(i)) for i in ids if str(i).lstrip("-").isdigit())

    def _load_lookups(self) -> Lookups:
        if CatalystCaseRepo._lookups_cache is not None:
            return CatalystCaseRepo._lookups_cache
        lk = Lookups()
        for r in self._zcql("SELECT CrimeHeadID, CrimeGroupName FROM CrimeHead"):
            d = self._unwrap(r, "CrimeHead"); lk.crime_head[d.get("CrimeHeadID")] = d.get("CrimeGroupName")
        for r in self._zcql("SELECT CrimeSubHeadID, CrimeHeadName FROM CrimeSubHead"):
            d = self._unwrap(r, "CrimeSubHead"); lk.crime_subhead[d.get("CrimeSubHeadID")] = d.get("CrimeHeadName")
        for r in self._zcql("SELECT CaseStatusID, CaseStatusName FROM CaseStatusMaster"):
            d = self._unwrap(r, "CaseStatusMaster"); lk.status[d.get("CaseStatusID")] = d.get("CaseStatusName")
        for r in self._zcql("SELECT UnitID, UnitName, DistrictID FROM Unit"):
            d = self._unwrap(r, "Unit"); lk.unit[d.get("UnitID")] = {"name": d.get("UnitName"), "district_id": d.get("DistrictID")}
        for r in self._zcql("SELECT DistrictID, DistrictName FROM District"):
            d = self._unwrap(r, "District"); lk.district[d.get("DistrictID")] = d.get("DistrictName")
        for r in self._zcql("SELECT CaseCategoryID, LookupValue FROM CaseCategory"):
            d = self._unwrap(r, "CaseCategory"); lk.category[d.get("CaseCategoryID")] = d.get("LookupValue")
        for r in self._zcql("SELECT GravityOffenceID, LookupValue FROM GravityOffence"):
            d = self._unwrap(r, "GravityOffence"); lk.gravity[d.get("GravityOffenceID")] = d.get("LookupValue")
        for r in self._zcql("SELECT ActCode, ShortName FROM Act"):
            d = self._unwrap(r, "Act"); lk.act[d.get("ActCode")] = d.get("ShortName") or d.get("ActCode")
        CatalystCaseRepo._lookups_cache = lk
        return lk

    def _children_for(self, case_ids: list[Any]) -> dict[Any, dict[str, list]]:
        """Fetch victim/accused/complainant/act-section rows for a set of
        CaseMasterIDs, grouped by CaseMasterID."""
        grouped: dict[Any, dict[str, list]] = {
            cid: {"victims": [], "accused": [], "complainants": [], "act_sections": []} for cid in case_ids
        }
        ids = self._in_clause(case_ids)
        if not ids:
            return grouped
        for table, key in (("Victim", "victims"), ("Accused", "accused"),
                           ("ComplainantDetails", "complainants"), ("ActSectionAssociation", "act_sections")):
            for r in self._zcql(f"SELECT * FROM {table} WHERE CaseMasterID IN ({ids})"):
                d = self._unwrap(r, table)
                cid = d.get("CaseMasterID")
                if cid in grouped:
                    grouped[cid][key].append(d)
        return grouped

    def _bundle(self, cm: dict[str, Any], children: dict[str, list]) -> KspCaseBundle:
        return KspCaseBundle(
            case_master=cm,
            victims=children.get("victims", []),
            accused=children.get("accused", []),
            complainants=children.get("complainants", []),
            act_sections=children.get("act_sections", []),
        )

    def list(self, limit: int = 50, offset: int = 0) -> list[Case]:
        limit, offset = int(limit), int(offset)
        span = f"{offset}, {limit}" if offset else f"{limit}"
        masters = [self._unwrap(r, "CaseMaster")
                   for r in self._zcql(f"SELECT * FROM CaseMaster ORDER BY CrimeRegisteredDate DESC LIMIT {span}")]
        case_ids = [m.get("CaseMasterID") for m in masters if m.get("CaseMasterID") is not None]
        children = self._children_for(case_ids)
        lk = self._load_lookups()
        out: list[Case] = []
        for m in masters:
            try:
                out.append(project_case(self._bundle(m, children.get(m.get("CaseMasterID"), {})), lk))
            except Exception:  # noqa: BLE001 — skip a malformed FIR rather than fail the whole list
                continue
        return out

    def get(self, case_id: str) -> Case | None:
        rows = self._zcql(
            f"SELECT * FROM CaseMaster WHERE CrimeNo = '{_zcql_literal(case_id)}'"
        )
        if not rows:
            return None
        cm = self._unwrap(rows[0], "CaseMaster")
        cid = cm.get("CaseMasterID")
        children = self._children_for([cid]).get(cid, {})
        try:
            return project_case(self._bundle(cm, children), self._load_lookups())
        except Exception:  # noqa: BLE001
            return None

    def upsert(self, case: Case) -> None:
        # KSP seed the ER tables directly via their own ETL; the app is read-only
        # against the KSP corpus. Writing a flat Case back across ~7 normalized
        # tables would be lossy, so we fail loudly instead of corrupting data.
        raise NotImplementedError(
            "CatalystCaseRepo is read-only: KSP seed the FIR ER tables directly. "
            "Use the in-memory repo (CATALYST_ENABLED=false) for dev ingest."
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
        _case_repo = CatalystCaseRepo() if datastore_enabled() else InMemoryCaseRepo()
    return _case_repo


def audit_repo() -> AuditRepository:
    global _audit_repo
    if _audit_repo is None:
        _audit_repo = CatalystAuditRepo() if datastore_enabled() else InMemoryAuditRepo()
    return _audit_repo


def reset_for_tests() -> None:
    # Tests assume a clean, empty datastore — bypass the demo seed so
    # counts/aggregates start from zero. Always in-memory under test.
    global _case_repo, _audit_repo
    _case_repo = InMemoryCaseRepo(seed=False)
    _audit_repo = InMemoryAuditRepo()
