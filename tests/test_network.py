"""Network graph tests. We assert on node/edge counts and edge directionality
since those determine how the frontend visualization renders."""

from __future__ import annotations

from datetime import date

import pytest

from models import Case, CaseStatus, EdgeKind, NodeKind
from services import datastore
from services.network import graph_for_case, graph_for_suspect


@pytest.fixture(autouse=True)
def fresh_repo():
    datastore.reset_for_tests()
    yield
    datastore.reset_for_tests()


def _case(case_id: str, suspects: list[str], **overrides) -> Case:
    base = dict(
        case_id=case_id,
        crime_type="theft",
        locality="HSR Layout",
        occurred_on=date(2025, 11, 1),
        status=CaseStatus.UNDER_INVESTIGATION,
        suspect_names=suspects,
    )
    base.update(overrides)
    return Case(**base)


def _seed_simple():
    """Two suspects share one case; one of them also has another solo case."""
    datastore.case_repo().upsert(_case("FIR-1", ["Ravi Kumar", "Manoj S"]))
    datastore.case_repo().upsert(_case("FIR-2", ["Ravi Kumar"]))


class TestGraphForCase:
    def test_missing_case_returns_none(self):
        assert graph_for_case("FIR-NOPE") is None

    def test_depth_0_returns_case_and_its_suspects_only(self):
        _seed_simple()
        g = graph_for_case("FIR-1", depth=0)
        labels = {n.label for n in g.nodes}
        assert "FIR-1" in labels
        assert "Ravi Kumar" in labels
        assert "Manoj S" in labels
        # No expansion → FIR-2 should not be present.
        assert "FIR-2" not in labels

    def test_depth_1_expands_to_co_offender_cases(self):
        _seed_simple()
        g = graph_for_case("FIR-1", depth=1)
        labels = {n.label for n in g.nodes}
        assert {"FIR-1", "FIR-2", "Ravi Kumar", "Manoj S"} <= labels

    def test_co_suspect_edge_present_when_shared_case(self):
        _seed_simple()
        g = graph_for_case("FIR-1", depth=0)
        co_edges = [e for e in g.edges if e.kind == EdgeKind.CO_SUSPECT]
        assert len(co_edges) == 1

    def test_mentions_edges_have_correct_direction(self):
        _seed_simple()
        g = graph_for_case("FIR-1", depth=0)
        mentions = [e for e in g.edges if e.kind == EdgeKind.MENTIONS]
        # Source must be the case node; target the suspect.
        for e in mentions:
            src = next(n for n in g.nodes if n.id == e.source)
            tgt = next(n for n in g.nodes if n.id == e.target)
            assert src.kind == NodeKind.CASE
            assert tgt.kind == NodeKind.SUSPECT

    def test_skips_unknown_and_redacted_suspects(self):
        datastore.case_repo().upsert(_case("FIR-3", ["Ravi Kumar", "unknown", "REDACTED", ""]))
        g = graph_for_case("FIR-3", depth=0)
        labels = {n.label for n in g.nodes if n.kind == NodeKind.SUSPECT}
        assert labels == {"Ravi Kumar"}


class TestGraphForSuspect:
    def test_missing_suspect_returns_none(self):
        _seed_simple()
        assert graph_for_suspect("nobody") is None

    def test_centered_suspect_pulls_their_cases(self):
        _seed_simple()
        g = graph_for_suspect("Ravi Kumar", depth=0)
        case_labels = {n.label for n in g.nodes if n.kind == NodeKind.CASE}
        assert case_labels == {"FIR-1", "FIR-2"}

    def test_depth_1_pulls_co_offenders(self):
        _seed_simple()
        g = graph_for_suspect("Ravi Kumar", depth=1)
        suspect_labels = {n.label for n in g.nodes if n.kind == NodeKind.SUSPECT}
        assert "Manoj S" in suspect_labels

    def test_case_insensitive_lookup(self):
        _seed_simple()
        g = graph_for_suspect("ravi kumar", depth=0)
        assert g is not None
