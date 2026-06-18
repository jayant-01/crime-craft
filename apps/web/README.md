# Crime Craft — Frontend

React 18 + Vite + Tailwind + TypeScript. Talks to the FastAPI backend at
`http://localhost:8000` via a Vite proxy on `/api`.

## Run

```bash
# From repo root
make install-frontend
make dev-frontend

# Or directly:
cd apps/web
npm install
npm run dev          # http://localhost:5173
```

Backend must be running too — `make dev-backend` in another pane.

## Login (local dev)

The backend's local-dev `/auth/login` accepts **any password** while
`CATALYST_ENABLED=false`. Username prefix sets the role:

| Username           | Role             | Sees                                              |
|--------------------|------------------|---------------------------------------------------|
| `alice`            | PUBLIC           | Redacted case fields, public-safe chat            |
| `officer_priya`    | OFFICER          | Full case dossiers, network graph, dashboard, PDF |
| `senior_jayant`    | SENIOR_OFFICER   | Everything OFFICER sees + recidivism scoring      |
| `admin_jayant`     | ADMIN            | Senior + admin ingest endpoint                    |

When `CATALYST_ENABLED=true`, this endpoint refuses and the frontend should
redirect to the Catalyst hosted login flow. That swap is on the TODO list —
see [../../catalyst/README.md](../../catalyst/README.md).

## Routes

| Path             | Role          | Page                                                    |
|------------------|---------------|---------------------------------------------------------|
| `/login`         | anyone        | Sign in                                                 |
| `/cases`         | any signed-in | Case list (redacted for public, full for officers)      |
| `/cases/:id`     | any signed-in | Case detail (role-aware fields)                         |
| `/chat`          | any signed-in | RAG chat — voice in/out, language detection, citation chips, PDF export |
| `/dashboard`     | officer+      | Weekly trend bar chart, top localities, hotspots        |
| `/network`       | officer+      | Cytoscape.js interactive case/suspect graph             |
| `/recidivism`    | senior+       | XGBoost + SHAP recidivism risk scoring                  |

## Source layout

```
src/
├── api/
│   ├── client.ts         # single chokepoint: JWT injection, 401 → logout
│   ├── types.ts          # TypeScript mirrors of Pydantic models
│   └── endpoints.ts      # authApi, casesApi, chatApi, conversationsApi,
│                         # analyticsApi, voiceApi, pdfApi, predictiveApi, networkApi
├── auth/
│   ├── AuthContext.tsx   # JWT in localStorage, /me hydration on boot
│   └── (hasRole helper)
├── voice/
│   ├── useMicRecorder.ts # MediaRecorder hook, clean tear-down on stop
│   └── speak.ts          # backend TTS first → browser speechSynthesis fallback
├── components/
│   ├── Layout.tsx        # header + role pill + nav
│   └── ProtectedRoute.tsx # auth + optional role gate
└── pages/
    ├── LoginPage.tsx
    ├── CasesPage.tsx
    ├── CaseDetailPage.tsx
    ├── ChatPage.tsx          # mic, 🔊, language badge, PDF export ⇣
    ├── DashboardPage.tsx     # CSS-grid bar chart (no chart library)
    ├── NetworkPage.tsx       # Cytoscape.js — case/suspect modes, URL-synced
    └── RecidivismPage.tsx    # required-reason form + SHAP contributions
```

## Voice integration

Two paths, picked at runtime:

1. **Backend** — `POST /voice/transcribe` (multipart audio) and `POST /voice/tts` (JSON in, audio/wav out). Stubbed by default; flip `VOICE_PROVIDER=live` to enable Whisper STT (after `pip install openai-whisper`) and a real Indic TTS provider.
2. **Browser fallback** — when the backend TTS is in stub mode (returns a silent WAV), [voice/speak.ts](src/voice/speak.ts) transparently falls back to `window.speechSynthesis` so the user still hears something. STT has no browser fallback in production (Web Speech API is Chrome-only and not accurate enough for Hindi/Kannada).

## PDF export

Each conversation in the sidebar has a ⇣ icon that opens `/api/conversations/:id/export.pdf`
in a new tab. The PDF is rendered server-side by [services/pdf.py](../../services/pdf.py)
with a per-page watermark identifying the requester — see [../../DEMO.md](../../DEMO.md).

## Build for production

```bash
npm run build           # → apps/web/dist/
make catalyst-deploy    # builds + ships to Catalyst (frontend → Client, backend → AppSail)
```

The Vite proxy on `/api` only applies in dev — in production the React app calls the same
origin and the FastAPI backend serves under the same hostname (per Catalyst's routing).
