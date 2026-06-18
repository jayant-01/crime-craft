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
    suspect_names: list[str] = []  # PII
    phone_numbers: list[str] = []  # PII
    narrative: str | None = None  # SENSITIVE (post-redaction)


class PublicCaseView(BaseModel):
    """Redacted view safe for public users."""
    case_id: str
    crime_type: str
    locality: str
    occurred_on: date
    status: CaseStatus
