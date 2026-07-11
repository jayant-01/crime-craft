"""Conversation persistence.

Same dual-impl pattern as the case datastore: an in-memory implementation
for local dev / tests, and a Catalyst implementation for prod. Stored history
lets the frontend resume a session and lets us replay context to the LLM.

Conversations are user-scoped — listing returns only the caller's
conversations, and a fetch on a foreign id returns None.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Protocol

from models import ChatTurn, Conversation, ConversationSummary
from services.catalyst_client import get_catalyst, is_enabled as catalyst_enabled


class ConversationRepository(Protocol):
    def create(self, user_id: str, title: str | None = None) -> Conversation: ...
    def get(self, conversation_id: str, user_id: str) -> Conversation | None: ...
    def list_for_user(self, user_id: str, limit: int = 50) -> list[ConversationSummary]: ...
    def append_turns(self, conversation_id: str, user_id: str, turns: list[ChatTurn]) -> Conversation | None: ...
    def delete(self, conversation_id: str, user_id: str) -> bool: ...


def _now() -> datetime:
    return datetime.now(timezone.utc)


# --- in-memory implementation ---------------------------------------------

class InMemoryConversationRepo:
    def __init__(self) -> None:
        self._rows: dict[str, Conversation] = {}

    def create(self, user_id: str, title: str | None = None) -> Conversation:
        cid = f"conv_{uuid.uuid4().hex[:12]}"
        now = _now()
        conv = Conversation(
            id=cid,
            user_id=user_id,
            title=title,
            created_at=now,
            updated_at=now,
            turns=[],
        )
        self._rows[cid] = conv
        return conv

    def get(self, conversation_id: str, user_id: str) -> Conversation | None:
        c = self._rows.get(conversation_id)
        if c is None or c.user_id != user_id:
            return None
        return c

    def list_for_user(self, user_id: str, limit: int = 50) -> list[ConversationSummary]:
        items = [c for c in self._rows.values() if c.user_id == user_id]
        items.sort(key=lambda c: c.updated_at, reverse=True)
        return [
            ConversationSummary(
                id=c.id, title=c.title, created_at=c.created_at,
                updated_at=c.updated_at, turn_count=len(c.turns),
            )
            for c in items[:limit]
        ]

    def append_turns(self, conversation_id: str, user_id: str, turns: list[ChatTurn]) -> Conversation | None:
        c = self.get(conversation_id, user_id)
        if c is None:
            return None
        new_turns = c.turns + turns
        # Auto-title from the first user message, once we have one.
        title = c.title
        if title is None:
            for t in new_turns:
                if t.role == "user":
                    title = t.content[:80]
                    break
        updated = c.model_copy(update={"turns": new_turns, "updated_at": _now(), "title": title})
        self._rows[conversation_id] = updated
        return updated

    def delete(self, conversation_id: str, user_id: str) -> bool:
        c = self._rows.get(conversation_id)
        if c is None or c.user_id != user_id:
            return False
        self._rows.pop(conversation_id, None)
        return True


# --- Catalyst implementation ----------------------------------------------

def _zcql_literal(value: str) -> str:
    """Escape a value for safe interpolation inside a single-quoted ZCQL string
    literal: strip control chars and double any single quotes. Without this,
    user-controlled ids/user_ids allow ZCQL injection (cross-user read/delete)."""
    cleaned = "".join(ch for ch in str(value) if ch >= " " and ch != "\x7f")
    return cleaned.replace("'", "''")


class CatalystConversationRepo:
    """One row per conversation; turns serialized as JSON in a single column.
    Acceptable for the 6-month MVP — conversations are small (~50 turns max)."""

    TABLE = "Conversations"

    def _table(self):
        return get_catalyst().datastore().table(self.TABLE)

    def create(self, user_id: str, title: str | None = None) -> Conversation:
        cid = f"conv_{uuid.uuid4().hex[:12]}"
        now = _now()
        conv = Conversation(id=cid, user_id=user_id, title=title, created_at=now, updated_at=now)
        self._table().insert_row(self._to_row(conv))
        return conv

    def get(self, conversation_id: str, user_id: str) -> Conversation | None:
        ds = get_catalyst().datastore()
        rows = ds.execute_zcql_query(
            f"SELECT * FROM {self.TABLE} WHERE id = '{_zcql_literal(conversation_id)}' "
            f"AND user_id = '{_zcql_literal(user_id)}'"
        )
        if not rows:
            return None
        return self._from_row(rows[0].get(self.TABLE, rows[0]))

    def list_for_user(self, user_id: str, limit: int = 50) -> list[ConversationSummary]:
        ds = get_catalyst().datastore()
        rows = ds.execute_zcql_query(
            f"SELECT id, title, created_at, updated_at, turns FROM {self.TABLE} "
            f"WHERE user_id = '{_zcql_literal(user_id)}' ORDER BY updated_at DESC LIMIT {int(limit)}"
        )
        out: list[ConversationSummary] = []
        for r in rows:
            row = r.get(self.TABLE, r)
            import json
            turns_count = len(json.loads(row.get("turns") or "[]"))
            out.append(
                ConversationSummary(
                    id=row["id"],
                    title=row.get("title"),
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                    turn_count=turns_count,
                )
            )
        return out

    def append_turns(self, conversation_id: str, user_id: str, turns: list[ChatTurn]) -> Conversation | None:
        existing = self.get(conversation_id, user_id)
        if existing is None:
            return None
        new_turns = existing.turns + turns
        title = existing.title
        if title is None:
            for t in new_turns:
                if t.role == "user":
                    title = t.content[:80]
                    break
        updated = existing.model_copy(update={"turns": new_turns, "updated_at": _now(), "title": title})
        # Catalyst Datastore update by ROWID lookup is finicky from the SDK; the simplest
        # safe path is delete + insert. Atomicity isn't critical for chat history.
        try:
            ds = get_catalyst().datastore()
            ds.execute_zcql_query(
            f"DELETE FROM {self.TABLE} WHERE id = '{_zcql_literal(conversation_id)}' "
            f"AND user_id = '{_zcql_literal(user_id)}'"
        )
            self._table().insert_row(self._to_row(updated))
        except Exception:
            import logging
            logging.getLogger("conversations").exception("catalyst conversation update failed")
            return None
        return updated

    def delete(self, conversation_id: str, user_id: str) -> bool:
        existing = self.get(conversation_id, user_id)
        if existing is None:
            return False
        ds = get_catalyst().datastore()
        ds.execute_zcql_query(
            f"DELETE FROM {self.TABLE} WHERE id = '{_zcql_literal(conversation_id)}' "
            f"AND user_id = '{_zcql_literal(user_id)}'"
        )
        return True

    @staticmethod
    def _to_row(conv: Conversation) -> dict[str, Any]:
        import json
        return {
            "id": conv.id,
            "user_id": conv.user_id,
            "title": conv.title,
            "created_at": conv.created_at.isoformat(),
            "updated_at": conv.updated_at.isoformat(),
            "turns": json.dumps([t.model_dump() for t in conv.turns]),
        }

    @staticmethod
    def _from_row(row: dict[str, Any]) -> Conversation:
        import json
        return Conversation(
            id=row["id"],
            user_id=row["user_id"],
            title=row.get("title"),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            turns=[ChatTurn(**t) for t in json.loads(row.get("turns") or "[]")],
        )


# --- factory --------------------------------------------------------------

_repo: ConversationRepository | None = None


def conversation_repo() -> ConversationRepository:
    global _repo
    if _repo is None:
        _repo = CatalystConversationRepo() if catalyst_enabled() else InMemoryConversationRepo()
    return _repo


def reset_for_tests() -> None:
    global _repo
    _repo = None
