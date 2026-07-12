"""AppSail entry point.

Starting uvicorn via a shell command relies on the shell expanding
`$X_ZOHO_CATALYST_LISTEN_PORT`, which doesn't always happen on AppSail and leaves
uvicorn with an invalid port (the app then fails to start). Reading the port here
in Python is unambiguous: we use the platform-provided port, or 9000 by default.

Startup command:  python run.py
"""

import os

import uvicorn

if __name__ == "__main__":
    port = int(os.getenv("X_ZOHO_CATALYST_LISTEN_PORT", "9000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, workers=1)
