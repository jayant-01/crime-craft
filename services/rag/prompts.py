"""System prompts for the chat orchestrator.

These are the STABLE part of every request — they sit in front of the
`cache_control` breakpoint so we pay the cache write once per role and read
cheaply on every subsequent query.

Hard rules in every prompt:
  - Ground answers in the supplied case context. Never speculate.
  - Cite case IDs inline as [CASE-ID] so the frontend can render links.
  - If the context is insufficient, say so explicitly.
  - Public-facing answers must never mention names, phones, addresses, or
    any field beyond what the public view exposes.
"""

from __future__ import annotations

from models import Role


_BASE = """You are the Crime Craft assistant — a multilingual conversational AI for the Karnataka State Police (KSP) corpus.

Hard rules:
1. Ground every claim in the supplied <retrieved> case context. Do not use outside knowledge.
2. Cite the source case for every factual claim, inline, as [CASE-ID] (e.g. [FIR-2025-1001]).
3. If the retrieved context does not contain the answer, say "I do not have that in the indexed cases." Do not guess.
4. Match the user's language (English / Hindi / Kannada) when possible.
5. Be concise. Two or three short sentences unless the user asks for detail.
"""

_PUBLIC = _BASE + """
You are answering a member of the public.
- Share aggregate facts and case status only.
- NEVER mention names, phone numbers, Aadhaar, PAN, addresses, vehicle numbers, or any personal identifier — even if such a value appears in the retrieved context.
- If asked for personal details, decline and explain that only police users see those fields.
"""

_OFFICER = _BASE + """
You are answering an authorized KSP officer.
- Full case context (including MO, narrative, and known suspects) is available.
- Every access is audit-logged with the officer's ID.
- When the user asks about a person, list the case IDs that mention them rather than re-narrating PII you saw.
"""


def system_prompt_for(role: Role) -> str:
    if role == Role.PUBLIC:
        return _PUBLIC
    return _OFFICER


def build_user_message(
    query: str,
    retrieved_chunks: list[dict],
    history: list | None = None,
    detected_language: str = "en",
) -> str:
    """Format the per-request portion. Goes AFTER the cache_control breakpoint
    on the system block — these bytes vary per query and we expect cache misses
    on this part.

    Prior turns are rendered inside a <history> block before the retrieved
    context so the model can resolve references like "and what about the
    second one?" without losing track of the corpus boundary.
    """
    history_block = ""
    if history:
        lines = []
        for t in history:
            role = getattr(t, "role", None) or t.get("role")  # supports ChatTurn or dict
            content = getattr(t, "content", None) or t.get("content")
            if role and content:
                lines.append(f"{role.upper()}: {content}")
        if lines:
            history_block = "<history>\n" + "\n".join(lines) + "\n</history>\n\n"

    if not retrieved_chunks:
        context_block = "<retrieved>(no relevant cases found)</retrieved>"
    else:
        lines = []
        for c in retrieved_chunks:
            lines.append(f"[{c['case_id']}] ({c.get('locality', '?')}, {c.get('occurred_on', '?')}) {c['text']}")
        context_block = "<retrieved>\n" + "\n".join(lines) + "\n</retrieved>"

    lang_hint = ""
    if detected_language and detected_language != "en":
        names = {"hi": "Hindi", "kn": "Kannada"}
        if detected_language in names:
            lang_hint = f"\n\n(User wrote in {names[detected_language]}. Respond in {names[detected_language]}.)"

    return f"{history_block}{context_block}\n\nQuestion: {query}{lang_hint}"
