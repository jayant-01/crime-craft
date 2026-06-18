# Crime Craft — Tests

All tests run **offline**, with **no API keys**, in <30 seconds.
Provider interfaces (LLM, embeddings, vector store, voice, predictive) are swapped to
deterministic stubs via `RAG_PROVIDER=stub` (the default).

## Run

```bash
make test          # full suite, verbose
make test-fast     # stop on first failure, quiet
make smoke         # bootability check: boots app, hits /health
```

## Coverage map

| File | Tests | What it guards |
|---|---|---|
| [test_pii.py](test_pii.py) | ~30 | PII detection (phone, Aadhaar, PAN, email, vehicle, **names**) + idempotency + name-stopword false-positive avoidance. **Highest-risk path** in the codebase — over-test on purpose. |
| [test_ingest.py](test_ingest.py) | 5 | CSV/JSON loader, row normalization, end-to-end ingest on the sample corpus, PII findings counted. |
| [test_analytics.py](test_analytics.py) | 11 | Trend bucket alignment (week → Monday, month → 1st), top-localities ranking, hotspots recent-window math, filter combinations, edge cases. |
| [test_conversations.py](test_conversations.py) | 10 | User-scoping (foreign-id reads/deletes), auto-titling, multi-turn persistence, end-to-end /chat with `conversation_id`. |
| [test_rag_chunker.py](test_rag_chunker.py) | 7 | Case-to-chunk classification (summary=OPEN, mo/narrative=SENSITIVE), no-PII-in-chunks invariant, edge cases for missing fields. |
| [test_rag_chat.py](test_rag_chat.py) | 7 | End-to-end orchestrator: role-aware retrieval, public-only-sees-OPEN, officer-can-see-SENSITIVE, stub LLM citation extraction, empty-corpus behavior. |
| [test_lang.py](test_lang.py) | 7 | Devanagari → Hindi, Kannada script → Kannada, Latin → English, mixed-script tie-breaking. |
| [test_pdf.py](test_pdf.py) | 3 | PDF byte-stream validity, HTML-escaping of user content, empty-conversation rendering. Skipped if `reportlab` not installed. |
| [test_predictive.py](test_predictive.py) | 10 | Feature extraction, exact-name matching (no partial-match false positives), risk-band thresholds, stub-flag presence, "no-history" decision note. |
| [test_network.py](test_network.py) | 11 | Case→suspect edge directionality, depth expansion, co-suspect deduplication, case-insensitive suspect lookup, `unknown`/`redacted` skip. |
| [test_voice.py](test_voice.py) | 7 | STT stub determinism, TTS WAV header validity, language fallback, empty-input rejection. |
| [test_smoke.py](test_smoke.py) | 2 | App boots, `/health` returns 200. Guards against "the app doesn't even start" regressions. |

**Total: ~108 tests.**

## Pinned guarantees (anti-regression)

These behaviors are spec-level — never relax them without explicit approval.

| File | Guarantee | Why |
|---|---|---|
| `test_pii.py::TestRedactText` | Redaction is **idempotent** | Re-ingest must not double-replace |
| `test_pii.py::TestDetectNames::test_stopword_locations_not_redacted` | Place names are never redacted as people | DPDP edge case — false-redacting "Karnataka State Police" breaks analytics |
| `test_rag_chat.py::TestRoleAwareRetrieval::test_public_only_retrieves_open_chunks` | Public role can **never** retrieve SENSITIVE chunks | The single most important invariant in the system |
| `test_rag_chat.py::TestPiiSafety` | No PII text appears in retrieved chunk payloads even for officers | PII access happens by case_id lookup, not via vector retrieval |
| `test_rag_chunker.py::TestEdgeCases::test_no_pii_in_any_chunk` | Names/phones never end up in chunks | Chunker is the upstream guard for the retrieval invariant above |
| `test_predictive.py::TestScoreSubject::test_decision_note_always_advisory` | Every recidivism response carries "ADVISORY ONLY" | Ethics requirement — UI relies on it |
| `test_predictive.py::TestSubjectFilter::test_no_partial_match` | Recidivism only scores **exact-name** subjects | Prevents scoring "Ravi Kumar" when looking up "Ravi" |
| `test_conversations.py::TestRepoBasics::test_get_by_other_user_returns_none` | Conversations are strictly user-scoped | A leaked conv_id must not expose history to another user |

## Adding a new test

1. Put it under [tests/](.) — pytest discovers via the project root.
2. [conftest.py](conftest.py) already adds the repo root to `sys.path`, so you can `from services.x import ...` without an installed package.
3. Use the `fresh_state` / `fresh_repo` fixture pattern from existing tests when touching module-level singletons (datastore, vectorstore, LLM, embedder, conversations).
4. **Spec-level invariants** belong in the table above — update it in the same PR.

## CI hookup (TBD)

Not yet wired. The pattern is intentional — `make test` is the only command CI needs:

```yaml
# .github/workflows/test.yml (proposed)
- run: pip install -r requirements.txt
- run: make test
```

When that lands, the stub providers mean CI runs in <1 minute with no secrets.
