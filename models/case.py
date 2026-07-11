from datetime import date
from enum import Enum
from pydantic import BaseModel, Field


class Classification(str, Enum):
    """Field-level visibility. Public sees OPEN only; officers see all."""
    OPEN = "open"
    SENSITIVE = "sensitive"
    PII = "pii"


class CaseStatus(str, Enum):
    OPEN = "open"
    UNDER_INVESTIGATION = "under_investigation"
    CHARGESHEETED = "chargesheeted"
    CLOSED = "closed"


class Case(BaseModel):
    """Canonical case record. The redaction layer decides which fields ship to the client based on caller role."""

    case_id: str = Field(..., description="FIR / case reference")
    crime_type: str  # OPEN
    locality: str  # OPEN — broad area only (e.g. ward)
    street_address: str | None = None  # SENSITIVE
    occurred_on: date  # OPEN
    status: CaseStatus  # OPEN
    mo_details: str | None = None  # SENSITIVE
    victim_names: list[str] = []  # PII
    suspect_names: list[str] = []  # PII  (KSP: Accused.AccusedName)
    phone_numbers: list[str] = []  # PII
    narrative: str | None = None  # SENSITIVE (post-redaction)  (KSP: BriefFacts)

    # --- Real KSP schema fields (optional; populated by the normalized-source
    # ingest — see docs/KSP_SCHEMA_MAPPING.md and catalyst/datastore-schema.json.
    # Additive so the flat demo projection + existing services/tests are unaffected). ---
    crime_no: str | None = None            # CaseMaster.CrimeNo (18-digit structured)
    case_no: str | None = None             # CaseMaster.CaseNo
    crime_head: str | None = None          # CrimeHead.CrimeGroupName (major)     OPEN
    crime_subhead: str | None = None       # CrimeSubHead.CrimeHeadName (minor)   OPEN
    category: str | None = None            # CaseCategory.LookupValue (FIR/UDR/PAR)
    gravity: str | None = None             # GravityOffence.LookupValue (Heinous/…)
    district: str | None = None            # District.DistrictName                OPEN
    police_station: str | None = None      # Unit.UnitName                        SENSITIVE
    registered_on: date | None = None      # CaseMaster.CrimeRegisteredDate       OPEN
    latitude: float | None = None          # CaseMaster.latitude                  SENSITIVE
    longitude: float | None = None         # CaseMaster.longitude                 SENSITIVE
    complainant_names: list[str] = []      # ComplainantDetails.ComplainantName   PII
    acts_sections: list[str] = []          # ActSectionAssociation → "IPC 302"    SENSITIVE
    chargesheet_type: str | None = None    # ChargesheetDetails.cstype (A/B/C)    SENSITIVE
    investigating_officer_id: str | None = None  # Employee.KGID via IOID          PII


class PublicCaseView(BaseModel):
    """Redacted view safe for public users."""
    case_id: str
    crime_type: str
    locality: str
    occurred_on: date
    status: CaseStatus
