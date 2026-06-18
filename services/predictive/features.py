"""Feature engineering for recidivism scoring.

Given a `subject` (a name or alias that appears in `Case.suspect_names`),
collect the cases where they appear and compute a small tabular feature
vector. The features are deliberately interpretable — anything an officer
or auditor must defend in court has to be explainable in plain language.

Features (current set):
  prior_count            : int  — number of prior cases linking to subject
  unique_localities      : int  — number of distinct localities
  unique_crime_types     : int  — number of distinct crime types
  has_violent_crime      : 0/1  — robbery/assault/kidnapping in history
  has_property_crime     : 0/1  — theft/burglary/vehicle theft in history
  days_since_last_case   : int  — recency
  open_or_investigating  : 0/1  — at least one case currently active
"""

from __future__ import annotations

from datetime import date
from typing import Any

from models import Case


VIOLENT = {"robbery", "assault", "kidnapping", "murder"}
PROPERTY = {"theft", "burglary", "vehicle theft", "fraud", "cybercrime"}


def cases_for_subject(subject: str, all_cases: list[Case]) -> list[Case]:
    needle = subject.strip().lower()
    matches = []
    for c in all_cases:
        names = [n.strip().lower() for n in c.suspect_names]
        if needle in names:
            matches.append(c)
    return matches


def extract_features(subject_cases: list[Case], as_of: date | None = None) -> dict[str, Any]:
    if not subject_cases:
        return {
            "prior_count": 0,
            "unique_localities": 0,
            "unique_crime_types": 0,
            "has_violent_crime": 0,
            "has_property_crime": 0,
            "days_since_last_case": -1,
            "open_or_investigating": 0,
        }

    as_of = as_of or max(c.occurred_on for c in subject_cases)
    types = {c.crime_type.lower() for c in subject_cases}
    most_recent = max(c.occurred_on for c in subject_cases)

    return {
        "prior_count": len(subject_cases),
        "unique_localities": len({c.locality for c in subject_cases}),
        "unique_crime_types": len(types),
        "has_violent_crime": int(bool(types & VIOLENT)),
        "has_property_crime": int(bool(types & PROPERTY)),
        "days_since_last_case": (as_of - most_recent).days,
        "open_or_investigating": int(any(
            c.status.value in ("open", "under_investigation") for c in subject_cases
        )),
    }


FEATURE_ORDER: list[str] = [
    "prior_count",
    "unique_localities",
    "unique_crime_types",
    "has_violent_crime",
    "has_property_crime",
    "days_since_last_case",
    "open_or_investigating",
]


def feature_vector(features: dict[str, Any]) -> list[float]:
    return [float(features[k]) for k in FEATURE_ORDER]
