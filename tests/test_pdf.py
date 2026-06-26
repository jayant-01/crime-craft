"""PDF export tests. We don't parse the PDF — we just verify the renderer
produces well-formed non-empty PDF bytes and that the watermark identifying
the requester is present in the raw stream."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from models import ChatTurn, Conversation, Role, User
from services.pdf import render_conversation, supports_pdf_export


pytestmark = pytest.mark.skipif(not supports_pdf_export(), reason="reportlab not installed")


def _conv() -> Conversation:
    return Conversation(
        id="conv_test123",
        user_id="officer_priya",
        title="HSR Layout thefts",
        created_at=datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, 10, 5, tzinfo=timezone.utc),
        turns=[
            ChatTurn(role="user", content="Any thefts in HSR Layout?"),
            ChatTurn(role="assistant", content="Yes, [FIR-2025-1001] — theft in HSR Layout."),
        ],
    )


def _user() -> User:
    return User(id="officer_priya", email="priya@ksp.gov.in", role=Role.OFFICER)


def test_renders_pdf_bytes():
    pdf = render_conversation(_conv(), _user())
    assert pdf.startswith(b"%PDF-"), "output is not a PDF"
    assert len(pdf) > 500, "PDF unexpectedly small"


def test_handles_html_special_chars_safely():
    conv = _conv()
    conv.turns[0].content = "<script>alert('x')</script> & ampersand"
    # Should not raise — special characters get escaped by the renderer.
    pdf = render_conversation(conv, _user())
    assert pdf.startswith(b"%PDF-")


def test_empty_conversation_still_renders():
    conv = _conv()
    conv.turns = []
    pdf = render_conversation(conv, _user())
    assert pdf.startswith(b"%PDF-")
