"""Speech-to-text.

Provider behind a thin interface so prod can swap implementations without
touching the route. We default to a stub that returns a placeholder
transcript — useful for wiring the frontend and tests without a model
download. Real STT requires `openai-whisper` (~150MB+ + model weights) and
gets enabled via `VOICE_PROVIDER=live` and `pip install openai-whisper`.
"""

from __future__ import annotations

import logging
import os
import tempfile
from dataclasses import dataclass

log = logging.getLogger("voice.stt")


@dataclass(frozen=True)
class Transcript:
    text: str
    language: str        # ISO 639-1 code: "en" | "hi" | "kn" | ...
    duration_seconds: float
    provider: str        # "whisper" | "stub"


def stt_provider_name() -> str:
    return os.environ.get("VOICE_PROVIDER", "stub")


def transcribe(audio_bytes: bytes, filename_hint: str | None = None) -> Transcript:
    if not audio_bytes:
        raise ValueError("audio is empty")

    if stt_provider_name() == "live":
        return _whisper_transcribe(audio_bytes, filename_hint)
    return _stub_transcribe(audio_bytes, filename_hint)


def _stub_transcribe(audio_bytes: bytes, filename_hint: str | None) -> Transcript:
    # Deterministic so tests and frontend wiring have something stable.
    seconds = max(1.0, len(audio_bytes) / 32_000.0)  # rough estimate at 16-bit / 16kHz
    return Transcript(
        text="[stub transcription — set VOICE_PROVIDER=live and install openai-whisper]",
        language="en",
        duration_seconds=round(seconds, 2),
        provider="stub",
    )


def _whisper_transcribe(audio_bytes: bytes, filename_hint: str | None) -> Transcript:
    """Real STT. Lazy-imports whisper. The model name is configurable; default
    `small` is a reasonable English/Hindi tradeoff. For Kannada use `medium`."""
    try:
        import whisper  # type: ignore
    except ImportError as e:
        raise RuntimeError(
            "VOICE_PROVIDER=live but openai-whisper isn't installed. "
            "Run `pip install openai-whisper` (large download)."
        ) from e

    model_name = os.environ.get("WHISPER_MODEL", "small")
    suffix = ".webm" if (filename_hint or "").endswith(".webm") else ".wav"

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        model = whisper.load_model(model_name)
        result = model.transcribe(tmp_path)
        return Transcript(
            text=str(result.get("text", "")).strip(),
            language=str(result.get("language", "en")),
            duration_seconds=float(result.get("duration", 0.0) or 0.0),
            provider="whisper",
        )
    finally:
        from pathlib import Path
        Path(tmp_path).unlink(missing_ok=True)
