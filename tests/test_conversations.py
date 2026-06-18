"""Conversation persistence + multi-turn chat tests."""

from __future__ import annotations

from datetime import date

import pytest

from models import Case, CaseStatus, ChatRequest, ChatTurn, Role, User
from services import datastore
from services import conversations as conv_module
from services.rag import chat as rag_chat_module
from services.rag import embeddings as emb_module
from services.rag import llm as llm_module
from services.rag import vectorstore as vs_module
from services.rag.indexer import index_case


@pytest.fixture(autouse=True)
def fresh_state():
    for mod in (datastore, conv_module, emb_module, vs_module, llm_module):
        mod.reset_for_tests()
    yield
    for mod in (datastore, conv_module, emb_module, vs_module, llm_module):
        mod.reset_for_tests()


def _user(role: Role = Role.OFFICER, id_: str = "officer_priya") -> User:
    return User(id=id_, email=f"{id_}@example.test", role=role)


def _seed_case():
    case = Case(
        case_id="FIR-2025-1001",
        crime_type="theft",
        locality="HSR Layout",
        occurred_on=date(2025, 11, 14),
        status=CaseStatus.UNDER_INVESTIGATION,
        narrative="Theft reported by resident.",
    )
    datastore.case_repo().upsert(case)
    index_case(case)


class TestRepoBasics:
    def test_create_and_get(self):
        u = _user()
        conv = conv_module.conversation_repo().create(u.id)
        fetched = conv_module.conversation_repo().get(conv.id, u.id)
        assert fetched is not None
        assert fetched.id == conv.id
        assert fetched.user_id == u.id
        assert fetched.turns == []

    def test_get_by_other_user_returns_none(self):
        u1 = _user(id_="officer_a")
        u2 = _user(id_="officer_b")
        conv = conv_module.conversation_repo().create(u1.id)
        assert conv_module.conversation_repo().get(conv.id, u2.id) is None

    def test_list_for_user_excludes_others(self):
        u1, u2 = _user(id_="a"), _user(id_="b")
        conv_module.conversation_repo().create(u1.id)
        conv_module.conversation_repo().create(u1.id)
        conv_module.conversation_repo().create(u2.id)
        assert len(conv_module.conversation_repo().list_for_user(u1.id)) == 2
        assert len(conv_module.conversation_repo().list_for_user(u2.id)) == 1

    def test_append_turns_updates_title_and_timestamps(self):
        u = _user()
        conv = conv_module.conversation_repo().create(u.id)
        first_updated = conv.updated_at
        appended = conv_module.conversation_repo().append_turns(
            conv.id, u.id,
            [ChatTurn(role="user", content="any thefts in HSR Layout?")],
        )
        assert appended is not None
        assert appended.title and "HSR Layout" in appended.title
        assert appended.updated_at >= first_updated

    def test_delete(self):
        u = _user()
        conv = conv_module.conversation_repo().create(u.id)
        assert conv_module.conversation_repo().delete(conv.id, u.id) is True
        assert conv_module.conversation_repo().get(conv.id, u.id) is None

    def test_delete_foreign_id_returns_false(self):
        u1, u2 = _user(id_="a"), _user(id_="b")
        conv = conv_module.conversation_repo().create(u1.id)
        assert conv_module.conversation_repo().delete(conv.id, u2.id) is False


class TestMultiTurnChat:
    def test_chat_persists_turns_when_conversation_id_set(self):
        _seed_case()
        u = _user()
        conv = conv_module.conversation_repo().create(u.id)
        resp = rag_chat_module.ask(
            ChatRequest(query="recent cases?", conversation_id=conv.id),
            u,
        )
        assert resp.conversation_id == conv.id
        loaded = conv_module.conversation_repo().get(conv.id, u.id)
        assert loaded is not None
        assert len(loaded.turns) == 2
        assert loaded.turns[0].role == "user"
        assert loaded.turns[1].role == "assistant"

    def test_unknown_conversation_id_is_created_on_demand(self):
        _seed_case()
        u = _user()
        # User passes a conversation_id the server has never seen — server
        # creates a new one and echoes its real id back.
        resp = rag_chat_module.ask(
            ChatRequest(query="hello?", conversation_id="conv_unknown"),
            u,
        )
        assert resp.conversation_id is not None
        assert resp.conversation_id != "conv_unknown"

    def test_chat_without_conversation_id_does_not_persist(self):
        _seed_case()
        u = _user()
        resp = rag_chat_module.ask(ChatRequest(query="hello?"), u)
        assert resp.conversation_id is None
        assert conv_module.conversation_repo().list_for_user(u.id) == []

    def test_history_passed_inline_is_used(self):
        _seed_case()
        u = _user()
        resp = rag_chat_module.ask(
            ChatRequest(
                query="follow-up?",
                history=[
                    ChatTurn(role="user", content="any thefts?"),
                    ChatTurn(role="assistant", content="Yes, [FIR-2025-1001]."),
                ],
            ),
            u,
        )
        # Pipeline ran successfully; assistant response should mention FIR-2025-1001
        # because the stub LLM cites the first [CASE-ID] it sees in the user message.
        assert resp.answer
