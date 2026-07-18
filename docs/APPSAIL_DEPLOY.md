# AppSail Deploy — the working recipe

Everything below is the *verified-correct* configuration. The app code, startup
command, and requirements are all confirmed good; the only thing that has tripped
us up is **getting AppSail to install the Python dependencies**. This doc nails
that down.

## The one rule that matters
AppSail must run `pip install -r requirements.txt` **on its own Linux build** —
we cannot ship the libraries inside the zip (they'd be the wrong platform, and
Zoho's SDK can't be downloaded from the dev machine's network). That install is
triggered by the **Build file** setting. If it's blank, you get
`No module named uvicorn`.

---

## Option A — Console (what you're using)

Recreate the AppSail deployment with **exactly** these values:

| Field | Value |
|---|---|
| Stack | **Python 3.13** |
| **Build file** | **`requirements.txt`**  ← must NOT be blank; this is what installs deps |
| Startup command | **`python3 -u run.py`** |
| Port | `9000` |
| Memory | `1024` |
| Upload | `crime-craft-appsail.zip` |
| Env vars | `APP_ENV=production`, `CATALYST_ENABLED=true`, `JWT_SECRET=<the long value>`, `CATALYST_ENVIRONMENT=production` |

After you deploy, **open the build / deployment log** (not the runtime log). You
are looking for a line like:
```
Successfully installed fastapi-0.115.0 uvicorn-0.32.0 pydantic-2.9.2 ... zcatalyst-sdk-1.2.0
```
- If you see that → the app should now boot. Open `/health`.
- If the build log is **empty / no pip install happened** → the console isn't
  honoring the build file. Switch to Option B.

---

## Option B — CLI from your Windows machine (most reliable)

The CLI installs dependencies on AppSail's Linux build for you. Run these on the
**Windows** box (it has normal internet, so Zoho's SDK downloads fine):

```bash
npm i -g zcatalyst-cli          # once
catalyst login                  # opens browser, sign in

# get the project code onto this machine (git clone, or copy the folder)
cd crime-craft

catalyst init                   # choose the EXISTING project; confirm AppSail + Client
catalyst deploy
```

The CLI reads `catalyst/app-config.json`, which is already set correctly:
- `"stack": "python3.11"`  → change to the version you provisioned if needed
- `"command": "python3 -u run.py"`
- AppSail installs `requirements.txt` during the build.

---

## Sanity checklist (all already done in the repo)
- ✅ `run.py` reads the port in Python and runs uvicorn **in-process** (no `workers`).
- ✅ Startup command uses **`python3`** (not `python`).
- ✅ `requirements.txt` uses **`zcatalyst-sdk`** (not `zcatalyst-sdk-python`) and is lean.
- ✅ Env guard: app refuses to boot unless `CATALYST_ENABLED=true` + a real `JWT_SECRET`.

## If it still fails, capture this and we can finish it
1. The **build log** (does `pip install` run? any error?).
2. The **runtime log** (the `run.py` startup banner — Python version + which env vars are set).
Those two logs tell us exactly what's wrong in one shot.
