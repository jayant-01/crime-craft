"""Case ingest pipeline.

Flow:
    source file (CSV/JSON)
       → load_rows()              read raw dicts
       → normalize_row()           coerce to typed Case
       → scrub_pii()               run free-text through services.pii
       → upsert_case()             write to datastore (Catalyst in prod)

Used by:
    - the admin `POST /admin/ingest` route (manual upload)
    - the hourly Catalyst Cron function in `functions/ingest_cron/`
    - the CLI entrypoint  `python -m services.ingest <path>`
"""

from __future__ import annotations

import csv
import json
import logging
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable

from models import Case, CaseStatus
from services.cases import upsert_case
from services.pii import redact_text
from services.rag.indexer import index_case

log = logging.getLogger("ingest")


@dataclass
class IngestReport:
    file: str
    total: int
    inserted: int
    skipped: int
    pii_findings: int
    errors: list[str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "file": self.file,
            "total": self.total,
            "inserted": self.inserted,
            "skipped": self.skipped,
            "pii_findings": self.pii_findings,
            "errors": self.errors,
        }


# --- load -----------------------------------------------------------------

def load_rows(path: str | Path) -> Iterable[dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"ingest source not found: {p}")
    if p.suffix.lower() == ".csv":
        with p.open(newline="", encoding="utf-8") as f:
            yield from csv.DictReader(f)
    elif p.suffix.lower() == ".json":
        with p.open(encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            raise ValueError("ingest JSON must be a list of case objects")
        yield from data
    else:
        raise ValueError(f"unsupported ingest format: {p.suffix}")


# --- normalize ------------------------------------------------------------

def _split_list(raw: Any) -> list[str]:
    if raw is None or raw == "":
        return []
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if str(x).strip()]
    return [s.strip() for s in str(raw).split("|") if s.strip()]


def normalize_row(row: dict[str, Any]) -> Case:
    """Coerce a raw source row into a typed Case. Raises ValueError on bad data."""
    try:
        return Case(
            case_id=str(row["case_id"]).strip(),
            crime_type=str(row["crime_type"]).strip().lower(),
            locality=str(row["locality"]).strip(),
            street_address=(row.get("street_address") or None) or None,
            occurred_on=date.fromisoformat(str(row["occurred_on"]).strip()),
            status=CaseStatus(str(row["status"]).strip().lower()),
            mo_details=row.get("mo_details") or None,
            victim_names=_split_list(row.get("victim_names")),
            suspect_names=_split_list(row.get("suspect_names")),
            phone_numbers=_split_list(row.get("phone_numbers")),
            narrative=row.get("narrative") or None,
        )
    except KeyError as e:
        raise ValueError(f"missing required field: {e}") from e


# --- scrub ----------------------------------------------------------------

def scrub_pii(case: Case) -> tuple[Case, int]:
    """Rewrite free-text fields with redacted versions. Structured PII columns
    (names, phones) are left intact — they are PII-classified at the schema
    level and the role-based redactor strips them at read time."""
    total_findings = 0

    new_narrative, f1 = redact_text(case.narrative)
    total_findings += len(f1)
    new_mo, f2 = redact_text(case.mo_details)
    total_findings += len(f2)

    if new_narrative != case.narrative or new_mo != case.mo_details:
        case = case.model_copy(update={"narrative": new_narrative, "mo_details": new_mo})
    return case, total_findings


# --- pipeline -------------------------------------------------------------

def ingest_file(path: str | Path) -> IngestReport:
    report = IngestReport(file=str(path), total=0, inserted=0, skipped=0, pii_findings=0, errors=[])
    for row in load_rows(path):
        report.total += 1
        try:
            case = normalize_row(row)
            case, findings = scrub_pii(case)
            upsert_case(case)
            try:
                index_case(case)  # keep the vector store in sync with the canonical store
            except Exception as ie:  # noqa: BLE001 — indexing is best-effort; don't fail ingest on a vector store hiccup
                log.warning("index_case failed for %s: %s", case.case_id, ie)
            report.inserted += 1
            report.pii_findings += findings
        except Exception as e:  # noqa: BLE001 — we explicitly want to keep going past one bad row
            report.skipped += 1
            report.errors.append(f"row {report.total}: {e}")
            log.warning("ingest row %d failed: %s", report.total, e)
    log.info("ingest done: %s", report.as_dict())
    return report


# --- CLI ------------------------------------------------------------------

def _main(argv: list[str]) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    if len(argv) < 2:
        print("usage: python -m services.ingest <path-to-csv-or-json>", file=sys.stderr)
        return 2
    report = ingest_file(argv[1])
    print(json.dumps(report.as_dict(), indent=2))
    return 0 if not report.errors else 1


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv))
