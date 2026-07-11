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
    # Start from any caller-supplied filters, then stamp the role's classification
    # filter LAST so a caller can never override it (e.g. a public user asking for
    # "sensitive" chunks). The role guard must always win.
    filters: dict[str, Any] = dict(extra_filters or {})
    filters["classification"] = _allowed_classifications(role)
    return get_vector_store().search(query_vec, top_k=top_k, filters=filters)
