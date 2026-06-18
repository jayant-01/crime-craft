"""Index a case into the vector store.

Called from:
  - the ingest pipeline (every upsert)
  - the `python -m services.rag.indexer reindex` CLI (one-shot bulk reindex)
"""

from __future__ import annotations

import logging
import sys
from typing import Iterable

from models import Case
from services.datastore import case_repo
from services.rag.chunker import chunk_case
from services.rag.embeddings import get_embedder
from services.rag.vectorstore import VectorPoint, get_vector_store

log = logging.getLogger("rag.indexer")


def index_case(case: Case) -> int:
    """Embed every chunk for `case` and upsert into the vector store. Returns the chunk count."""
    chunks = chunk_case(case)
    if not chunks:
        return 0
    vectors = get_embedder().embed([c.text for c in chunks])
    points = [
        VectorPoint(
            id=c.chunk_id,
            vector=v,
            payload={
                "case_id": c.case_id,
                "field": c.field,
                "classification": c.classification.value,
                "text": c.text,
                **c.metadata,
            },
        )
        for c, v in zip(chunks, vectors)
    ]
    # Replace any prior chunks for this case to keep the store consistent.
    get_vector_store().delete_by_case(case.case_id)
    get_vector_store().upsert(points)
    return len(points)


def reindex_all(cases: Iterable[Case] | None = None) -> int:
    """Reindex every case in the datastore. Returns the total chunks indexed."""
    cases = cases if cases is not None else case_repo().list(limit=10_000)
    total = 0
    for case in cases:
        total += index_case(case)
    log.info("reindex_all complete: %d chunks across %d cases", total, len(list(cases)) if isinstance(cases, list) else -1)
    return total


def _main(argv: list[str]) -> int:
    logging.basicConfig(level=logging.INFO)
    if len(argv) > 1 and argv[1] == "reindex":
        total = reindex_all()
        print(f"indexed {total} chunks")
        return 0
    print("usage: python -m services.rag.indexer reindex", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv))
