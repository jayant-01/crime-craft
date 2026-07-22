"""Embedding providers.

Two implementations behind one Protocol:
  - StubEmbedder: deterministic LEXICAL bag-of-words hashing. No model
    download. Texts that share words get a high cosine similarity, so
    keyword / locality / case-id queries actually retrieve the right cases.
    It is NOT semantic (won't map "theft"→"robbery"), but it's good enough
    for offline dev and for demos where BGE-M3 + Qdrant aren't available.
  - LocalEmbedder: sentence-transformers + BGE-M3 (multilingual,
    English/Hindi/Kannada). Lazy-imports the dep so dev installs don't pay
    the ~600MB model download until they need it.
"""

from __future__ import annotations

import hashlib
import math
import re
from typing import Protocol

from config import get_settings

_settings = get_settings()


class Embedder(Protocol):
    @property
    def dim(self) -> int: ...
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class StubEmbedder:
    """Deterministic lexical bag-of-words hashing embedder (no model download).

    Each token (unicode word chars, lowercased) is hashed into a fixed-dim
    vector with a signed value; texts sharing tokens get a high cosine. This
    makes queries like "thefts in HSR Layout" or "FIR-2025-1001" retrieve the
    matching case summaries, unlike a whole-text hash (which is random noise).
    """

    DIM = 512
    _TOKEN_RE = re.compile(r"\w+", re.UNICODE)  # matches Latin + Devanagari + Kannada

    @property
    def dim(self) -> int:
        return self.DIM

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(t) for t in texts]

    def _embed_one(self, text: str) -> list[float]:
        vec = [0.0] * self.DIM
        for tok in self._TOKEN_RE.findall(text.lower()):
            h = int.from_bytes(hashlib.md5(tok.encode("utf-8")).digest()[:8], "big")
            idx = h % self.DIM
            sign = 1.0 if (h >> 12) & 1 else -1.0  # signed hashing cancels collisions
            vec[idx] += sign
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0.0:
            vec = [v / norm for v in vec]
        return vec


class LocalEmbedder:
    """sentence-transformers / BGE-M3. Lazy-imported."""

    def __init__(self, model_name: str | None = None) -> None:
        self._model_name = model_name or _settings.embedding_model
        self._model = None  # loaded on first use
        self._dim = 1024  # BGE-M3 is 1024-d

    @property
    def dim(self) -> int:
        return self._dim

    def _load(self):
        if self._model is not None:
            return self._model
        from sentence_transformers import SentenceTransformer  # lazy

        self._model = SentenceTransformer(self._model_name)
        self._dim = self._model.get_sentence_embedding_dimension()
        return self._model

    def embed(self, texts: list[str]) -> list[list[float]]:
        model = self._load()
        return model.encode(texts, normalize_embeddings=True).tolist()


_embedder: Embedder | None = None


def get_embedder() -> Embedder:
    global _embedder
    if _embedder is None:
        if _settings.rag_provider == "live":
            _embedder = LocalEmbedder()
        else:
            _embedder = StubEmbedder()
    return _embedder


def reset_for_tests() -> None:
    global _embedder
    _embedder = None
