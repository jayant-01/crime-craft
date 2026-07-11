# KSP Schema & Zoho Feature Gap Analysis

This is the design/planning artifact reconciling **two source documents** the KSP
team shared with the app as built today:

1. `Police_FIR_ER_Diagram.pdf` — the **real KSP FIR database schema** (~26
   normalized tables).
2. The three *"Zoho supported feature"* images — a capability map of **native
   Catalyst services** we can use instead of self-hosting/stubbing.

It answers: *what has to change in our data model, and which of our stubbed /
self-hosted components can be replaced by a managed Catalyst service.*

> **Status:** planning doc. The concrete artifacts already updated from this are
> `catalyst/datastore-schema.json` (now models the real ER) and `models/case.py`
> (additive real-schema fields). The full ingest/service migration is scoped
> in [§4](#4-migration-phasing) and needs the KSP export format to execute.

---

## 1. The core gap — flat toy model vs the real KSP schema

The app models a case as one flat `Case` row. The real KSP FIR is a normalized
graph: one `CaseMaster` with child rows for complainant/victim/accused/arrest/
charges, and a dozen lookup + geography + org tables.

### 1.1 Field-by-field mapping (repo → KSP source)

| Repo `Case` field | KSP source (table.column) | Notes / join |
|---|---|---|
| `case_id` | `CaseMaster.CrimeNo` | 18-digit structured (`cat+district+station+year+serial`); keep `CaseNo` too |
| `crime_type` | `CrimeSubHead.CrimeHeadName` (+ `CrimeHead.CrimeGroupName`) | via `CaseMaster.CrimeMinorHeadID → CrimeSubHead`, `CrimeMajorHeadID → CrimeHead` |
| `locality` | `Unit.UnitName` / `District.DistrictName` | via `CaseMaster.PoliceStationID → Unit → District`. **District = OPEN**, station/street = SENSITIVE |
| *(new)* `latitude`,`longitude` | `CaseMaster.latitude/longitude` | enables **real geo hotspots** (ST-DBSCAN) instead of string counts |
| `occurred_on` | `CaseMaster.IncidentFromDate` (date) | plus `IncidentToDate`, `CrimeRegisteredDate` |
| `status` | `CaseStatusMaster.CaseStatusName` | via `CaseMaster.CaseStatusID` |
| `mo_details` | *(derive)* `CrimeSubHead` + `ActSectionAssociation` | no direct MO column; MO ≈ sub-head + charged sections |
| `narrative` | `CaseMaster.BriefFacts` | SENSITIVE |
| `victim_names[]` | `Victim.VictimName` (1‑many) | + `AgeYear`, `GenderID`, `VictimPolice` |
| `suspect_names[]` | `Accused.AccusedName` (1‑many) | + `PersonID` (A1/A2), `AgeYear`, `GenderID` |
| `phone_numbers[]` | *(not in ER)* | KSP ER has no phone column; if present it's PII in a contact table |
| *(new)* complainant | `ComplainantDetails` | name + **caste/religion/occupation** (DPDP-sensitive PII) |
| *(new)* charges | `ActSectionAssociation → Act/Section` | legal acts + sections (e.g. IPC 302) |
| *(new)* arrests | `ArrestSurrender` (+ `inv_arrestsurrenderaccused`) | arrest/surrender events; drives **recidivism** |
| *(new)* disposal | `ChargesheetDetails` | A=chargesheet / B=false / C=undetected |
| *(new)* officer | `Employee` (`FirstName`,`KGID`,`Rank`,`Designation`) | via `PolicePersonID`, `IOID` |
| *(new)* category/gravity | `CaseCategory` (FIR/UDR/PAR), `GravityOffence` (Heinous) | |

### 1.2 What the richer schema *unlocks* (features that improve, not just port)

- **Geo hotspots** — real `latitude`/`longitude` → proper spatial-temporal
  clustering (ST-DBSCAN/KDE) instead of counting locality strings.
- **Recidivism (Track 2)** — `Accused` + `ArrestSurrender` linked across FIRs is a
  *real* prior-offence signal (the current model synthesises priors from
  `suspect_names`). Features: prior arrests, distinct districts, act-severity,
  time-since-last, chargesheet outcomes.
- **Network graph** — `Accused.PersonID` + junction table gives genuine
  co-accused edges; `Act/Section` adds charge-similarity edges.
- **Legal analytics** — charge frequency by act/section, heinous vs non-heinous
  trends, chargesheet/false/undetected rates.

---

## 2. PII / classification re-tagging (DPDP)

The real schema has **more sensitive data** than the toy model — most importantly
**caste, religion, occupation** (special-category personal data under the DPDP
Act). The redactor's classification map is updated accordingly (see the
`classification` tags now in `catalyst/datastore-schema.json`):

| Class | Fields | Public | Officer |
|---|---|---|---|
| **OPEN** | crime head/sub-head, category, **district**, status, registration date | ✅ | ✅ |
| **SENSITIVE** | `BriefFacts`, exact `lat/long`, incident times, `Act/Section` charges, arrest details, station | ❌ | ✅ |
| **PII** | all names (complainant/victim/accused/officer), age, **caste/religion/occupation**, `KGID`, Aadhaar/phone, DOB | ❌ never | ✅ audit-logged |

> **Consequence:** public analytics must aggregate at **district** level and never
> expose caste/religion/occupation cross-tabs (re-identification + discrimination
> risk). This is now a hard rule for the analytics service.

---

## 3. Zoho Catalyst native services — replace our stubs/self-hosting

The feature images map our needs onto managed Catalyst services. **Verified**
against Catalyst docs (July 2026); caveats flagged.

| Our component (today) | Catalyst service | Verified? | Caveat / decision |
|---|---|---|---|
| RAG: self-host **Qdrant + external Claude** | **QuickML** — Knowledge Base + RAG + LLM Serving | ✅ RAG via **Qwen 2.5-14B**, KB indexing, OAuth endpoints | Models are **Qwen, not Claude**. In-region → **solves residency**. Evaluate Qwen quality on Hindi/Kannada vs keeping external Claude for quality |
| Data residency (open question) | **India DC** (Mumbai + Chennai) | ✅ DPDP-aligned; pick IN DC at project creation | Aadhaar/Identity Scanner is **IN-DC only** — fine (India-only app) |
| Recidivism XGBoost (self-train) | **Zia AutoML** (tabular) / QuickML pipelines | ✅ no-code tabular AutoML | Keep SHAP-style explanation + audit requirement; validate bias parity |
| PII name redaction gap (audit finding #7) | **Zia Text Analytics (NER)** + **Zia Identity Scanner (Aadhaar)** | ✅ NER + Aadhaar OCR (name/addr/number) | Replaces the regex-only redactor's blind spots (non-Latin/single-token names) |
| Voice STT/TTS (Whisper/Indic stubs) | **Zia Services** speech | ⚠️ partial | STT = **English + Hindi only; Kannada NOT yet** supported. TTS not documented → keep Bhashini/IndicTTS fallback for Kannada |
| PDF export (reportlab) | **Catalyst SmartBrowz** | ◻️ per images (headless browser/PDF) | Optional; reportlab works today |
| Object/blob storage (case docs/photos) | **Catalyst Stratus** (S3-style) | ◻️ per images | For scanned FIRs / evidence photos |
| Event-driven indexing | **Catalyst Signals + Event Functions** | ◻️ per images | Auto-embed a case on Data Store insert |
| Ingest orchestration | **Catalyst Circuits** | ◻️ per images | ingest → redact → embed → index as a workflow |
| API routing/throttling | **Catalyst API Gateway** | ◻️ per images | in front of AppSail |
| Cron ingest | **Catalyst Cron** | ✅ already used | `functions/ingest_cron/` |

✅ = confirmed in Catalyst docs · ⚠️ = confirmed with a limitation · ◻️ = per the
feature images, confirm exact API before building.

### 3.1 The big architectural decision: QuickML vs external Claude
- **QuickML RAG (Qwen, in-region)** → data never leaves the India DC, cleanly
  satisfying "no raw case data leaves Indian data centers". Trade-off: Qwen 2.5
  quality (esp. Kannada) vs Claude.
- **External Claude** → higher quality/multilingual, but sends case text out of
  region → needs a residency/DPA sign-off that may not be grantable.
- **Recommendation:** default production to **QuickML RAG** for residency; keep
  the provider abstraction (`services/rag/llm.py`) so Claude can be A/B'd in a
  non-residency-restricted eval. The app's `RAG_PROVIDER` toggle already makes
  this a config choice.

---

## 4. Migration phasing

Nothing below is done blindly — it needs the KSP export format (per-table CSVs? a
joined view? DB replica?).

**Phase A — schema & classification (done):** `datastore-schema.json` models the
real ER; `models/case.py` carries additive real-schema fields; classification map
updated.

**Phase B — ER read path (DONE):** production reads the real ER. KSP seed their
data directly into the ER tables; `CatalystCaseRepo` (services/datastore.py) reads
`CaseMaster` + child + lookup tables via ZCQL and projects each FIR into `Case`
via the pure, unit-tested `services/ksp_mapping.py` (see `tests/test_ksp_mapping.py`).
The in-memory/demo path stays flat (our synthetic data). **The projection is
tested; the ZCQL execution is verified on the live Catalyst deploy only.**
- The app is **read-only** against the KSP corpus — `CatalystCaseRepo.upsert`
  raises (KSP own the seeding ETL). The `/admin/ingest` + cron paths are dev/flat-only.
- **Chat/RAG over KSP data** needs an embedding job that reads `CatalystCaseRepo.list`,
  chunks (OPEN/SENSITIVE), and loads a QuickML Knowledge Base / Qdrant — see Phase D.

**Phase C — service upgrades:** geo hotspots on real `lat/long`; recidivism on
`Accused`+`ArrestSurrender`; network on `Accused`/`PersonID`; district-only public
analytics. (Services already consume `Case`, now populated with these fields.)

**Phase D — managed services cutover:** QuickML KB/RAG for retrieval; Zia AutoML
for recidivism; Signals/Circuits for the pipeline; Stratus for documents.

---

## Sources (Catalyst capability verification, Jul 2026)
- QuickML RAG / LLM Serving / Knowledge Base — https://docs.catalyst.zoho.com/en/quickml/help/generative-ai/rag/ , https://docs.catalyst.zoho.com/en/quickml/help/generative-ai/llm-serving/ , https://docs.catalyst.zoho.com/en/quickml/help/generative-ai/knowledge-base/
- Zia Identity Scanner (Aadhaar) + Text Analytics NER — https://docs.catalyst.zoho.com/en/zia-services/help/identity-scanner/introduction/ , https://docs.catalyst.zoho.com/en/zia-services/
- India DC / data residency (DPDP) — https://www.zoho.com/know-your-datacenter.html
- Zia speech-to-text (English + Hindi, Kannada not yet) — https://www.deccanherald.com/technology/ai-race-zoho-launches-its-own-llm-proprietary-models-for-speech-to-text-conversion-3634773
