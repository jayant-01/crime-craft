"""Response models for the Crime Map and Person Dossier features."""

from datetime import date

from pydantic import BaseModel

from .case import CaseStatus


class MapPoint(BaseModel):
    case_id: str
    crime_type: str
    locality: str
    status: CaseStatus
    occurred_on: date
    lat: float
    lng: float


class MapResponse(BaseModel):
    points: list[MapPoint]
    total: int


class DossierCase(BaseModel):
    case_id: str
    crime_type: str
    locality: str
    occurred_on: date
    status: CaseStatus


class PersonDossier(BaseModel):
    name: str
    case_count: int
    localities: list[str]
    crime_types: list[str]
    co_accused: list[str]
    first_seen: date | None = None
    last_seen: date | None = None
    recidivism_band: str | None = None
    recidivism_score: float | None = None
    cases: list[DossierCase]
