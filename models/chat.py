from datetime import date, datetime
from pydantic import BaseModel, Field


class Citation(BaseModel):
    case_id: str
    locality: str | None = None
    occurred_on: date | None = None
    crime_type: str | None = None
    score: float | None = None


class ChatTurn(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    top_k: int = Field(6, ge=1, le=20)
    filters: dict[str, str] | None = None
    history: list[ChatTurn] = []           # caller-provided history (overrides stored history)
    conversation_id: str | None = None     # if set, server loads & persists history for this conversation


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation]
    retrieved_chunk_ids: list[str]
    model: str
    conversation_id: str | None = None     # echoed back so the frontend can keep using it
    detected_language: str = "en"          # "en" | "hi" | "kn"


class Conversation(BaseModel):
    id: str
    user_id: str
    title: str | None = None
    created_at: datetime
    updated_at: datetime
    turns: list[ChatTurn] = []


class ConversationSummary(BaseModel):
    id: str
    title: str | None
    created_at: datetime
    updated_at: datetime
    turn_count: int
