# Zoho Catalyst — deployment & setup

This folder holds the Catalyst project config. The actual app code lives one level up (FastAPI in `main.py`, React in `apps/web/` once added).

## One-time setup

1. **Install the Catalyst CLI** (Node 18+):
   ```bash
   npm i -g zcatalyst-cli
   catalyst login
   ```
2. **Create the project** in the Catalyst Console (https://console.catalyst.zoho.com).
   Copy the project ID into `catalyst.json` → `project.id`.
3. **Link locally**:
   ```bash
   cd catalyst
   catalyst init   # confirm existing project
   ```

## Provisioning the datastore

Open the Catalyst Console → **Data Store** and create the tables defined in
[`datastore-schema.json`](datastore-schema.json). Columns, indexes, and primary
keys must match — the SDK code in `services/datastore.py` assumes them.

> The schema file is the source of truth. If you change a column, update the
> file in the same PR.

## Provisioning user types

Console → **Authentication → User Types**. Create the four types listed in
the schema file. Officer / senior_officer / admin must have `selfSignup = false`
(invite-only). Set a custom user attribute `officer_id` (string) on the officer
types.

## SDK credentials

Console → **Project Settings → SDK Credentials** → generate a new credential set
and copy values into `.env`:

```
CATALYST_PROJECT_ID=...
CATALYST_PROJECT_DOMAIN=...
CATALYST_PROJECT_KEY=...
CATALYST_ENVIRONMENT=development
CATALYST_CLIENT_ID=...
CATALYST_CLIENT_SECRET=...
CATALYST_REFRESH_TOKEN=...
CATALYST_ENABLED=true
```

`CATALYST_ENABLED=true` flips the app off of the in-memory stubs and onto real
Catalyst services. Keep it `false` for local dev so contributors don't need
production credentials.

## Local dev against Catalyst (optional)

```bash
catalyst serve         # boots Catalyst dev server with our config
# or, just run uvicorn against staging Catalyst:
CATALYST_ENABLED=true uvicorn main:app --reload
```

## Deploying

```bash
# From repo root:
cd apps/web && npm run build && cd ../..
cd catalyst && catalyst deploy
```

`catalyst deploy` packages:
- the FastAPI app (per `app-config.json`) → AppSail
- the React `dist/` → Catalyst Client (CDN)

## What lives where

| Concern               | Catalyst feature              | Code that talks to it           |
|-----------------------|-------------------------------|---------------------------------|
| Auth (login, MFA)     | User Management               | `auth/catalyst_auth.py`         |
| Case rows + audit log | Data Store                    | `services/datastore.py`         |
| Hourly case ingest    | Cron                          | (Phase 1) `services/ingest.py`  |
| File uploads          | File Store                    | (Phase 2)                       |
| API hosting           | AppSail (python3.11)          | `main.py`                       |
| Frontend hosting      | Catalyst Client (CDN)         | `apps/web/`                     |
| Background jobs       | Functions                     | (Phase 1) `functions/`          |

## Native Catalyst services we can use (verified Jul 2026)

Earlier notes claimed Catalyst had "no vector primitive." That's outdated — see
[docs/KSP_SCHEMA_MAPPING.md](../docs/KSP_SCHEMA_MAPPING.md) §3 for the full map.

| Need | Catalyst service | Notes |
|------|------------------|-------|
| RAG / vector search / LLM | **QuickML** (Knowledge Base + RAG + LLM Serving) | Qwen 2.5, in-region → resolves residency; Qwen-vs-Claude quality to evaluate |
| Recidivism (tabular ML) | **Zia AutoML** | keep SHAP-style explanation + audit + bias check |
| PII redaction | **Zia Text Analytics (NER) + Identity Scanner (Aadhaar)** | replaces the regex-only redactor's blind spots |
| Voice STT/TTS | **Zia Services** | ⚠️ STT is **English + Hindi only, no Kannada yet** → keep Bhashini/IndicTTS fallback for Kannada |
| Object storage (docs/photos) | **Catalyst Stratus** | scanned FIRs / evidence |
| Event-driven indexing | **Catalyst Signals + Event Functions** | auto-embed on Data Store insert |
| Ingest orchestration | **Catalyst Circuits** | ingest → redact → embed → index |
| Data residency | **India DC** (Mumbai/Chennai) | pick at project creation; DPDP-aligned |

| Still compute in app code | Why | Our plan |
|---|---|---|
| Geospatial hotspots | Data Store has no geo index | ST-DBSCAN/KDE over real `lat/long` (paged scan); cache results |
