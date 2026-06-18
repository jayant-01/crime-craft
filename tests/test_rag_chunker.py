"""Chunker tests. Focus is on what's classified as what — that drives role-based
retrieval, so a regression here would silently leak SENSITIVE chunks to public users."""

from __future__ import annotations

from datetime import date

from models import Case, CaseStatus, Classification
from services.rag.chunker import chunk_case


def _case(**overrides) -> Case:
    base = dict(
        case_id="FIR-2025-1001",
        crime_type="theft",
        locality="HSR Layout",
        street_address=None,
        occurred_on=date(2025, 11, 14),
        status=CaseStatus.UNDER_INVESTIGATION,
        mo_details="forced entry via balcony",
        victim_names=[],
        suspect_names=[],
        phone_numbers=[],
        narrative="CCTV under review.",
    )
    base.update(overrides)
    return Case(**base)


class TestClassification:
    def test_summary_is_open(self):
        chunks = chunk_case(_case())
        summary = [c for c in chunks if c.field == "summary"]
        assert len(summary) == 1
        assert summary[0].classification == Classification.OPEN

    def test_mo_and_narrative_are_sensitive(self):
        chunks = chunk_case(_case())
        for c in chunks:
            if c.field in {"mo", "narrative"}:
                assert c.classification == Classification.SENSITIVE


class TestPayloadShape:
    def test_summary_text_includes_open_facts_only(self):
        case = _case()
        summary = next(c for c in chunk_case(case) if c.field == "summary")
        assert case.case_id in summary.text
        assert case.crime_type in summary.text
        assert case.locality in summary.text
        # MO detail should NOT appear in the OPEN summary chunk.
        assert "forced entry" not in summary.text.lower()

    def test_metadata_includes_filterable_fields(self):
        chunks = chunk_case(_case())
        for c in chunks:
            for key in ("locality", "crime_type", "status", "occurred_on"):
                assert key in c.metadata

    def test_chunk_ids_are_unique_per_field(self):
        chunks = chunk_case(_case())
        ids = [c.chunk_id for c in chunks]
        assert len(ids) == len(set(ids))


class TestEdgeCases:
    def test_missing_optional_fields_skipped(self):
        case = _case(mo_details=None, narrative=None)
        chunks = chunk_case(case)
        fields = {c.field for c in chunks}
        assert fields == {"summary"}

    def test_no_pii_in_any_chunk(self):
        # Even if a case has structured PII, the chunker must not include it.
        case = _case(
            victim_names=["Ramesh Kumar"],
            suspect_names=["Unknown"],
            phone_numbers=["9845012345"],
        )
        chunks = chunk_case(case)
        for c in chunks:
            assert "Ramesh" not in c.text
            assert "9845012345" not in c.text
