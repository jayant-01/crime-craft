"""Project KSP FIR ER rows into the app's flat `Case` model.

KSP seed their real (confidential) data directly into the normalized ER tables
in production (see catalyst/datastore-schema.json and docs/KSP_SCHEMA_MAPPING.md).
Every app service consumes the flat `Case` model, so this module is the single
mapping layer: given a `CaseMaster` row + its child/lookup rows, produce a `Case`.

It is deliberately **pure** (no I/O) so it can be unit-tested without a live
Catalyst — the Catalyst ZCQL layer (services/datastore.CatalystCaseRepo) just
fetches rows and hands them here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from models import Case, CaseStatus


# --- coercion helpers -----------------------------------------------------

def _to_date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    s = str(value).strip().replace("Z", "")
    try:
        return datetime.fromisoformat(s).date()
    except ValueError:
        try:
            return date.fromisoformat(s[:10])
        except ValueError:
            return None


def _to_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


_STATUS_MAP = {
    "under investigation": CaseStatus.UNDER_INVESTIGATION,
    "under_investigation": CaseStatus.UNDER_INVESTIGATION,
    "investigation": CaseStatus.UNDER_INVESTIGATION,
    "charge sheeted": CaseStatus.CHARGESHEETED,
    "chargesheeted": CaseStatus.CHARGESHEETED,
    "charge-sheeted": CaseStatus.CHARGESHEETED,
    "closed": CaseStatus.CLOSED,
    "disposed": CaseStatus.CLOSED,
    "open": CaseStatus.OPEN,
    "registered": CaseStatus.OPEN,
}


def _status_from_name(name: str | None) -> CaseStatus:
    if not name:
        return CaseStatus.UNDER_INVESTIGATION
    return _STATUS_MAP.get(str(name).strip().lower(), CaseStatus.UNDER_INVESTIGATION)


def _names(rows: list[dict[str, Any]], key: str) -> list[str]:
    out: list[str] = []
    for r in rows:
        v = (r.get(key) or "").strip()
        if v and v.lower() not in ("unknown", "redacted"):
            out.append(v)
    return out


# --- lookup + bundle containers -------------------------------------------

@dataclass
class Lookups:
    """id -> display maps for the KSP reference/lookup tables."""
    crime_head: dict[Any, str] = field(default_factory=dict)     # CrimeHeadID -> CrimeGroupName
    crime_subhead: dict[Any, str] = field(default_factory=dict)  # CrimeSubHeadID -> CrimeHeadName
    status: dict[Any, str] = field(default_factory=dict)         # CaseStatusID -> CaseStatusName
    unit: dict[Any, dict] = field(default_factory=dict)          # UnitID -> {"name":..., "district_id":...}
    district: dict[Any, str] = field(default_factory=dict)       # DistrictID -> DistrictName
    category: dict[Any, str] = field(default_factory=dict)       # CaseCategoryID -> LookupValue
    gravity: dict[Any, str] = field(default_factory=dict)        # GravityOffenceID -> LookupValue
    act: dict[Any, str] = field(default_factory=dict)            # ActCode -> ShortName

    def unit_name(self, unit_id: Any) -> str | None:
        u = self.unit.get(unit_id)
        return u.get("name") if u else None

    def district_of_unit(self, unit_id: Any) -> str | None:
        u = self.unit.get(unit_id)
        return self.district.get(u.get("district_id")) if u else None


@dataclass
class KspCaseBundle:
    """A CaseMaster row plus its related child rows for one FIR."""
    case_master: dict[str, Any]
    victims: list[dict[str, Any]] = field(default_factory=list)
    accused: list[dict[str, Any]] = field(default_factory=list)
    complainants: list[dict[str, Any]] = field(default_factory=list)
    act_sections: list[dict[str, Any]] = field(default_factory=list)  # {"ActID":..., "SectionID":...}
    chargesheet: dict[str, Any] | None = None


# --- projection -----------------------------------------------------------

def project_case(bundle: KspCaseBundle, lookups: Lookups) -> Case:
    """Build a flat `Case` from a KSP ER bundle. Raises ValueError if the case
    has no usable date (the caller should skip such rows rather than crash)."""
    cm = bundle.case_master

    head = lookups.crime_head.get(cm.get("CrimeMajorHeadID"))
    subhead = lookups.crime_subhead.get(cm.get("CrimeMinorHeadID"))
    crime_type = subhead or head or "unknown"

    station_id = cm.get("PoliceStationID")
    district = lookups.district_of_unit(station_id)
    police_station = lookups.unit_name(station_id)

    occurred = _to_date(cm.get("IncidentFromDate")) or _to_date(cm.get("CrimeRegisteredDate"))
    if occurred is None:
        raise ValueError(f"CaseMaster {cm.get('CaseMasterID')} has no incident/registration date")

    acts_sections = [
        f"{lookups.act.get(a.get('ActID'), a.get('ActID'))} {a.get('SectionID') or ''}".strip()
        for a in bundle.act_sections
        if a.get("ActID") or a.get("SectionID")
    ]

    return Case(
        case_id=str(cm.get("CrimeNo") or cm.get("CaseMasterID")),
        crime_type=str(crime_type),
        locality=district or "Unknown",          # OPEN: broad area = district
        street_address=None,
        occurred_on=occurred,
        status=_status_from_name(lookups.status.get(cm.get("CaseStatusID"))),
        mo_details=None,
        victim_names=_names(bundle.victims, "VictimName"),
        suspect_names=_names(bundle.accused, "AccusedName"),
        phone_numbers=[],
        narrative=cm.get("BriefFacts"),
        # additive KSP fields
        crime_no=cm.get("CrimeNo"),
        case_no=cm.get("CaseNo"),
        crime_head=head,
        crime_subhead=subhead,
        category=lookups.category.get(cm.get("CaseCategoryID")),
        gravity=lookups.gravity.get(cm.get("GravityOffenceID")),
        district=district,
        police_station=police_station,
        registered_on=_to_date(cm.get("CrimeRegisteredDate")),
        latitude=_to_float(cm.get("latitude")),
        longitude=_to_float(cm.get("longitude")),
        complainant_names=_names(bundle.complainants, "ComplainantName"),
        acts_sections=acts_sections,
        chargesheet_type=(bundle.chargesheet or {}).get("cstype"),
    )
