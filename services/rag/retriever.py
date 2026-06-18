"""Role-aware retrieval.

Reads a user query + the caller's Role and returns the top-k vector hits the
caller is *allowed to see*. This is the choke point — every /chat request
goes through here, so role-based access control on retrieval can't drift.

Rule:
  PUBLIC          → may retrieve OPEN chunks only
  OFFICER+        → may retrieve OPEN + SENSITIVE chunks
  (PII chunks)    → never retrieved by similarity, only by case_id
"""

from __future__ import annotations

from typing import Any

from models import Classification, Role
from services.rag.embeddings import get_embedder
from services.rag.vectorstore import ScoredPoint, get_vector_store


def _allowed_classifications(role: Role) -> list[str]:
    if role == Role.PUBLIC:
        return [Classification.OPEN.value]
    return [Classification.OPEN.value, Classification.SENSITIVE.value]


def retrieve(
    query: str,
    role: Role,
    top_k: int = 6,
    extra_filters: dict[str, Any] | None = None,
) -> list[ScoredPoint]:
    query_vec = get_embedder().embed([query])[0]
    filters: dict[str, Any] = {"classification": _allowed_classifications(role)}
    if extra_filters:
        filters.update(extra_filters)
    return get_vector_store().search(query_vec, top_k=top_k, filters=filters)
