# Crime Craft — Live Demo Script

A **5-minute walkthrough** designed for hackathon judges and KSP pilot stakeholders.
Hits every shipped feature in a story-driven order: citizen view → officer view → senior-officer tools.

> **Before you start.** Run `make seed && make dev` in two panes. Wait until the frontend prints
> `Local: http://localhost:5173`. Open it in a fresh incognito window so localStorage is clean.

---

## Act 1 — The citizen (60 seconds)

**Story:** A resident of HSR Layout wants to know if there's been a recent crime spike in their area.

1. **Login** at <http://localhost:5173>
   - Username: `alice` · Password: `anything`
   - Role pill in the header shows **PUBLIC**.
2. **Cases tab** — show the redacted public view:
   - Only `case_id`, `crime_type`, `locality`, `occurred_on`, `status` columns.
   - No names, no narrative, no MO details.
3. **Click a case** — confirm the detail page shows the same five fields plus the footnote
   *"Additional fields are visible to authorized officers only."*
4. **Chat tab** — ask: *"Any thefts in HSR Layout?"*
   - Response cites `[FIR-2025-1001]` as a chip.
   - **Click the chip** → navigates back to the public-redacted case page.
   - Point out: the citizen never sees a name or phone number, even though the case file contains them.

> 🎯 **Talking point:** Same backend, same RAG pipeline, same audit log — public users get strictly redacted access through one chokepoint, not per-route handwritten checks.

---

## Act 2 — The officer (90 seconds)

**Story:** An investigating officer wants to assemble context on a string of HSR Layout thefts.

1. **Logout · Login as** `officer_priya` (any password)
   - Role pill now reads **OFFICER**.
2. **Same case** — now you see `street_address`, `mo_details`, `narrative`. Names and phones
   are visible because they're structured columns; free-text PII (Aadhaar / PAN / vehicle reg /
   emails inside narratives) has been redacted at ingest by [services/pii.py](services/pii.py).
3. **Chat tab** — ask in Hindi: *एचएसआर लेआउट में चोरी की रिपोर्ट?*
   - Show the **HI badge** on the assistant bubble — language was auto-detected.
   - Click the **🔊 button** — the answer is read aloud (browser TTS falls back when backend TTS is stubbed).
4. **Voice input** — click the 🎤 button, say *"Any recent burglaries?"*, click again to stop.
   - Transcript appears in the draft field. Hit Send.
5. **Conversation sidebar** — click the ⇣ icon next to a conversation.
   - PDF opens in a new tab with a **watermark** on every page showing the exporter's email,
     role, and UTC timestamp. Drag-and-share-traceable.

> 🎯 **Talking point:** Every voice + PDF + chat action is audit-logged by
> [middleware/audit.py](middleware/audit.py), with caller, route, status, and latency. The
> middleware writes to the Catalyst `AuditLog` table in prod.

---

## Act 3 — The senior officer (90 seconds)

**Story:** A senior officer is reviewing case linkages and a parole-eligibility question.

1. **Logout · Login as** `senior_jayant`
   - Role pill reads **SENIOR_OFFICER**. Two new tabs appear: **Network**, **Recidivism**.
2. **Dashboard** — show the trend bar chart, top localities, and hotspots (recent-30d window).
3. **Network tab**
   - Mode = **By case**, query = `FIR-2025-1002`, depth = `1`, click **Render**.
   - Show the Cytoscape graph: blue rectangles = cases, red circles = suspects, dashed lines =
     co-suspect relationships, yellow border = the center node.
   - Switch mode to **By suspect**, query = `Ravi Kumar`. Shows the cases linking back to him.
4. **Recidivism tab** (senior+ only)
   - Subject: `Ravi Kumar`
   - Reason: `Reviewing active investigation in Indiranagar for procedural decision.`
   - Click **Score subject**.
   - Show the **risk band**, the **SHAP contributions** with plain-English explanations
     ("3 prior cases linked to subject — increases risk"), and the bright amber
     **ADVISORY ONLY** banner.
   - Mention: the **reason field is required**. A score view with no logged reason is treated
     as a bug, not a feature.

> 🎯 **Talking point:** Track 2 (recidivism) is the highest-risk feature ethically. Every score
> is audit-logged with the requester's stated reason, every contribution is human-readable,
> and the UI is unambiguous that this is a decision aid — not a decision.

---

## Act 4 — Under the hood (60 seconds, optional)

If you have time, show the engineering surface:

1. **Open `/docs`** at <http://localhost:8000/docs> — the auto-generated OpenAPI panel.
   - 18 endpoints, every one role-gated where appropriate.
2. **Run `make test`** — ~108 tests, all offline, no API keys.
3. **Open [catalyst/datastore-schema.json](catalyst/datastore-schema.json)** — show the four
   tables (`Cases`, `AuditLog`, `Conversations`, `CaseEmbeddings`) defined as the source of
   truth that gets provisioned via the Catalyst console.
4. **Toggle the flags** — `CATALYST_ENABLED=false → true`, `RAG_PROVIDER=stub → live`.
   Same code; what changes is which providers get instantiated by the factory functions in
   [services/datastore.py](services/datastore.py) and [services/rag/](services/rag/).

---

## Demo cheat sheet

| Persona | Username | Sees |
|---|---|---|
| Citizen | `alice` | Redacted case fields only, chat with citations |
| Officer | `officer_priya` | Full case dossiers, chat with full retrieval, voice |
| Senior officer | `senior_jayant` | Officer view + Network + Recidivism |
| Admin | `admin_jayant` | Everything + `/admin/ingest` |

| URL | What |
|---|---|
| <http://localhost:5173> | Frontend |
| <http://localhost:8000/docs> | Backend OpenAPI |
| <http://localhost:8000/health> | Liveness probe (`{"status":"ok"}`) |

| Sample queries | Why |
|---|---|
| `Any thefts in HSR Layout?` | RAG retrieval + citation |
| `एचएसआर लेआउट में चोरी?` | Language detection (Hindi) |
| `ಕಳ್ಳತನ HSR Layout` | Language detection (Kannada) |
| `Tell me about FIR-2025-1004` | Direct case lookup via RAG |

---

## If something breaks during demo

| Symptom | Quick fix |
|---|---|
| Empty cases list | `make seed` and refresh |
| Chat returns "I do not have that…" | `make seed` — the in-memory vector store was reset |
| Mic button does nothing | Browser permission denied — fall back to typing |
| PDF download 503 | `pip install reportlab` — only happens if requirements didn't fully install |
| Network graph blank | Search for `FIR-2025-1002` or `Ravi Kumar` — the sample data has two named suspects |

---

## What to say if a judge asks…

**"Where's the real data?"**
> Under MoU with KSP. We can't put it on a laptop. [data/](data/) holds only synthetic samples
> with deliberately embedded PII so the redaction pipeline gets exercised. Production data
> lives in the Catalyst Datastore in the Indian region.

**"Is the LLM trained on KSP data?"**
> No. We use a hosted Claude Sonnet 4.6 via API with RAG — retrieval over our own
> case-chunk embeddings, then grounded generation. No KSP data crosses the inference boundary
> outside the retrieval window. Data-residency review for the provider is on the open-questions list.

**"How does the recidivism scorer avoid the COMPAS / PredPol failure mode?"**
> Three guardrails: (1) it scores **known** offenders only — refuses to score anyone without
> prior cases; (2) every score requires a logged reason and is shown to senior officers only;
> (3) the response carries a mandatory "advisory only, human-in-the-loop required" note.
> Bias audit is on the roadmap before this goes live in production.

**"What's the ethics-and-bias plan?"**
> See README §6b and §12. The hackathon scope shows the surface; production launch is gated
> on independent academic + KSP review of recidivism outputs across demographic slices.
