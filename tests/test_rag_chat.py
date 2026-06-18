"""End-to-end chat test using stub providers (RAG_PROVIDER=stub).

We don't assert on the LLM's wording — the stub is deterministic but the goal
is to exercise the pipeline: index → retrieve → role-filter → prompt → cite."""

from __future__ import annotations

from datetime import date

import pytest

from models import Case, CaseStatus, ChatRequest, Role, User
from services import datastore
from services.rag import chat as rag_chat_module
from services.rag import embeddings as emb_module
from services.rag import llm as llm_module
from services.rag import vectorstore as vs_module
from services.rag.indexer import index_case


@pytest.fixture(autouse=True)
def fresh_state():
    datastore.reset_for_tests()
    emb_module.reset_for_tests()
    vs_module.reset_for_tests()
    llm_module.reset_for_tests()
    yield
    datastore.reset_for_tests()
    emb_module.reset_for_tests()
    vs_module.reset_for_tests()
    llm_module.reset_for_tests()


def _seed_case(case_id="FIR-2025-1001") -> Case:
    case = Case(
        case_id=case_id,
        crime_type="theft",
        locality="HSR Layout",
        street_address="27th Main",
        occurred_on=date(2025, 11, 14),
        status=CaseStatus.UNDER_INVESTIGATION,
        mo_details="forced entry via balcony",
        victim_names=["Ramesh Kumar"],
        suspect_names=["Unknown"],
        phone_numbers=["9845012345"],
        narrative="CCTV under review. Suspect entered around 2am.",
    )
    datastore.case_repo().upsert(case)
    index_case(case)
    return case


def _user(role: Role) -> User:
    return User(id=f"{role.value}_test", email=f"{role.value}@example.test", role=role)


class TestEndToEnd:
    def test_officer_chat_runs_and_produces_response(self):
        _seed_case()
        resp = rag_chat_module.ask(
            ChatRequest(query="any thefts in HSR Layout?", top_k=3),
            _user(Role.OFFICER),
        )
        assert resp.answer
        assert resp.model == "stub-llm"
        assert len(resp.retrieved_chunk_ids) > 0

    def test_public_chat_runs_and_produces_response(self):
        _seed_case()
        resp = rag_chat_module.ask(
            ChatRequest(query="any thefts in HSR Layout?", top_k=3),
            _user(Role.PUBLIC),
        )
        assert resp.answer
        assert resp.model == "stub-llm"

    def test_stub_response_contains_citation(self):
        _seed_case("FIR-2025-7777")
        resp = rag_chat_module.ask(
            ChatRequest(query="recent cases", top_k=3),
            _user(Role.OFFICER),
        )
        assert any(c.case_id == "FIR-2025-7777" for c in resp.citations)


class TestRoleAwareRetrieval:
    def test_public_only_retrieves_open_chunks(self):
        _seed_case()
        resp = rag_chat_module.ask(
            ChatRequest(query="any thefts?", top_k=10),
            _user(Role.PUBLIC),
        )
        # Public must only pull `summary` chunks (OPEN). MO and narrative are SENSITIVE.
        for chunk_id in resp.retrieved_chunk_ids:
            assert chunk_id.endswith("::summary"), (
                f"public retrieved a non-OPEN chunk: {chunk_id}"
            )

    def test_officer_can_retrieve_sensitive_chunks(self):
        _seed_case()
        resp = rag_chat_module.ask(
            ChatRequest(query="forced entry", top_k=10),
            _user(Role.OFFICER),
        )
        # Officer should be able to see at least one non-summary (i.e. SENSITIVE) chunk.
        suffixes = {cid.rsplit("::", 1)[-1] for cid in resp.retrieved_chunk_ids}
        assert suffixes & {"mo", "narrative"}, (
            f"officer retrieved no SENSITIVE chunks: {resp.retrieved_chunk_ids}"
        )


class TestPiiSafety:
    def test_no_pii_text_in_retrieved_payload(self):
        _seed_case()
        resp = rag_chat_module.ask(
            ChatRequest(query="case details", top_k=10),
            _user(Role.OFFICER),
        )
        # Even officers must not see structured PII via the vector payload —
        # that comes from the structured columns, not retrieval.
        joined = " ".join(resp.retrieved_chunk_ids)
        assert "Ramesh" not in joined
        assert "9845012345" not in joined


class TestEmptyCorpus:
    def test_empty_corpus_returns_response_without_citations(self):
        # No seed_case() call → no chunks in the store.
        resp = rag_chat_module.ask(
            ChatRequest(query="anything?", top_k=3),
            _user(Role.OFFICER),
        )
        assert resp.retrieved_chunk_ids == []
        # The stub LLM will still produce *some* response.
        assert resp.answer
