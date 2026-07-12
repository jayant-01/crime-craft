"""AppSail entry point + startup diagnostics.

Reads the platform port (X_ZOHO_CATALYST_LISTEN_PORT, default 9000) in Python to
avoid shell env-var expansion issues, and prints a startup banner so a failed
boot shows a clear reason in the AppSail logs instead of a generic 500.
"""

import os
import sys
import traceback


def _present(name: str) -> str:
    v = os.getenv(name)
    if v is None:
        return f"{name}=<MISSING>"
    if name == "JWT_SECRET":
        return f"{name}=<set,len={len(v)}>"
    return f"{name}={v!r}"


port = int(os.getenv("X_ZOHO_CATALYST_LISTEN_PORT", "9000"))

print("=" * 60, flush=True)
print("crime-craft AppSail startup", flush=True)
print(f"python: {sys.version.split()[0]}  cwd: {os.getcwd()}", flush=True)
print("files:", ", ".join(sorted(os.listdir("."))[:25]), flush=True)
print("config:", _present("APP_ENV"), _present("CATALYST_ENABLED"),
      _present("JWT_SECRET"), _present("CATALYST_ENVIRONMENT"), flush=True)
print(f"listen port: {port}", flush=True)
print("=" * 60, flush=True)

try:
    import main  # noqa: F401  — triggers config load + app build
    print("import main: OK", flush=True)
except Exception:
    print("import main: FAILED\n" + traceback.format_exc(), flush=True)
    raise

import uvicorn

try:
    # Pass the app object directly (single process, no reload/workers) — the most
    # robust launch path for AppSail.
    uvicorn.run(main.app, host="0.0.0.0", port=port)
except Exception:
    print("uvicorn.run FAILED (startup/lifespan error):\n" + traceback.format_exc(), flush=True)
    raise
