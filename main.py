import logging
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import APIRouter, Depends, FastAPI, File, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordRequestForm

from datetime import date as _date

from auth import create_access_token, get_current_user, require_officer, require_roles
from config import get_settings
from middleware import AuditMiddleware
from models import (
    ChatRequest,
    ChatResponse,
    Conversation,
    ConversationSummary,
    HotspotsResponse,
    NetworkResponse,
    RecidivismRequest,
    RecidivismResponse,
    Role,
    TopLocalitiesResponse,
    TrendsResponse,
    User,
)
from services import get_case, list_cases
from services.analytics import crime_trends, hotspots, top_localities
from services.conversations import conversation_repo
from services.ingest import ingest_file
from services.rag import ask as rag_ask

require_admin = require_roles(Role.ADMIN)
require_senior_or_admin = require_roles(Role.SENIOR_OFFICER, Role.ADMIN)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
settings = get_settings()

def _is_production() -> bool:
    return settings.app_env.strip().lower() in {"production", "prod", "staging"}


@asynccontextmanager
async def _lifespan(app: FastAPI):
    # Fail closed: the local JWT login stub assigns roles from the username prefix
    # with NO password check, so it must never be the auth path in production.
    if _is_production():
        if not settings.catalyst_enabled:
            raise RuntimeError(
                "Refusing to start: APP_ENV is production but CATALYST_ENABLED is false. "
                "The local login stub grants roles without a password — enable Catalyst auth."
            )
        if settings.jwt_secret == "dev-only-change-me":
            raise RuntimeError(
                "Refusing to start: default JWT secret in production. Set a strong JWT_SECRET."
            )

    # Index the in-memory seed corpus into the RAG store so chat works over the
    # demo data. Only when the DATA layer is in-memory (not the Catalyst datastore).
    if not settings.catalyst_datastore:
        try:
            from services.rag.indexer import reindex_all

            chunks = reindex_all()
            logging.getLogger("startup").info("indexed seed corpus: %d chunks", chunks)
        except Exception as e:  # noqa: BLE001 — never block startup on indexing
            logging.getLogger("startup").warning("seed indexing skipped: %s", e)
    yield


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=_lifespan)
app.add_middleware(AuditMiddleware)

# All API routes live under /api so the React SPA can own the root paths
# (/cases, /chat, ...) without colliding with the API. Included at the bottom.
api = APIRouter()


@api.get("/health")
def health():
    return {"status": "ok", "env": settings.app_env, "catalyst": settings.catalyst_enabled}


@api.post("/auth/login")
def login(form: OAuth2PasswordRequestForm = Depends()):
    """Local-dev login stub. When CATALYST_ENABLED=true the frontend talks
    directly to Catalyst's hosted login flow, not this endpoint."""
    if settings.catalyst_enabled:
        raise HTTPException(
            status_code=400,
            detail="catalyst is enabled — log in via the Catalyst hosted flow",
        )
    if _is_production():
        # Defense in depth (startup already refuses this combo): never issue
        # stub tokens in production.
        raise HTTPException(
            status_code=503,
            detail="local login is disabled in production; use Catalyst SSO",
        )
    if not form.password:
        raise HTTPException(status_code=400, detail="password required")

    username = form.username.lower()
    if username.startswith("admin_"):
        role = Role.ADMIN
    elif username.startswith("senior_"):
        role = Role.SENIOR_OFFICER
    elif username.startswith("officer_"):
        role = Role.OFFICER
    else:
        role = Role.PUBLIC

    token = create_access_token(user_id=form.username, role=role)
    return {"access_token": token, "token_type": "bearer", "role": role.value}


@api.get("/me")
def me(request: Request, user: User = Depends(get_current_user)):
    request.state.user = user
    return user


@api.get("/cases")
def cases_list(request: Request, user: User = Depends(get_current_user)):
    request.state.user = user
    return list_cases(user.role)


@api.get("/cases/{case_id}")
def case_detail(case_id: str, request: Request, user: User = Depends(get_current_user)):
    request.state.user = user
    case = get_case(case_id, user.role)
    if case is None:
        raise HTTPException(status_code=404, detail="case not found")
    return case


@api.get("/officer/dashboard")
def officer_dashboard(request: Request, user: User = Depends(require_officer)):
    request.state.user = user
    return {"message": f"hello {user.id}", "role": user.role}


@api.get("/analytics/trends", response_model=TrendsResponse)
def analytics_trends(
    request: Request,
    granularity: str = "week",
    from_date: _date | None = None,
    to_date: _date | None = None,
    crime_type: str | None = None,
    locality: str | None = None,
    user: User = Depends(get_current_user),
) -> TrendsResponse:
    """Aggregate counts by week or month, with optional filters. Public-safe."""
    request.state.user = user
    if granularity not in ("week", "month"):
        raise HTTPException(status_code=400, detail="granularity must be 'week' or 'month'")
    return crime_trends(
        granularity=granularity,
        from_date=from_date,
        to_date=to_date,
        crime_type=crime_type,
        locality=locality,
    )


@api.get("/analytics/top-localities", response_model=TopLocalitiesResponse)
def analytics_top_localities(
    request: Request,
    limit: int = 10,
    user: User = Depends(get_current_user),
) -> TopLocalitiesResponse:
    request.state.user = user
    limit = max(1, min(limit, 100))
    return top_localities(limit=limit)


@api.get("/analytics/hotspots", response_model=HotspotsResponse)
def analytics_hotspots(
    request: Request,
    limit: int = 10,
    window_days: int = 30,
    user: User = Depends(get_current_user),
) -> HotspotsResponse:
    request.state.user = user
    limit = max(1, min(limit, 100))
    window_days = max(1, min(window_days, 365))
    return hotspots(limit=limit, window_days=window_days)


@api.post("/chat", response_model=ChatResponse)
def chat(
    req: ChatRequest,
    request: Request,
    user: User = Depends(get_current_user),
) -> ChatResponse:
    """Grounded conversational Q&A over the indexed case corpus.

    Retrieval is role-aware: public callers see OPEN chunks only; officers
    see OPEN + SENSITIVE. Every call is audit-logged.
    """
    request.state.user = user
    return rag_ask(req, user)


@api.post("/conversations", response_model=Conversation)
def create_conversation(request: Request, user: User = Depends(get_current_user)) -> Conversation:
    request.state.user = user
    return conversation_repo().create(user.id)


@api.get("/conversations", response_model=list[ConversationSummary])
def list_conversations(
    request: Request,
    limit: int = 50,
    user: User = Depends(get_current_user),
) -> list[ConversationSummary]:
    request.state.user = user
    limit = max(1, min(limit, 200))
    return conversation_repo().list_for_user(user.id, limit=limit)


@api.get("/conversations/{conversation_id}", response_model=Conversation)
def get_conversation(
    conversation_id: str,
    request: Request,
    user: User = Depends(get_current_user),
) -> Conversation:
    request.state.user = user
    conv = conversation_repo().get(conversation_id, user.id)
    if conv is None:
        raise HTTPException(status_code=404, detail="conversation not found")
    return conv


@api.get("/conversations/{conversation_id}/export.pdf")
def export_conversation_pdf(
    conversation_id: str,
    request: Request,
    user: User = Depends(get_current_user),
):
    """Render a conversation as PDF. Audit-logged like any read. The PDF carries
    an inline watermark with the requesting user and timestamp so leaked copies
    are traceable."""
    request.state.user = user
    from services.pdf import render_conversation, supports_pdf_export

    if not supports_pdf_export():
        raise HTTPException(status_code=503, detail="PDF export not available — install reportlab")
    conv = conversation_repo().get(conversation_id, user.id)
    if conv is None:
        raise HTTPException(status_code=404, detail="conversation not found")
    pdf_bytes = render_conversation(conv, user)
    filename = f"crime-craft-{conv.id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@api.delete("/conversations/{conversation_id}")
def delete_conversation(
    conversation_id: str,
    request: Request,
    user: User = Depends(get_current_user),
):
    request.state.user = user
    if not conversation_repo().delete(conversation_id, user.id):
        raise HTTPException(status_code=404, detail="conversation not found")
    return {"deleted": conversation_id}


@api.post("/voice/transcribe")
async def voice_transcribe(
    request: Request,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    """Speech-to-text. Returns the transcript + detected language so the
    frontend can show the user what was heard before sending it to /chat."""
    request.state.user = user
    from services.voice import transcribe

    audio = await file.read()
    if not audio:
        raise HTTPException(status_code=400, detail="empty audio")
    result = transcribe(audio, filename_hint=file.filename)
    return {
        "text": result.text,
        "language": result.language,
        "duration_seconds": result.duration_seconds,
        "provider": result.provider,
    }


@api.post("/voice/tts")
def voice_tts(
    body: dict,
    request: Request,
    user: User = Depends(get_current_user),
):
    """Text-to-speech. Body: {text: str, language?: 'en'|'hi'|'kn'}.
    Returns binary audio (audio/wav from the stub; provider-dependent live)."""
    request.state.user = user
    from services.voice import synthesize

    text = (body.get("text") or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="text is required")
    lang = body.get("language") or "en"
    result = synthesize(text, language=lang)
    return Response(
        content=result.audio,
        media_type=result.media_type,
        headers={
            "X-Voice-Provider": result.provider,
            "X-Voice-Voice": result.voice,
        },
    )


@api.get("/network/case/{case_id}", response_model=NetworkResponse)
def network_for_case(
    case_id: str,
    request: Request,
    depth: int = 1,
    user: User = Depends(require_officer),
) -> NetworkResponse:
    """Criminal network graph centered on a case. Officer+ only — audit-logged."""
    request.state.user = user
    from services.network import graph_for_case

    depth = max(0, min(depth, 3))
    g = graph_for_case(case_id, depth=depth)
    if g is None:
        raise HTTPException(status_code=404, detail="case not found")
    return g


@api.get("/network/suspect/{name}", response_model=NetworkResponse)
def network_for_suspect(
    name: str,
    request: Request,
    depth: int = 1,
    user: User = Depends(require_officer),
) -> NetworkResponse:
    """Criminal network graph centered on a suspect. Officer+ only — audit-logged."""
    request.state.user = user
    from services.network import graph_for_suspect

    depth = max(0, min(depth, 3))
    g = graph_for_suspect(name, depth=depth)
    if g is None:
        raise HTTPException(status_code=404, detail="suspect not found")
    return g


@api.post("/predictive/recidivism", response_model=RecidivismResponse)
def predictive_recidivism(
    req: RecidivismRequest,
    request: Request,
    user: User = Depends(require_senior_or_admin),
) -> RecidivismResponse:
    """Recidivism risk score for a KNOWN offender. Gated to senior officers
    and admins. Every call is audit-logged with the requester's stated reason —
    a score view with no reason is treated as a bug, not a feature."""
    request.state.user = user
    # Persist the subject + stated reason into the durable audit record (the
    # AuditLog `reason` column) via the audit middleware. A recidivism score
    # with no logged reason is treated as a bug, not a feature.
    request.state.audit_reason = f"recidivism subject={req.subject!r}: {req.reason}"

    from services.predictive import score_subject
    return score_subject(req.subject)


@api.post("/admin/ingest")
async def admin_ingest(
    request: Request,
    file: UploadFile = File(...),
    user: User = Depends(require_admin),
):
    """Manually trigger ingest. Same pipeline used by the hourly cron — see
    `functions/ingest_cron/`. Admin-only because ingest writes to the case table."""
    request.state.user = user
    if not file.filename or not file.filename.lower().endswith((".csv", ".json")):
        raise HTTPException(status_code=400, detail="file must be .csv or .json")

    suffix = Path(file.filename).suffix
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        report = ingest_file(tmp_path)
    finally:
        Path(tmp_path).unlink(missing_ok=True)
    return report.as_dict()


# Mount every API route under /api.
app.include_router(api, prefix="/api")


# --- serve the built React SPA so the whole app (UI + API) lives on one URL ---
# API is under /api; everything else serves the SPA (static asset if it exists,
# else index.html for client-side routes like /cases, /dashboard).
_DIST = Path(__file__).resolve().parent / "apps" / "web" / "dist"
if _DIST.is_dir():
    @app.get("/{full_path:path}", include_in_schema=False)
    def _spa(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="not found")
        candidate = _DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_DIST / "index.html")
