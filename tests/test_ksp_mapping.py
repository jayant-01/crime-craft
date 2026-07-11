"""Tests for the KSP ER -> Case projection (services/ksp_mapping).

These exercise the production data-shape (the real KSP FIR ER) without needing a
live Catalyst — we feed row dicts exactly as the ZCQL layer would return them.
"""

from __future__ import annotations

from datetime import date

import pytest

from models import CaseStatus
from services.ksp_mapping import KspCaseBundle, Lookups, project_case


def _lookups() -> Lookups:
    return Lookups(
        crime_head={10: "Crimes Against Property"},
        crime_subhead={101: "Theft", 102: "Murder"},
        status={1: "Under Investigation", 2: "Charge Sheeted", 3: "Closed"},
        unit={5001: {"name": "HSR Layout PS", "district_id": 43}},
        district={43: "Bengaluru South"},
        category={1: "FIR"},
        gravity={2: "Non-Heinous"},
        act={"IPC": "IPC", "NDPS": "NDPS"},
    )


def _case_master(**over) -> dict:
    base = {
        "CaseMasterID": 900001,
        "CrimeNo": "104430006202600001",
        "CaseNo": "202600001",
        "CrimeRegisteredDate": "2026-01-15",
        "IncidentFromDate": "2026-01-14 22:30:00",
        "PoliceStationID": 5001,
        "CaseCategoryID": 1,
        "GravityOffenceID": 2,
        "CrimeMajorHeadID": 10,
        "CrimeMinorHeadID": 101,
        "CaseStatusID": 1,
        "latitude": "12.9116",
        "longitude": "77.6389",
        "BriefFacts": "Jewellery reported missing from a flat.",
    }
    base.update(over)
    return base


def test_full_projection():
    bundle = KspCaseBundle(
        case_master=_case_master(),
        victims=[{"VictimName": "Ramesh Kumar"}, {"VictimName": "unknown"}],
        accused=[{"AccusedName": "Ravi Kumar", "PersonID": "A1"}, {"AccusedName": "REDACTED"}],
        complainants=[{"ComplainantName": "Anita Sharma"}],
        act_sections=[{"ActID": "IPC", "SectionID": "379"}, {"ActID": "IPC", "SectionID": "34"}],
        chargesheet={"cstype": "A"},
    )
    c = project_case(bundle, _lookups())

    assert c.case_id == "104430006202600001"
    assert c.crime_no == "104430006202600001"
    assert c.crime_type == "Theft"             # from CrimeSubHead
    assert c.crime_head == "Crimes Against Property"
    assert c.crime_subhead == "Theft"
    assert c.locality == "Bengaluru South"     # OPEN = district
    assert c.district == "Bengaluru South"
    assert c.police_station == "HSR Layout PS"  # SENSITIVE
    assert c.status == CaseStatus.UNDER_INVESTIGATION
    assert c.occurred_on == date(2026, 1, 14)  # IncidentFromDate wins over registered
    assert c.registered_on == date(2026, 1, 15)
    assert c.latitude == pytest.approx(12.9116)
    assert c.longitude == pytest.approx(77.6389)
    assert c.category == "FIR"
    assert c.gravity == "Non-Heinous"
    assert c.narrative == "Jewellery reported missing from a flat."
    # unknown / REDACTED names are dropped
    assert c.victim_names == ["Ramesh Kumar"]
    assert c.suspect_names == ["Ravi Kumar"]
    assert c.complainant_names == ["Anita Sharma"]
    assert c.acts_sections == ["IPC 379", "IPC 34"]
    assert c.chargesheet_type == "A"


def test_status_variants():
    lk = _lookups()
    assert project_case(KspCaseBundle(_case_master(CaseStatusID=2)), lk).status == CaseStatus.CHARGESHEETED
    assert project_case(KspCaseBundle(_case_master(CaseStatusID=3)), lk).status == CaseStatus.CLOSED
    # unknown status id -> safe default
    assert project_case(KspCaseBundle(_case_master(CaseStatusID=999)), lk).status == CaseStatus.UNDER_INVESTIGATION


def test_date_falls_back_to_registered():
    c = project_case(KspCaseBundle(_case_master(IncidentFromDate=None)), _lookups())
    assert c.occurred_on == date(2026, 1, 15)


def test_missing_date_raises():
    with pytest.raises(ValueError):
        project_case(KspCaseBundle(_case_master(IncidentFromDate=None, CrimeRegisteredDate=None)), _lookups())


def test_unresolved_lookups_degrade_gracefully():
    # Empty lookups -> crime_type unknown, locality Unknown, no crash
    c = project_case(KspCaseBundle(_case_master()), Lookups())
    assert c.crime_type == "unknown"
    assert c.locality == "Unknown"
    assert c.status == CaseStatus.UNDER_INVESTIGATION


def test_case_id_falls_back_to_casemasterid():
    c = project_case(KspCaseBundle(_case_master(CrimeNo=None)), _lookups())
    assert c.case_id == "900001"
