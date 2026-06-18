"""Chat orchestrator.

Flow per request:
  1. If conversation_id is set, load stored history (server-side).
     Otherwise use req.history as-is (caller-managed).
  2. Retrieve role-allowed chunks via vector similarity.
  3. Build a grounded prompt: stable system prompt + history + retrieved + query.
  4. Call the LLM (with prompt caching on the system block).
  5. Extract citations from the answer; persist the new turn pair if requested.

The new user turn AND the model's answer are persisted as one append so the
stored history stays internally consistent — no half-written conversations
if the LLM call fails mid-flight.
"""

from __future__ import annotations

import re
from datetime import date

from models import (
    Case,
    ChatRequest,
    ChatResponse,
    ChatTurn,
    Citation,
    Role,
    User,
)
from services.cases import get_case
from services.conversations import conversation_repo
from services.lang import detect as detect_language
from services.rag.llm import get_llm
from services.rag.prompts import build_user_message, system_prompt_for
from services.rag.retriever import retrieve

CITATION_RE = re.compile(r"\[([A-Z]+-\d{4}-\d+)\]")
MAX_HISTORY_TURNS = 20  # cap replayed turns to keep prompt size bounded


def ask(req: ChatRequest, user: User) -> ChatResponse:
    # --- 1. Load history --------------------------------------------------
    stored_conv = None
    history: list[ChatTurn] = list(req.history)
    if req.conversation_id:
        stored_conv = conversation_repo().get(req.conversation_id, user.id)
        if stored_conv is not None:
            # Stored history wins over caller-supplied history when a
            # conversation_id is given — the server is the source of truth.
            history = list(stored_conv.turns)

    history = history[-MAX_HISTORY_TURNS:]  # cap

    # --- 2. Retrieve ------------------------------------------------------
    hits = retrieve(req.query, user.role, top_k=req.top_k, extra_filters=req.filters)
    retrieved = [
        {
            "case_id": h.payload.get("case_id"),
            "text": h.payload.get("text", ""),
            "locality": h.payload.get("locality"),
            "occurred_on": h.payload.get("occurred_on"),
            "crime_type": h.payload.get("crime_type"),
            "score": h.score,
        }
        for h in hits
    ]

    # --- 3. Prompt --------------------------------------------------------
    lang = detect_language(req.query)
    system = system_prompt_for(user.role)
    user_msg = build_user_message(req.query, retrieved, history=history, detected_language=lang.value)

    # --- 4. LLM call ------------------------------------------------------
    llm = get_llm()
    answer = llm.chat(system, user_msg)

    citations = _build_citations(answer, retrieved, user.role)

    # --- 5. Persist if conversation_id was provided -----------------------
    conv_id_out: str | None = None
    if req.conversation_id:
        # Create on demand if the id was unknown to the server.
        conv = stored_conv or conversation_repo().create(user.id)
        conv_id_out = conv.id
        new_turns = [
            ChatTurn(role="user", content=req.query),
            ChatTurn(role="assistant", content=answer),
        ]
        conversation_repo().append_turns(conv.id, user.id, new_turns)

    return ChatResponse(
        answer=answer,
        citations=citations,
        retrieved_chunk_ids=[h.id for h in hits],
        model=llm.model_id,
        conversation_id=conv_id_out,
        detected_language=lang.value,
    )


def _build_citations(answer: str, retrieved: list[dict], role: Role) -> list[Citation]:
    refs = list(dict.fromkeys(CITATION_RE.findall(answer)))
    by_id = {r["case_id"]: r for r in retrieved if r.get("case_id")}

    citations: list[Citation] = []
    for case_id in refs:
        meta = by_id.get(case_id)
        if meta:
            citations.append(
                Citation(
                    case_id=case_id,
                    locality=meta.get("locality"),
                    occurred_on=_parse_date(meta.get("occurred_on")),
                    crime_type=meta.get("crime_type"),
                    score=meta.get("score"),
                )
            )
            continue
        fallback = get_case(case_id, role)
        if isinstance(fallback, Case):
            citations.append(
                Citation(
                    case_id=case_id,
                    locality=fallback.locality,
                    occurred_on=fallback.occurred_on,
                    crime_type=fallback.crime_type,
                )
            )
        elif fallback is not None:  # PublicCaseView
            citations.append(
                Citation(
                    case_id=case_id,
                    locality=getattr(fallback, "locality", None),
                    occurred_on=getattr(fallback, "occurred_on", None),
                    crime_type=getattr(fallback, "crime_type", None),
                )
            )
        else:
            citations.append(Citation(case_id=case_id))
    return citations


def _parse_date(s) -> date | None:
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except (TypeError, ValueError):
        return None
