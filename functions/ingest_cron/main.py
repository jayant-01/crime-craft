"""Hourly ingest Catalyst Cron function.

Triggered by the cron schedule in `catalyst-config.json`. Pulls any new CSV
files from the configured Catalyst File Store folder and runs them through
the standard ingest pipeline.

The function reuses our `services.ingest` module verbatim — so the same code
path runs whether ingest is triggered by:
  - this hourly cron
  - the admin `POST /admin/ingest` endpoint
  - the CLI `python -m services.ingest <path>`

If you change ingest logic, you change it in one place.
"""

from __future__ import annotations

import logging
import os
import sys
import tempfile
from pathlib import Path

# Add repo root to sys.path so Catalyst's function sandbox can import our package.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import zcatalyst_sdk

from services.ingest import ingest_file

log = logging.getLogger("ingest_cron")

# Folder in Catalyst File Store where KSP drops new CSVs. The exact folder
# ID is provisioned in the Catalyst Console and supplied via env var.
INBOX_FOLDER_ID = os.environ.get("INGEST_INBOX_FOLDER_ID", "")
PROCESSED_FOLDER_ID = os.environ.get("INGEST_PROCESSED_FOLDER_ID", "")


def handler(event: dict, context):  # noqa: ARG001 — Catalyst Cron signature
    logging.basicConfig(level=logging.INFO)
    if not INBOX_FOLDER_ID:
        log.error("INGEST_INBOX_FOLDER_ID not configured; skipping run")
        return {"status": "skipped", "reason": "no inbox configured"}

    app = zcatalyst_sdk.initialize(context)
    filestore = app.filestore()
    inbox = filestore.folder(INBOX_FOLDER_ID)

    files = inbox.get_files()  # SDK returns metadata list
    reports = []

    for meta in files:
        name = meta.get("file_name") or meta.get("name") or "unknown"
        if not name.lower().endswith((".csv", ".json")):
            continue

        log.info("processing %s", name)
        with tempfile.NamedTemporaryFile(suffix=Path(name).suffix, delete=False) as tmp:
            inbox.file(meta["file_id"]).download(tmp.name)
            tmp_path = tmp.name

        try:
            report = ingest_file(tmp_path)
            reports.append(report.as_dict())
            # Move to processed/ so we don't double-ingest next hour.
            if PROCESSED_FOLDER_ID:
                inbox.file(meta["file_id"]).move(PROCESSED_FOLDER_ID)
        except Exception:
            log.exception("ingest failed for %s", name)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    return {"status": "ok", "reports": reports}
