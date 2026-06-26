"""Ingest tests — focus on the pipeline contract, not the SDK.

We deliberately exercise the in-memory datastore path (CATALYST_ENABLED=false)
so these run fast and offline. The Catalyst path is verified manually in
staging because mocking the full SDK adds more risk than it removes.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from services import datastore
from services.ingest import ingest_file, normalize_row, scrub_pii


@pytest.fixture(autouse=True)
def fresh_repo():
    datastore.reset_for_tests()
    yield
    datastore.reset_for_tests()


SAMPLE = Path(__file__).resolve().parents[1] / "data" / "sample_cases.csv"


def test_sample_file_loads():
    report = ingest_file(SAMPLE)
    assert report.total == 10
    assert report.inserted == 10
    assert report.skipped == 0
    assert report.errors == []


def test_sample_file_redacts_pii():
    report = ingest_file(SAMPLE)
    # The sample includes phones, Aadhaar, PAN, email, vehicle reg in narratives.
    # We expect every one to be caught.
    assert report.pii_findings >= 5


def test_normalize_rejects_missing_fields():
    with pytest.raises(ValueError, match="missing required field"):
        normalize_row({"case_id": "X"})  # only one field present


def test_scrub_pii_redacts_narrative_phone():
    row = {
        "case_id": "T-1",
        "crime_type": "theft",
        "locality": "HSR",
        "occurred_on": "2025-01-01",
        "status": "open",
        "narrative": "Victim phone 9845012345.",
    }
    case = normalize_row(row)
    case, findings = scrub_pii(case)
    assert "9845012345" not in case.narrative
    # scrub_pii returns a count of redactions, not the findings themselves.
    assert findings >= 1


def test_scrub_pii_leaves_clean_narrative_alone():
    row = {
        "case_id": "T-2",
        "crime_type": "theft",
        "locality": "HSR",
        "occurred_on": "2025-01-01",
        "status": "open",
        "narrative": "No identifying details.",
    }
    case = normalize_row(row)
    new_case, findings = scrub_pii(case)
    assert new_case.narrative == "No identifying details."
    assert findings == 0
