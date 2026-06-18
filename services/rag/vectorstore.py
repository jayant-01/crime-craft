"""Vector store providers.

Two implementations behind one Protocol:
  - InMemoryVectorStore: dict + naive cosine-similarity scan. Fine up to
    a few thousand vectors; we have ~1100 cases × ~3 chunks = ~3.3k vectors.
  - QdrantVectorStore: real Qdrant client; expects a running Qdrant on
    VECTOR_DB_URL. Self-hosted in the same Zoho region in prod.

The store is intentionally dumb about ranking — filters reduce the
candidate set, then we cosine-score. The retriever is the only thing that
knows about role-based filters.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Protocol

from config import get_settings

_settings = get_settings()


@dataclass(frozen=True)
class VectorPoint:
    id: str
    vector: list[float]
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ScoredPoint:
    id: str
    score: float
    payload: dict[str, Any]


class VectorStore(Protocol):
    def upsert(self, points: list[VectorPoint]) -> None: ...
    def search(
        self,
        query: list[float],
        top_k: int = 6,
        filters: dict[str, Any] | None = None,
    ) -> list[ScoredPoint]: ...
    def delete_by_case(self, case_id: str) -> None: ...


class InMemoryVectorStore:
    def __init__(self) -> None:
        self._points: dict[str, VectorPoint] = {}

    def upsert(self, points: list[VectorPoint]) -> None:
        for p in points:
            self._points[p.id] = p

    def search(
        self,
        query: list[float],
        top_k: int = 6,
        filters: dict[str, Any] | None = None,
    ) -> list[ScoredPoint]:
        candidates = self._filter(self._points.values(), filters)
        scored = [
            ScoredPoint(id=p.id, score=_cosine(query, p.vector), payload=p.payload)
            for p in candidates
        ]
        scored.sort(key=lambda s: s.score, reverse=True)
        return scored[:top_k]

    def delete_by_case(self, case_id: str) -> None:
        to_drop = [pid for pid, p in self._points.items() if p.payload.get("case_id") == case_id]
        for pid in to_drop:
            self._points.pop(pid, None)

    @staticmethod
    def _filter(points, filters: dict[str, Any] | None):
        if not filters:
            return list(points)
        out = []
        for p in points:
            ok = True
            for key, want in filters.items():
                got = p.payload.get(key)
                if isinstance(want, (list, tuple, set)):
                    if got not in want:
                        ok = False
                        break
                else:
                    if got != want:
                        ok = False
                        break
            if ok:
                out.append(p)
        return out


class QdrantVectorStore:
    """Real Qdrant. Lazy-imports the client so dev installs don't need it."""

    COLLECTION = "case_chunks"

    def __init__(self, url: str | None = None, dim: int = 1024) -> None:
        self._url = url or _settings.vector_db_url
        self._dim = dim
        self._client = None

    def _ensure_client(self):
        if self._client is not None:
            return self._client
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, VectorParams

        self._client = QdrantClient(url=self._url)
        existing = {c.name for c in self._client.get_collections().collections}
        if self.COLLECTION not in existing:
            self._client.create_collection(
                collection_name=self.COLLECTION,
                vectors_config=VectorParams(size=self._dim, distance=Distance.COSINE),
            )
        return self._client

    def upsert(self, points: list[VectorPoint]) -> None:
        from qdrant_client.models import PointStruct

        client = self._ensure_client()
        client.upsert(
            collection_name=self.COLLECTION,
            points=[
                PointStruct(id=_stable_int_id(p.id), vector=p.vector, payload={**p.payload, "chunk_id": p.id})
                for p in points
            ],
        )

    def search(
        self,
        query: list[float],
        top_k: int = 6,
        filters: dict[str, Any] | None = None,
    ) -> list[ScoredPoint]:
        from qdrant_client.models import FieldCondition, Filter, MatchAny, MatchValue

        client = self._ensure_client()
        qfilter = None
        if filters:
            must = []
            for k, v in filters.items():
                if isinstance(v, (list, tuple, set)):
                    must.append(FieldCondition(key=k, match=MatchAny(any=list(v))))
                else:
                    must.append(FieldCondition(key=k, match=MatchValue(value=v)))
            qfilter = Filter(must=must)

        results = client.search(
            collection_name=self.COLLECTION,
            query_vector=query,
            limit=top_k,
            query_filter=qfilter,
        )
        return [
            ScoredPoint(
                id=r.payload.get("chunk_id", str(r.id)),
                score=r.score,
                payload=r.payload or {},
            )
            for r in results
        ]

    def delete_by_case(self, case_id: str) -> None:
        from qdrant_client.models import FieldCondition, Filter, MatchValue, FilterSelector

        client = self._ensure_client()
        client.delete(
            collection_name=self.COLLECTION,
            points_selector=FilterSelector(
                filter=Filter(must=[FieldCondition(key="case_id", match=MatchValue(value=case_id))])
            ),
        )


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _stable_int_id(s: str) -> int:
    """Qdrant point IDs must be ints (or UUIDs). Hash the chunk_id to a 63-bit int."""
    import hashlib

    return int.from_bytes(hashlib.sha1(s.encode("utf-8")).digest()[:8], "big") >> 1


_store: VectorStore | None = None


def get_vector_store() -> VectorStore:
    global _store
    if _store is None:
        if _settings.rag_provider == "live":
            from .embeddings import get_embedder

            _store = QdrantVectorStore(dim=get_embedder().dim)
        else:
            _store = InMemoryVectorStore()
    return _store


def reset_for_tests() -> None:
    global _store
    _store = None
