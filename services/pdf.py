"""Conversation → PDF.

ReportLab-based renderer. Pure Python, no system deps.

Layout:
  - Cover block with title, conversation id, timestamps
  - Each turn as a labeled paragraph (USER / ASSISTANT)
  - Citations rendered as a footer list
  - Watermark on every page noting the user and export time (officer's name +
    timestamp), so a leaked PDF is traceable

The renderer is the only thing that understands the rendering format — if we
later swap to wkhtmltopdf or weasyprint, only this file changes.
"""

from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
from typing import Iterable

from models import Conversation, User


def render_conversation(conv: Conversation, requested_by: User) -> bytes:
    """Render `conv` to a PDF. Returns raw bytes the route can stream back."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib.colors import HexColor
    from reportlab.platypus import (
        BaseDocTemplate,
        Frame,
        PageTemplate,
        Paragraph,
        Spacer,
    )

    buf = BytesIO()
    doc = BaseDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2.5 * cm,
        title=conv.title or "Crime Craft conversation",
        author=requested_by.email,
    )

    watermark_text = (
        f"Exported by {requested_by.email} ({requested_by.role.value}) on "
        f"{datetime.now(timezone.utc).isoformat(timespec='seconds')}"
    )

    def on_page(canvas, _doc):
        canvas.saveState()
        canvas.setFillColor(HexColor("#94a3b8"))
        canvas.setFont("Helvetica", 7)
        canvas.drawString(2 * cm, 1.2 * cm, watermark_text)
        canvas.drawRightString(doc.pagesize[0] - 2 * cm, 1.2 * cm, f"Page {_doc.page}")
        canvas.restoreState()

    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="body")
    doc.addPageTemplates([PageTemplate(id="default", frames=[frame], onPage=on_page)])

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TitleStyle", parent=styles["Title"], textColor=HexColor("#243766"), spaceAfter=12,
    )
    meta_style = ParagraphStyle("Meta", parent=styles["Normal"], textColor=HexColor("#64748b"), fontSize=9)
    user_label = ParagraphStyle(
        "UserLabel", parent=styles["Normal"], fontName="Helvetica-Bold",
        textColor=HexColor("#2f4988"), spaceBefore=10,
    )
    asst_label = ParagraphStyle(
        "AsstLabel", parent=styles["Normal"], fontName="Helvetica-Bold",
        textColor=HexColor("#0f766e"), spaceBefore=10,
    )
    body = ParagraphStyle("Body", parent=styles["BodyText"], leading=14)

    story: list = [
        Paragraph(conv.title or "Crime Craft — conversation", title_style),
        Paragraph(
            f"ID: <font face='Courier'>{conv.id}</font>  ·  "
            f"Created: {conv.created_at:%Y-%m-%d %H:%M UTC}  ·  "
            f"Updated: {conv.updated_at:%Y-%m-%d %H:%M UTC}",
            meta_style,
        ),
        Spacer(1, 0.4 * cm),
    ]

    for turn in conv.turns:
        label = user_label if turn.role == "user" else asst_label
        story.append(Paragraph(turn.role.upper(), label))
        story.append(Paragraph(_escape(turn.content), body))

    if not conv.turns:
        story.append(Paragraph("(no turns yet)", meta_style))

    doc.build(story)
    return buf.getvalue()


def _escape(text: str) -> str:
    """ReportLab Paragraph uses a tiny XML-like syntax, so HTML-escape user
    content first. Newlines become <br/>."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", "<br/>")
    )


def supports_pdf_export() -> bool:
    """Returns False if reportlab isn't installed — lets the route return a
    clean 503 instead of a stack trace."""
    try:
        import reportlab  # noqa: F401
    except ImportError:
        return False
    return True


# Exported for type-checker satisfaction in the route, even though we use Conversation/User
__all__: Iterable[str] = ("render_conversation", "supports_pdf_export")
