"""Recidivism scoring tests. We test the stub path end-to-end and the feature
extractor independently. The live XGBoost path is verified manually after
running `python -m services.predictive.train`."""

from __future__ import annotations

from datetime import date

import pytest

from models import Case, CaseStatus, RiskBand
from services import datastore
from services.predictive import score_subject
from services.predictive.features import cases_for_subject, extract_features
from services.predictive import model as model_module


@pytest.fixture(autouse=True)
def fresh_state():
    datastore.reset_for_tests()
    model_module.reset_for_tests()
    yield
    datastore.reset_for_tests()
    model_module.reset_for_tests()


def _case(case_id: str, *, suspects: list[str], crime: str = "theft",
          locality: str = "HSR Layout", occurred: date = date(2025, 11, 1),
          status: CaseStatus = CaseStatus.UNDER_INVESTIGATION) -> Case:
    return Case(
        case_id=case_id,
        crime_type=crime,
        locality=locality,
        occurred_on=occurred,
        status=status,
        suspect_names=suspects,
    )


class TestFeatureExtraction:
    def test_empty_when_no_cases(self):
        f = extract_features([])
        assert f["prior_count"] == 0
        assert f["has_violent_crime"] == 0

    def test_counts_priors(self):
        cases = [_case("a", suspects=["x"]), _case("b", suspects=["x"]), _case("c", suspects=["x"])]
        f = extract_features(cases)
        assert f["prior_count"] == 3

    def test_detects_violent_crime(self):
        cases = [_case("a", suspects=["x"], crime="robbery")]
        f = extract_features(cases)
        assert f["has_violent_crime"] == 1

    def test_detects_open_status(self):
        cases = [_case("a", suspects=["x"], status=CaseStatus.CLOSED)]
        assert extract_features(cases)["open_or_investigating"] == 0
        cases = [_case("a", suspects=["x"], status=CaseStatus.OPEN)]
        assert extract_features(cases)["open_or_investigating"] == 1

    def test_unique_localities(self):
        cases = [
            _case("a", suspects=["x"], locality="HSR Layout"),
            _case("b", suspects=["x"], locality="Indiranagar"),
            _case("c", suspects=["x"], locality="HSR Layout"),
        ]
        assert extract_features(cases)["unique_localities"] == 2


class TestSubjectFilter:
    def test_match_is_case_insensitive(self):
        cases = [_case("a", suspects=["Ravi Kumar"])]
        assert cases_for_subject("ravi kumar", cases) == cases
        assert cases_for_subject("RAVI KUMAR", cases) == cases

    def test_no_partial_match(self):
        cases = [_case("a", suspects=["Ravi Kumar"])]
        # We want exact-name matching to avoid false positives on shared names.
        assert cases_for_subject("Ravi", cases) == []


class TestScoreSubject:
    def test_no_history_returns_low_band(self):
        resp = score_subject("nobody")
        assert resp.band == RiskBand.LOW
        assert resp.score == 0.0
        assert resp.case_count == 0
        assert "KNOWN offenders" in resp.decision_note

    def test_single_minor_case_returns_low_band(self):
        datastore.case_repo().upsert(_case("a", suspects=["ravi"], crime="theft"))
        resp = score_subject("ravi")
        assert resp.case_count == 1
        assert resp.band in (RiskBand.LOW, RiskBand.MEDIUM)

    def test_violent_history_raises_band(self):
        for i in range(3):
            datastore.case_repo().upsert(_case(f"v{i}", suspects=["bashir"], crime="robbery"))
        resp = score_subject("bashir")
        assert resp.band in (RiskBand.MEDIUM, RiskBand.HIGH)
        assert any(c.name == "has_violent_crime" for c in resp.top_contributions)

    def test_decision_note_always_advisory(self):
        datastore.case_repo().upsert(_case("a", suspects=["ravi"]))
        resp = score_subject("ravi")
        assert "ADVISORY" in resp.decision_note.upper()

    def test_explanation_text_human_readable(self):
        for i in range(3):
            datastore.case_repo().upsert(_case(f"a{i}", suspects=["ravi"]))
        resp = score_subject("ravi")
        for c in resp.top_contributions:
            assert c.explanation, "every contribution must have a plain-language explanation"

    def test_stub_flag_when_no_model_file(self):
        datastore.case_repo().upsert(_case("a", suspects=["ravi"]))
        resp = score_subject("ravi")
        # The model file doesn't exist in the test env, so we must be in stub mode.
        assert resp.is_stub is True
