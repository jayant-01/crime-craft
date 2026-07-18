"""AppSail entry point with VISIBLE error reporting.

AppSail hides startup errors behind a generic "execution failed" page, and its
logs have been hard to reach. So if the real app fails to import or start (a
missing dependency, a config error, etc.), we fall back to a tiny stdlib HTTP
server that serves the actual traceback + diagnostics at the URL — so we can
finally SEE what's wrong in the browser.

When everything is fine, uvicorn runs the real app and this fallback never fires.

Startup command:  python3 -u run.py
"""

import os
import sys
import traceback

PORT = int(os.getenv("X_ZOHO_CATALYST_LISTEN_PORT", "9000"))


def _diagnostics() -> str:
    def present(name: str) -> str:
        v = os.getenv(name)
        if v is None:
            return f"{name}=<MISSING>"
        if name == "JWT_SECRET":
            return f"{name}=<set,len={len(v)}>"
        return f"{name}={v!r}"

    try:
        files = ", ".join(sorted(os.listdir("."))[:30])
    except Exception:
        files = "<unreadable>"
    return (
        f"python: {sys.version.split()[0]}\n"
        f"cwd: {os.getcwd()}\n"
        f"listen_port: {PORT}\n"
        f"files: {files}\n"
        f"config: {present('APP_ENV')} {present('USE_CATALYST')} "
        f"{present('JWT_SECRET')}\n"
    )


def _serve_error(message: str) -> None:
    """Tiny stdlib server (no third-party deps) that returns the error text."""
    from http.server import BaseHTTPRequestHandler, HTTPServer

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(message.encode("utf-8", "replace"))

        def log_message(self, *args):  # silence
            pass

    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()


print("=== crime-craft startup ===\n" + _diagnostics(), flush=True)

try:
    import main
    import uvicorn

    uvicorn.run(main.app, host="0.0.0.0", port=PORT)
except Exception:
    tb = traceback.format_exc()
    err = "CRIME-CRAFT STARTUP FAILED\n\n" + _diagnostics() + "\n" + tb
    print(err, flush=True)
    _serve_error(err)
