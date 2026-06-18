"""Case → chunks.

Each chunk is one passage to embed. We split a Case into a handful of small
chunks rather than one big one so retrieval can pinpoint *which part* of a
case matched (summary vs MO vs narrative).

Every chunk carries:
  - the case_id it belongs to
  - a classification tag (OPEN | SENSITIVE)
  - filterable metadata (locality, crime_type, status, occurred_on)

PII-classified fields (names, phones, Aadhaar) are NEVER chunked. They live
in the structured columns and are retrieved by case_id, not by embedding
similarity — searching by vector for "Ramesh Kumar" is both unhelpful and
unsafe.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from models import Case, Classification


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    case_id: str
    text: str
    field: str  # "summary" | "mo" | "narrative"
    classification: Classification
    metadata: dict[str, Any]


def chunk_case(case: Case) -> list[Chunk]:
    base_meta: dict[str, Any] = {
        "locality": case.locality,
        "crime_type": case.crime_type,
        "status": case.status.value,
        "occurred_on": case.occurred_on.isoformat(),
    }

    chunks: list[Chunk] = [
        # Summary is OPEN — citizens can retrieve this.
        Chunk(
            chunk_id=f"{case.case_id}::summary",
            case_id=case.case_id,
            text=(
                f"Case {case.case_id}: {case.crime_type} in {case.locality} "
                f"on {case.occurred_on.isoformat()}. Status: {case.status.value}."
            ),
            field="summary",
            classification=Classification.OPEN,
            metadata=base_meta,
        )
    ]

    if case.mo_details:
        chunks.append(
            Chunk(
                chunk_id=f"{case.case_id}::mo",
                case_id=case.case_id,
                text=f"MO: {case.mo_details}",
                field="mo",
                classification=Classification.SENSITIVE,
                metadata=base_meta,
            )
        )

    if case.narrative:
        chunks.append(
            Chunk(
                chunk_id=f"{case.case_id}::narrative",
                case_id=case.case_id,
                text=f"Narrative: {case.narrative}",
                field="narrative",
                classification=Classification.SENSITIVE,
                metadata=base_meta,
            )
        )

    return chunks
