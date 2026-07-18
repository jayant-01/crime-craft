"""AppSail entry point — installs deps (the managed runtime doesn't) + visible errors.

The Catalyst-managed Python runtime does NOT run `pip install -r requirements.txt`,
so we install the dependencies ourselves into a local `.deps` folder on AppSail's
own Linux runtime (correct platform binaries), then run the app. A `predeploy`
script in app-config.json can pre-populate `.deps` to make startup faster; if that
didn't happen (or produced wrong-platform binaries), we (re)install here.

If anything still fails, we serve the traceback at the URL so it's visible.

Startup command:  python3 -u run.py
"""

import importlib
import os
import shutil
import subprocess
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
DEPS = os.path.join(HERE, ".deps")
REQ = os.path.join(HERE, "requirements.txt")
PORT = int(os.getenv("X_ZOHO_CATALYST_LISTEN_PORT", "9000"))

# Make an already-installed .deps importable.
if DEPS not in sys.path:
    sys.path.insert(0, DEPS)


def _deps_ok() -> bool:
    """True if the key deps import (pydantic_core is a compiled pkg — also proves
    the binaries match this platform)."""
    try:
        import pydantic_core  # noqa: F401
        import fastapi  # noqa: F401
        import uvicorn  # noqa: F401
        return True
    except Exception:
        return False


def _install_deps() -> None:
    print("run.py: installing dependencies into .deps (managed runtime doesn't) ...", flush=True)
    shutil.rmtree(DEPS, ignore_errors=True)  # clear any wrong-platform bundle
    os.makedirs(DEPS, exist_ok=True)
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--no-cache-dir", "-r", REQ, "-t", DEPS],
        check=True,
    )
    importlib.invalidate_caches()


def _diagnostics() -> str:
    def present(name: str) -> str:
        v = os.getenv(name)
        if v is None:
            return f"{name}=<MISSING>"
        return f"{name}=<set,len={len(v)}>" if name == "JWT_SECRET" else f"{name}={v!r}"

    try:
        files = ", ".join(sorted(os.listdir("."))[:30])
    except Exception:
        files = "<unreadable>"
    return (
        f"python: {sys.version.split()[0]}\ncwd: {os.getcwd()}\nlisten_port: {PORT}\n"
        f"deps_ok: {_deps_ok()}\nfiles: {files}\n"
        f"config: {present('APP_ENV')} {present('USE_CATALYST')} {present('JWT_SECRET')}\n"
    )


def _serve_error(message: str) -> None:
    from http.server import BaseHTTPRequestHandler, HTTPServer

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(message.encode("utf-8", "replace"))

        def log_message(self, *args):
            pass

    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()


print("=== crime-craft startup ===\n" + _diagnostics(), flush=True)

try:
    if not _deps_ok():
        _install_deps()
    import main
    import uvicorn

    uvicorn.run(main.app, host="0.0.0.0", port=PORT)
except Exception:
    err = "CRIME-CRAFT STARTUP FAILED\n\n" + _diagnostics() + "\n" + traceback.format_exc()
    print(err, flush=True)
    _serve_error(err)
