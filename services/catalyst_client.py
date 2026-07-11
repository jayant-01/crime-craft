"""Single chokepoint for the Zoho Catalyst SDK.

We deliberately wrap the SDK so the rest of the codebase imports `get_catalyst()`
and never `zcatalyst_sdk` directly. That gives us:
  - one place to mock for tests
  - one place to swap if the SDK API shifts between versions
  - one place to inject request headers when running under AppSail

The SDK signatures below follow `zcatalyst-sdk-python` 1.x — verify against
the installed version when you wire real credentials.
"""

from __future__ import annotations

from typing import Any

from config import get_settings

_settings = get_settings()
_app_instance: Any | None = None


def is_enabled() -> bool:
    return _settings.catalyst_enabled


def _build_admin_credentials() -> dict[str, str]:
    """Credentials used when initializing outside of an AppSail request context
    (e.g. background jobs, the ingest cron, local admin scripts)."""
    return {
        "project_id": _settings.catalyst_project_id,
        "project_domain": _settings.catalyst_project_domain,
        "project_key": _settings.catalyst_project_key,
        "environment": _settings.catalyst_environment,
        "client_id": _settings.catalyst_client_id,
        "client_secret": _settings.catalyst_client_secret,
        "refresh_token": _settings.catalyst_refresh_token,
    }


def get_catalyst(request_headers: dict[str, str] | None = None) -> Any:
    """Returns an initialized Catalyst app instance.

    When called from a FastAPI route, pass `request_headers` so the SDK can pick
    up the caller's auth context (`Authorization`, `x-zc-*` cookies). When called
    from a job or CLI, headers are omitted and admin credentials are used.
    """
    if not is_enabled():
        raise RuntimeError("catalyst is disabled (CATALYST_ENABLED=false)")

    import zcatalyst_sdk  # imported lazily so local dev doesn't require the package

    if request_headers:
        # Request-scoped: the SDK reads identity from headers.
        return zcatalyst_sdk.initialize(request_headers)

    global _app_instance
    if _app_instance is None:
        creds = _build_admin_credentials()
        if creds.get("client_id") and creds.get("refresh_token"):
            # Explicit self-client credentials — needed only when running OUTSIDE
            # Catalyst (local admin scripts, external jobs).
            _app_instance = zcatalyst_sdk.initialize_with_credentials(creds)
        else:
            # Inside AppSail/Functions the SDK authenticates automatically from the
            # platform context — no OAuth tokens required.
            _app_instance = zcatalyst_sdk.initialize()
    return _app_instance


def reset_for_tests() -> None:
    global _app_instance
    _app_instance = None
