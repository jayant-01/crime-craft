# Crime Craft

> **Intelligent Conversational AI for Karnataka State Police (KSP)**
> A multilingual, role-aware platform that turns thousands of case records into actionable insights — for the public, and for police investigators.

---

## 🚀 Hackathon Quick Start

> **5-minute setup. Three commands.**

```bash
make install         # backend deps + npm install for the web app
make dev             # runs FastAPI on :8000 and Vite on :5173 in parallel
```

> `make dev` auto-seeds the demo corpus (65 fabricated cases in `data/demo_cases.csv`) and indexes it for chat on boot — no separate seed step needed. `make seed` still runs the ingest+PII pipeline over that corpus if you want to see the redaction report; `make demo-data` regenerates the CSV.

Open **<http://localhost:5173>**, log in as `senior_jayant` (any password — role inferred from username prefix), and you're in.

📋 **Live demo walkthrough:** [DEMO.md](DEMO.md) — exact 5-minute pitch sequence
🧪 **Run the tests:** `make test` → ~108 tests, no API keys required
🩺 **Smoke check:** `make smoke` → boots app + hits `/health`

### What's actually built (status snapshot — 2026-06-18)

| Capability | Status | Where |
|-----------|--------|-------|
| FastAPI + JWT auth + RBAC | ✅ shipped | [main.py](main.py), [auth/](auth/) |
| Zoho Catalyst integration (auth, datastore, AppSail, cron) | ✅ wired | [catalyst/](catalyst/), [services/catalyst_client.py](services/catalyst_client.py) |
| CSV/JSON ingest + PII redaction (regex + names) | ✅ shipped | [services/ingest.py](services/ingest.py), [services/pii.py](services/pii.py) |
| Audit middleware (every request logged) | ✅ shipped | [middleware/audit.py](middleware/audit.py) |
| RAG chat with Claude Sonnet 4.6 + prompt caching | ✅ shipped | [services/rag/](services/rag/) |
| Multi-turn conversations (server-persisted) | ✅ shipped | [services/conversations.py](services/conversations.py) |
| Analytics — trends / top localities / hotspots | ✅ shipped | [services/analytics.py](services/analytics.py) |
| Language detection (English / Hindi / Kannada) | ✅ shipped | [services/lang.py](services/lang.py) |
| PDF export of conversations (with watermark) | ✅ shipped | [services/pdf.py](services/pdf.py) |
| Recidivism scoring (XGBoost + SHAP, senior-only) | ✅ shipped | [services/predictive/](services/predictive/) |
| Criminal network graph (Cytoscape.js) | ✅ shipped | [services/network.py](services/network.py), [apps/web/src/pages/NetworkPage.tsx](apps/web/src/pages/NetworkPage.tsx) |
| Voice — Whisper STT + Indic TTS | ✅ shipped (stub + live paths) | [services/voice/](services/voice/) |
| React frontend — login / cases / chat / dashboard / network / recidivism | ✅ shipped | [apps/web/](apps/web/) |
| Tests (~108, all offline) | ✅ shipped | [tests/](tests/), [tests/README.md](tests/README.md) |

### Honest gaps to flag for judges

These are intentional — they need real partner data / credentials before they make sense to switch on.

| Stubbed | What it does today | What it needs |
|---|---|---|
| LLM provider | Templated stub answer with citation | `LLM_API_KEY=sk-ant-...` + `RAG_PROVIDER=live` |
| Embeddings | Deterministic 64-d hash → vectors | `pip install sentence-transformers` + `RAG_PROVIDER=live` |
| Vector store | In-memory cosine scan | `docker compose up qdrant` + `RAG_PROVIDER=live` |
| Whisper STT | Placeholder transcript | `pip install openai-whisper` + `VOICE_PROVIDER=live` |
| Indic TTS | Silent WAV (frontend falls back to browser TTS) | Bhashini / IndicTTS account — `_live_synthesize` to fill |
| Recidivism labels | Synthetic (prior_count ≥ 2) | Real recidivism labels from KSP |
| Catalyst Auth iframe | Local-dev JWT login | Production Catalyst project + frontend swap |

---

Today, querying KSP case data means digging through PDFs, FIR portals, and disconnected dashboards. Officers spend hours assembling context that an AI could surface in seconds. Citizens, meanwhile, have almost no easy way to get clear, redacted answers about case status or area-level crime trends.

**Crime Craft** sits on top of KSP's case corpus and provides:

- A **chat-first interface** in English / Hindi / Kannada (text + voice).
- **Role-aware access** — citizens see redacted public info; officers see full case dossiers, network graphs, and predictive signals.
- **Analytics dashboards** for trends, hotspots, and top-offender patterns.
- **Audit trail + explainability** for every police-facing prediction.

### Success criteria (end of 6 months)

| # | Outcome | How we measure it |
|---|---------|---------------------|
| 1 | Officers can answer 80% of common case-lookup questions via chat | Pilot user study, task completion rate |
| 2 | Citizens can query crime trends in their locality safely | DPDP-compliant PII redaction audit |
| 3 | Hotspot dashboard surfaces patterns matching analyst intuition | Validation against KSP analyst review |
| 4 | Recidivism scoring is gated, explainable, and audit-logged | 100% of scores have a saved rationale + officer ID |

---

## 2. Who Uses It (Personas)

### Persona A — Public User
- Wants: "Are there any recent thefts in HSR Layout?", "What's the status of FIR #1234?" (with redactions).
- Sees: anonymized aggregates, public case status, area-level trends.
- **Never** sees: PII (names, addresses, phone, Aadhaar), full case files, predictive scores, network graphs.

### Persona B — Police Officer
- Wants: "Pull every case linked to suspect X in last 2 years", "Show me the network around this gang", "Where are similar MOs happening?"
- Sees: full case dossiers, criminal network graphs, predictive signals, audit-logged tools.
- All actions are logged with officer ID, timestamp, query, and result.

---

## 3. High-Level Architecture

```
                         ┌────────────────────────────────────┐
                         │       React Web App (PWA)          │
                         │  Public view  │  Officer dashboard │
                         └────────────────┬───────────────────┘
                                          │ HTTPS (JWT)
                         ┌────────────────▼───────────────────┐
                         │     FastAPI Gateway + AuthZ        │
                         │  - Role guard (public vs police)   │
                         │  - Rate limit, audit log writer    │
                         └──┬───────────┬──────────┬──────────┘
                            │           │          │
                  ┌─────────▼──┐  ┌─────▼──────┐  ┌▼──────────────┐
                  │ Chat / RAG │  │ Analytics  │  │ Predictive    │
                  │  Service   │  │  Service   │  │  Service      │
                  └─────┬──────┘  └─────┬──────┘  └──┬────────────┘
                        │               │            │
                  ┌─────▼──────┐  ┌─────▼──────┐  ┌──▼──────────┐
                  │ Vector DB  │  │ PostgreSQL │  │ ML Models   │
                  │ (Qdrant /  │  │  + PostGIS │  │ (XGBoost,   │
                  │  pgvector) │  │            │  │  LightGBM)  │
                  └─────┬──────┘  └─────┬──────┘  └─────────────┘
                        │               │
                  ┌─────▼───────────────▼──────────────────────┐
                  │ Hosted LLM API (Claude / GPT-4) +          │
                  │ Multilingual embeddings (BGE-M3 / MuRIL)   │
                  └────────────────────────────────────────────┘

                  Storage / Hosting / Auth: Zoho Catalyst
                  (with fallback to AWS / GCP where Catalyst is weak)
```

---

## 4. Tech Stack

| Layer | Choice | Why |
|-------|--------|-----|
| Frontend | **React.js** + Vite + Tailwind | Fast, common, large hiring pool |
| Mobile/PWA | React PWA | One codebase, install on phones |
| Backend API | **FastAPI** (Python 3.11+) | Async, great for ML serving, OpenAPI built-in |
| Auth | Zoho Catalyst Auth (or Keycloak) + JWT | Role-based; SSO-ready for KSP later |
| Primary DB | **PostgreSQL** + PostGIS | Cases, users, audit logs, geo-queries |
| Vector DB | **Qdrant** (self-host) or **pgvector** (simpler) | RAG over case embeddings |
| LLM | **Claude / GPT-4** via API | Best multilingual reasoning; no training cost |
| Embeddings | **BGE-M3** or **multilingual-e5** | Strong on English + Hindi + Kannada |
| Predictive ML | XGBoost / LightGBM | Tabular, fast, explainable (SHAP) |
| Voice (Phase 2) | Whisper (STT) + Indic TTS | Multilingual transcription |
| Visualization | Cytoscape.js (networks), Recharts (charts), MapLibre (hotspots) | Open-source, no vendor lock |
| Infra / Hosting | **Zoho Catalyst** (preferred) | Functions + storage + frontend + auth in one |
| Container/Orchestration | Docker; k8s only if Catalyst can't fit ML workloads | Keep simple until forced otherwise |
| Observability | Sentry (errors) + Grafana/Loki (logs/metrics) | Standard, self-hostable |
| CI/CD | GitHub Actions | Standard |

> **Note on Zoho:** Catalyst is great for auth/storage/API/frontend but **weak for GPU-bound ML training**. Our plan avoids training: we use hosted LLMs + a vector DB, so Catalyst handles most of the stack. Heavy batch jobs (embedding the case corpus) can run on a one-off VM.

---

## 5. Data & Privacy (read this carefully)

### Source
- **1100+ real KSP cases** delivered under a formal data-sharing agreement.
- Initial load is a one-time bulk import; ongoing updates via a **scheduled job every hour** (Catalyst cron / Celery beat) that pulls deltas.

### Classification
Every field is tagged at ingest:

| Class | Visible to public | Visible to officers |
|-------|-------------------|---------------------|
| `OPEN` (crime type, date, broad locality, status) | yes | yes |
| `SENSITIVE` (street-level location, MO details) | redacted | yes |
| `PII` (names, addresses, phone, Aadhaar, photos) | NEVER | yes (audit-logged) |

### Compliance non-negotiables
- **DPDP Act 2023** alignment — data minimization, purpose limitation, audit log.
- **Encryption** at rest (AES-256) and in transit (TLS 1.3).
- **Right to redress** — every officer access to PII is logged with reason.
- **No raw case data leaves Indian data centers**. (Pin Zoho region; confirm LLM provider's data-residency story before going live — may require running an on-prem open model for production.)
- **PII redaction pipeline** runs at ingest; we never rely on the LLM to "remember to redact."

---

## 6. AI / ML Approach

We are **not training a language model from scratch.** 1100 cases is far too small. Instead:

### 6a. Chat (RAG, not fine-tuning)
1. Chunk each case into structured passages.
2. Embed with **BGE-M3** (multilingual).
3. Store in **Qdrant / pgvector** with metadata (case ID, locality, date, classification).
4. At query time: filter by role + classification → retrieve top-k → ask hosted LLM to answer grounded in retrieved chunks → cite case IDs.
5. **Officer mode** also gets entity-resolution (people, places, vehicles) and follow-up tool calls.

### 6b. Predictive analytics — split into two clear tracks

**Track 1 — Trend & hotspot analytics (everyone)**
- Spatial-temporal clustering (ST-DBSCAN / KDE) on crime locations.
- Time-series decomposition for type-by-locality trends.
- Output: heatmaps, top-N charts, week-over-week deltas.
- *Aggregate only — no individual prediction.*

**Track 2 — Recidivism risk scoring (senior officers only)**
- Tabular model (XGBoost) on prior offense history → risk band (low/med/high).
- **SHAP** explanations attached to every score.
- **Human-in-the-loop required** — UI shows "this is a hint, not a decision."
- Every score view is **audit-logged** with officer ID + justification.
- Subjected to **bias audit** before each release (false-positive parity across demographics).

> **Ethics statement:** Predictive policing has a documented history of harm when used as a black box. We treat Track 2 as a senior-officer aid with mandatory explanation and audit. We do not predict *who will commit* a crime — we score known offenders' recidivism likelihood with full transparency.

### 6c. Models considered → decisions

| Need | Considered | Picked | Why |
|------|------------|--------|-----|
| Multilingual chat | Train custom NLP | **Hosted LLM + RAG** | 100x cheaper, better quality, faster to ship |
| Embeddings | OpenAI text-embed-3 | **BGE-M3** | Better Hindi/Kannada, can self-host |
| Recidivism | Deep neural net | **XGBoost + SHAP** | Tabular data, explainable, regulator-friendly |
| Voice | Build STT | **Whisper** | Multilingual, open-source |
| Hotspot | Custom CNN on maps | **ST-DBSCAN / KDE** | Classical, well-understood, fast |

---

## 7. Feature Matrix (MVP → v1 → v2)

Hackathon delivery cuts across the original roadmap — most of MVP through v1 and large parts of v2 are working with stubs swapped for production providers via env toggles.

| Feature | MVP (M0–M3) | v1 (M3–M5) | v2 (M5–M6+) |
|---------|------------|-----------|------------|
| Auth + RBAC (public / officer / admin) | ✅ done | ✅ done | SSO with KSP (TBD) |
| Case ingestion pipeline + PII redaction | ✅ done | ✅ delta sync hourly via Catalyst cron | streaming |
| RAG chat | ✅ done (with prompt caching) | ✅ Hindi + Kannada (lang detection) | ✅ voice in/out |
| Citation of source case IDs | ✅ done | ✅ done (chips link to case detail) | rich card view |
| Trend & hotspot dashboard | ✅ done | ✅ filters | predictive trend |
| Criminal network graph | ✅ done | ✅ interactive Cytoscape | path-finding queries |
| Recidivism scoring (Track 2) | ✅ done (stub + live paths) | ✅ live with audit + SHAP | bias audit harness |
| PDF export of conversation | ✅ done (with watermark) | ✅ done | with citations panel |
| Audit log explorer (admin) | basic logger | filters + alerts (TBD) | anomaly detection |
| Explainability UI | ✅ per-citation chips | ✅ SHAP contributions in recidivism | full source highlight |

---

## 8. Roadmap & Milestones

### Phase 0 — Foundations (Weeks 1–3)
- Sign data-sharing MoU, scope PII fields, set up Indian-region infra.
- Repo, CI/CD, dev/staging/prod envs.
- Auth + RBAC skeleton.
- **Exit criteria:** team can clone, run locally, log in as each role.

### Phase 1 — Data & RAG MVP (Weeks 4–10)
- Ingest 1100 cases → PostgreSQL with classification tags.
- PII redaction pipeline (regex + NER, validated by KSP sample).
- Embed corpus → Qdrant/pgvector.
- English-only chat with citations.
- **Exit criteria:** officer can chat over corpus; public can query with redaction; both audit-logged.

### Phase 2 — Multilingual + Analytics (Weeks 11–18)
- Hindi + Kannada query support.
- Trend / hotspot dashboard (charts + map).
- Top-offender views (officer only).
- Network graph v1.
- **Exit criteria:** KSP pilot officers do real work for one week.

### Phase 3 — Predictive + Polish (Weeks 19–24)
- Recidivism scoring (shadow → live with audit).
- Voice in/out (English first).
- PDF export.
- Bias audit + ethics review.
- **Exit criteria:** sign-off from KSP and legal; production launch with one district.

---

## 9. Team Roles (5–8 people)

| Role | Count | Owns |
|------|-------|------|
| Tech lead / architect | 1 | Architecture, code review, KSP technical liaison |
| Frontend engineers | 2 | React app, dashboards, conversation UI, accessibility |
| Backend engineers | 2 | FastAPI services, ingest pipeline, auth, audit log |
| ML engineer | 1 | RAG, embeddings, recidivism model, evaluation harness |
| Data + DevOps engineer | 1 | Postgres/PostGIS, vector DB ops, CI/CD, observability |
| QA + compliance (part-time) | 1 | DPDP review, PII audits, bias testing |

If we end up at 5 people, the ML engineer doubles as data eng, and QA is shared.

---

## 10. Repository Structure (proposed)

```
crime-craft/
├── apps/
│   ├── web/                 # React frontend (public + officer)
│   └── api/                 # FastAPI gateway
├── services/
│   ├── chat/                # RAG service
│   ├── analytics/           # Trends, hotspots, charts
│   ├── predictive/          # XGBoost + SHAP recidivism
│   └── ingest/              # Case loader, PII redaction, embedding job
├── packages/
│   ├── schema/              # Shared Pydantic + TS types
│   └── ui/                  # Shared React components
├── infra/
│   ├── catalyst/            # Zoho deployment configs
│   ├── docker/              # Local dev compose files
│   └── ci/                  # GitHub Actions workflows
├── docs/
│   ├── architecture.md
│   ├── data-classification.md
│   ├── ethics-and-bias.md
│   └── runbooks/
└── README.md
```

---

## 11. Local Development (to be filled in by Phase 0)

```bash
# Quick start (placeholder — finalize during Phase 0)
git clone <repo>
cd crime-craft
cp .env.example .env
docker compose up -d postgres qdrant
make seed       # loads synthetic sample cases (NOT real KSP data)
make dev        # runs api + web on :8000 and :5173
```

> Real KSP data is **never** stored in laptops or public clouds. Use the synthetic seed for local dev.

---

## 12. Ethics, Bias & Audit (non-negotiable)

- Every police-facing prediction comes with an **explanation** (SHAP) and is **logged**.
- We run a **bias audit** before every minor release: false-positive parity across known sensitive attributes.
- We do not predict *who will commit* a crime — only *recidivism likelihood* of known offenders, as an officer aid.
- Public users never see predictive scores.
- Independent review (KSP + an external academic) signs off before Track 2 goes live.

---

## 13. Open Questions / TBD

These need answers before or during Phase 0:

1. Which LLM vendor satisfies India data-residency? (Anthropic / OpenAI region availability, or move to a self-hosted open model in production.)
2. Which Zoho Catalyst tier supports our background jobs and storage volume?
3. Confirm KSP's PII field list — we'll write a redaction spec from it.
4. Does KSP have an existing SSO / officer-ID system to integrate with, or do we issue credentials?
5. Pilot district + KSP champion(s) for Phase 2 user study.

---

## 14. References & Reading

- **DPDP Act 2023** — India's data protection law (mandatory reading for everyone).
- **BGE-M3** — multilingual embeddings paper.
- **RAG** — Retrieval-Augmented Generation overview (Lewis et al., 2020).
- **SHAP** — explainability for tabular models.
- **ST-DBSCAN** — spatial-temporal clustering for hotspots.
- **COMPAS / PredPol critiques** — required reading before working on Track 2.

---

*Maintainer: Jayant. Questions → drop them in #crime-craft on Slack or open an issue.*
