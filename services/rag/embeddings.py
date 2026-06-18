"""Embedding providers.

Two implementations behind one Protocol:
  - StubEmbedder: deterministic hash → 64-d vector. Same text → same vector.
    Lets the whole RAG pipeline run offline with no model download.
    Does NOT give meaningful semantic similarity — tests should not assert
    that "theft" retrieves "robbery" from a stub.
  - LocalEmbedder: sentence-transformers + BGE-M3 (multilingual,
    English/Hindi/Kannada). Lazy-imports the dep so dev installs don't pay
    the ~600MB model download until they need it.
"""

from __future__ import annotations

import hashlib
import struct
from typing import Protocol

from config import get_settings

_settings = get_settings()


class Embedder(Protocol):
    @property
    def dim(self) -> int: ...
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class StubEmbedder:
    """Deterministic 64-d vectors from SHA-256(text). Pipeline-only, not semantic."""

    DIM = 64

    @property
    def dim(self) -> int:
        return self.DIM

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(t) for t in texts]

    def _embed_one(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        # 64 bytes / 4 bytes per float = 16 floats; tile to reach DIM.
        floats: list[float] = []
        while len(floats) < self.DIM:
            for i in range(0, len(digest), 4):
                f = struct.unpack("f", digest[i : i + 4])[0]
                # Normalize roughly into [-1, 1].
                if not (f == f and abs(f) < 1e30):  # NaN / inf guard
                    f = 0.0
                floats.append(max(-1.0, min(1.0, f / 1e30)))
                if len(floats) >= self.DIM:
                    break
            digest = hashlib.sha256(digest).digest()
        return floats


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
