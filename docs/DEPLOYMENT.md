# Crime Craft — Production Deployment Walkthrough (Zoho Catalyst)

This is the end-to-end guide for taking Crime Craft from the repo to a running
production deployment on **Zoho Catalyst**. It assumes you are deploying from a
**Windows** workstation (PowerShell commands are given alongside the bash ones).

> **Golden rule:** In production the app runs on real Catalyst services with
> `CATALYST_ENABLED=true`. The local login stub (username-prefix → role, no
> password) is **dev-only** and the app now **refuses to boot** in production
> with the stub enabled or a default JWT secret (see [§7 Security](#7-security-hardening)).

---

## 0. What deploys where

```
                 ┌─────────────────────────────────────────────┐
   Browser ───►  │  Catalyst Client (CDN)   apps/web/dist       │  React SPA
                 └───────────────┬─────────────────────────────┘
                                 │ HTTPS (Catalyst session)
                 ┌───────────────▼─────────────────────────────┐
                 │  AppSail (python3.11)    main.py (FastAPI)   │  API + RBAC + audit
                 └───┬───────────┬───────────────┬─────────────┘
                     │           │               │
        ┌────────────▼──┐  ┌─────▼────────┐  ┌───▼──────────────┐
        │ Data Store    │  │ User Mgmt    │  │ Qdrant (self-host│  vector search
        │ Cases/Audit/… │  │ (auth)       │  │  on region VM)   │  (RAG live)
        └───────────────┘  └──────────────┘  └──────────────────┘
                     ▲
        ┌────────────┴──────────┐        ┌───────────────────────────┐
        │ Cron Function         │        │ Hosted LLM (Anthropic/…)  │
        │ functions/ingest_cron │        │  — data-residency review  │
        └───────────────────────┘        └───────────────────────────┘
```

| Concern | Catalyst feature | Code |
|---|---|---|
| Frontend hosting | Catalyst Client (CDN) | `apps/web/dist` |
| API hosting | AppSail `python3.11` | `main.py`, `catalyst/app-config.json` |
| Auth (login/MFA) | User Management | `auth/catalyst_auth.py` |
| Cases + audit log | Data Store | `services/datastore.py`, `catalyst/datastore-schema.json` |
| Hourly ingest | Cron Function | `functions/ingest_cron/` |
| RAG / vector search + LLM | **Catalyst QuickML** (Knowledge Base + RAG + LLM Serving, Qwen 2.5, in-region) — or self-hosted Qdrant + external LLM | `services/rag/` |
| Recidivism model | **Zia AutoML** (tabular) — or self-trained XGBoost | `services/predictive/` |
| PII redaction | **Zia Text Analytics (NER) + Identity Scanner (Aadhaar)** — or the regex fallback | `services/pii.py` |

> **Data model:** `catalyst/datastore-schema.json` now models the **real KSP FIR
> ER** (~26 tables). See [KSP_SCHEMA_MAPPING.md](KSP_SCHEMA_MAPPING.md) for the
> field mapping, PII re-tagging, and the native-service replacement plan.

---

## 1. Prerequisites (Windows workstation)

| Tool | Version | Install |
|---|---|---|
| Node.js | 18+ (LTS) | https://nodejs.org — includes npm |
| Python | **3.11** (matches AppSail stack) | https://www.python.org/downloads/ — check "Add to PATH" |
| Catalyst CLI | latest | `npm i -g zcatalyst-cli` |
| Zoho account | — | with a Catalyst project you can admin |
| Git | latest | https://git-scm.com |

Verify:

```powershell
node -v ; npm -v
py -3.11 --version
catalyst --version
catalyst login          # opens browser for Zoho SSO
```

> **Python note:** Use 3.11 to match the AppSail stack (`app-config.json`
> `"stack": "python3.11"`). The pinned deps in `requirements.txt` have 3.11
> wheels. (3.12+ works locally but keep the deploy target on 3.11.)

---

## 2. One-time Zoho Catalyst setup (Console)

Do these once in the Catalyst Console (https://console.catalyst.zoho.com).

### 2.1 Create the project & pin the region
1. **New Project** → name it (e.g. `crime-craft`).
2. **Set the data center to an Indian region** (Data residency is a hard
   requirement — see [§7](#7-security-hardening)). Confirm before adding data.
3. Copy the **Project ID** into `catalyst/catalyst.json` → `project.id`
   (replace `REPLACE_WITH_PROJECT_ID_FROM_CONSOLE`).

### 2.2 Provision the Data Store tables
Console → **Data Store** → create the tables exactly as in
[`catalyst/datastore-schema.json`](../catalyst/datastore-schema.json): `Cases`,
`AuditLog`, `Conversations`, `CaseEmbeddings`. Columns, types, primary keys and
indexes **must match** — `services/datastore.py` assumes them.

> The schema file is the source of truth. If you change a column there, change
> it in the Console in the same PR.

### 2.3 Provision User Types (RBAC)
Console → **Authentication → User Types**. Create the four types from the schema
file:

| Type | Self-signup | Notes |
|---|---|---|
| `public` | ✅ yes | citizen, redacted views |
| `officer` | ❌ no (invite) | add custom attribute `officer_id` (string) |
| `senior_officer` | ❌ no (invite) | recidivism access |
| `admin` | ❌ no (invite) | Crime Craft team |

The names must match `_USER_TYPE_TO_ROLE` in `auth/catalyst_auth.py`. Unknown
types fail closed to `public`.

### 2.4 File Store folders (for the ingest cron)
Console → **File Store** → create two folders and note their IDs:
- an **inbox** where KSP drops new CSVs → `INGEST_INBOX_FOLDER_ID`
- a **processed** folder → `INGEST_PROCESSED_FOLDER_ID`

### 2.5 SDK credentials
Console → **Project Settings → SDK Credentials** → generate a credential set.
You'll paste these into the AppSail environment (next section).

---

## 3. Configure environment variables

Two places need env vars: your **local `.env`** (for `catalyst deploy` / local
testing against Catalyst) and the **AppSail runtime environment** (Console →
AppSail → your app → Configuration → Environment Variables).

Copy `.env.example` → `.env` and fill in. The production-critical values:

```ini
APP_ENV=production
CATALYST_ENABLED=true

# Catalyst SDK credentials (from §2.5)
CATALYST_PROJECT_ID=...
CATALYST_PROJECT_DOMAIN=...
CATALYST_PROJECT_KEY=...
CATALYST_ENVIRONMENT=production        # development | production
CATALYST_CLIENT_ID=...
CATALYST_CLIENT_SECRET=...
CATALYST_REFRESH_TOKEN=...

# JWT stub is unused when CATALYST_ENABLED=true, but the app still refuses to
# boot in production with the default secret — set a strong one anyway.
JWT_SECRET=<64+ char random string>

# RAG — production ("live") wiring (see §6). Keep "stub" only for a smoke deploy.
RAG_PROVIDER=live
LLM_PROVIDER=anthropic
LLM_API_KEY=sk-ant-...
LLM_MODEL_ID=claude-sonnet-4-6
EMBEDDING_MODEL=BAAI/bge-m3
VECTOR_DB_URL=http://<qdrant-host>:6333

# Ingest cron (set on the FUNCTION's env, not AppSail — §5)
INGEST_INBOX_FOLDER_ID=...
INGEST_PROCESSED_FOLDER_ID=...
```

> **Never commit `.env`.** Set the same values in the AppSail Console
> environment so the deployed app has them at runtime.

**Generate a strong JWT secret (PowerShell):**
```powershell
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

---

## 4. Build & deploy

### 4.1 Install deps and build the frontend
```powershell
# backend deps (into a 3.11 venv)
py -3.11 -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt

# frontend
cd apps\web
npm install
npm run build          # produces apps/web/dist  (Catalyst Client source)
cd ..\..
```

> `apps/web/vite.config.ts` proxies `/api` to `localhost:8000` **for local dev
> only**. In production the SPA and API are served from the same Catalyst
> domain, so configure the frontend's API base to the deployed AppSail URL
> (env-driven in `apps/web/src/api/client.ts`) before `npm run build`.

### 4.2 Deploy
```powershell
cd catalyst
catalyst deploy
```

`catalyst deploy` packages, per `catalyst/catalyst.json`:
- the FastAPI app (`app-config.json`) → **AppSail** (`uvicorn main:app`, 2 workers, `/health` health-check)
- `apps/web/dist` → **Catalyst Client** (CDN)
- everything under `functions/` → **Functions** (the ingest cron)

### 4.3 First-boot check
The app **fails closed** on an insecure prod config (this is intentional). If it
won't start, check the AppSail logs for one of:
- `Refusing to start: APP_ENV is production but CATALYST_ENABLED is false` → set `CATALYST_ENABLED=true`.
- `Refusing to start: default JWT secret in production` → set `JWT_SECRET`.

---

## 5. Ingest cron (delta loading)

The cron function (`functions/ingest_cron/`) runs hourly (`0 * * * *`,
Asia/Kolkata) and ingests any new CSV/JSON dropped in the File Store inbox,
reusing the same `services.ingest` pipeline as the API and CLI.

Set its env vars on the **function** (Console → Functions → `ingest_cron` →
Configuration): `INGEST_INBOX_FOLDER_ID`, `INGEST_PROCESSED_FOLDER_ID` (from §2.4).

> **Reindex after ingest (RAG live):** ingest writes case rows + `CaseEmbeddings`
> metadata, but the Qdrant vectors must be (re)built. Run `make reindex`
> (`python -m services.rag.indexer reindex`) after a bulk load, or extend the
> cron to call `reindex_all()` once Qdrant is wired.

---

## 6. RAG in production ("live" provider)

**Correction to earlier guidance:** Catalyst *does* provide managed RAG —
**QuickML** (Knowledge Base + RAG + LLM Serving), verified against Catalyst docs.
Two viable paths:

**Option A — QuickML (recommended for residency).** Upload case chunks to a
QuickML **Knowledge Base**; QuickML's RAG (Qwen 2.5-14B, OAuth endpoint) answers
grounded in it. Inference stays in the **India DC** → cleanly satisfies "no raw
case data leaves Indian data centers." Trade-off: Qwen quality (esp. Kannada) vs
Claude — evaluate before committing. Keep role-aware retrieval by uploading only
OPEN chunks to a public KB and OPEN+SENSITIVE to an officer KB (or filter on the
`classification` column in `CaseEmbeddings`).

**Option B — self-hosted Qdrant + external LLM.** Qdrant on a VM **in the same
Indian region**; `EMBEDDING_MODEL=BAAI/bge-m3`; set `LLM_API_KEY`. ⚠️ An external
LLM (e.g. Claude) sends case text **out of region** → needs a residency/DPA
sign-off that may not be grantable. Higher quality; residency risk.

The provider abstraction (`services/rag/llm.py`, `RAG_PROVIDER` toggle) keeps this
a config choice. A first deploy can ship `RAG_PROVIDER=stub` (offline templated
answers + citations) to validate auth/data/hosting, then flip to A or B.

> **Residency:** create the Catalyst project in the **India DC** (Mumbai/Chennai;
> DPDP-aligned). Note Zia **Identity Scanner (Aadhaar) is IN-DC only** — expected,
> since this is an India-only deployment.

---

## 7. Security hardening

Recent security fixes already landed in this codebase (verified by the test
suite). Confirm each is in your deploy, then complete the checklist.

**Fixed in code:**
- ✅ **RBAC on retrieval** — a public user can no longer force officer-only
  (SENSITIVE) chunks via the `/chat` `filters` field; the role filter is
  enforced last (`services/rag/retriever.py`).
- ✅ **ZCQL injection** closed — Catalyst repo queries escape/scope user-supplied
  IDs (`services/conversations.py`, `services/datastore.py`).
- ✅ **Fail-closed in prod** — app refuses to boot with the login stub or a
  default JWT secret in production (`main.py`).
- ✅ **Audit "who/why"** — recidivism subject + reason and client IP now persist
  to the `AuditLog` (`middleware/audit.py`, `main.py`).
- ✅ **No exception leakage** from the Catalyst auth path (`auth/catalyst_auth.py`).

**Deployment checklist:**
- [ ] `APP_ENV=production`, `CATALYST_ENABLED=true`, strong `JWT_SECRET`.
- [ ] Catalyst project pinned to an **Indian data region**; confirm no raw case
      data leaves it (incl. the LLM call — §6).
- [ ] Officer/senior/admin user types are **invite-only** (`selfSignup=false`).
- [ ] TLS enforced (Catalyst default); HSTS on.
- [ ] Audit log review process in place (`AuditLog` is append-only).
- [ ] **PII redaction — known limitation:** narrative name-redaction
      (`services/pii.py`) is regex-based and misses single-token and
      **non-Latin (Hindi/Kannada)** names. Public users don't receive SENSITIVE
      narratives (fixed above), but before broadening exposure, wire a real NER
      model (`detect_names_with_ner` is a stub today).
- [ ] Rotate SDK credentials & `LLM_API_KEY`; store as AppSail env secrets, not in git.

---

## 8. Post-deploy verification

```powershell
# health
curl https://<your-appsail-domain>/health          # {"status":"ok","catalyst":true}

# OpenAPI renders (routes wired)
curl https://<your-appsail-domain>/openapi.json
```

Then in the browser (Catalyst Client URL):
- Log in via the **Catalyst hosted flow** (not the dev stub).
- As an **officer**: Cases, Chat (grounded citations), Dashboard, Network.
- As a **senior officer**: Recidivism scores — confirm each appears in `AuditLog`
  with the requester ID **and reason**.
- As **public**: confirm PII is redacted and officer-only pages are forbidden.

**Offline regression suite** (run on any machine with Docker before deploying):
```bash
docker run --rm -v "$PWD":/app -w /app \
  -e PIP_INDEX_URL=<your-pip-index> -e PIP_TRUSTED_HOST=<host> \
  python:3.12 bash -c 'pip install -r requirements.txt -q && python -m pytest -q'
```
(Windows: run the same from WSL2/Docker Desktop, or `py -3.11 -m venv` + `pip install -r requirements.txt` + `pytest`.)

---

## 9. Rollback & troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| App won't boot, "Refusing to start…" | insecure prod config (by design) | set `CATALYST_ENABLED=true` / `JWT_SECRET` |
| 500 on any authed request | missing `email-validator` or bad Catalyst creds | check deps + SDK credentials |
| Chat says "I don't have that…" | corpus not indexed in Qdrant | `make reindex` (RAG live) |
| Cases list empty | Data Store not provisioned / cron hasn't run | verify tables (§2.2), run ingest |
| Cron does nothing | `INGEST_INBOX_FOLDER_ID` unset | set function env (§5) |

**Rollback:** redeploy the previous git tag (`catalyst deploy` from that commit).
Data Store rows are unaffected by a code rollback; schema changes are not
auto-reverted — migrate deliberately.

---

## 10. Deployment checklist (tl;dr)

1. [ ] `catalyst login`; project created, region pinned, `project.id` set.
2. [ ] Data Store tables + User Types + File Store folders provisioned.
3. [ ] `.env` and AppSail env: `APP_ENV=production`, `CATALYST_ENABLED=true`, strong `JWT_SECRET`, SDK creds.
4. [ ] `pip install -r requirements.txt`; `npm run build` (API base pointed at prod).
5. [ ] (RAG live) Qdrant in-region up; `RAG_PROVIDER=live`; residency confirmed for the LLM.
6. [ ] `catalyst deploy`; `/health` returns `catalyst:true`.
7. [ ] Cron env set; first ingest + `make reindex` done.
8. [ ] Verify RBAC + audit end-to-end (§8); security checklist (§7) complete.
