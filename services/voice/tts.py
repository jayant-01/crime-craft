"""Text-to-speech.

Default stub returns a silent WAV file matching the requested duration —
enough for the frontend to wire its audio player without a real TTS backend.

Real Indic TTS options the prod path can plug into:
  - Bhashini (govt of India)
  - AI4Bharat IndicTTS
  - ElevenLabs / Google Cloud TTS (residency review needed)

The route is identical across providers: text + lang → audio/wav bytes.
"""

from __future__ import annotations

import io
import os
import struct
from dataclasses import dataclass


@dataclass(frozen=True)
class SynthResult:
    audio: bytes              # raw audio/wav bytes
    media_type: str           # "audio/wav" | "audio/mpeg"
    provider: str             # "bhashini" | "indic-tts" | "stub"
    voice: str                # provider-specific voice id


def tts_provider_name() -> str:
    return os.environ.get("VOICE_PROVIDER", "stub")


SUPPORTED_LANGS = {"en", "hi", "kn"}


def synthesize(text: str, language: str = "en") -> SynthResult:
    if not text or not text.strip():
        raise ValueError("text is empty")
    lang = language.lower() if language else "en"
    if lang not in SUPPORTED_LANGS:
        lang = "en"

    if tts_provider_name() == "live":
        return _live_synthesize(text, lang)
    return _stub_synthesize(text, lang)


# --- stub -----------------------------------------------------------------

def _stub_synthesize(text: str, lang: str) -> SynthResult:
    # Roughly 70ms per character ~ a normal speaking rate, cap at 30s.
    seconds = min(30.0, max(0.5, len(text) * 0.07))
    return SynthResult(
        audio=_silent_wav(seconds),
        media_type="audio/wav",
        provider="stub",
        voice=f"stub-{lang}",
    )


def _silent_wav(seconds: float, sample_rate: int = 16_000) -> bytes:
    """Generate a valid silent WAV (PCM 16-bit mono). Pure stdlib — no
    `wave`/`numpy` deps, no surprises."""
    n_samples = int(seconds * sample_rate)
    pcm = b"\x00\x00" * n_samples
    buf = io.BytesIO()
    # RIFF header
    buf.write(b"RIFF")
    buf.write(struct.pack("<I", 36 + len(pcm)))
    buf.write(b"WAVE")
    # fmt chunk
    buf.write(b"fmt ")
    buf.write(struct.pack("<IHHIIHH", 16, 1, 1, sample_rate, sample_rate * 2, 2, 16))
    # data chunk
    buf.write(b"data")
    buf.write(struct.pack("<I", len(pcm)))
    buf.write(pcm)
    return buf.getvalue()


# --- live -----------------------------------------------------------------

def _live_synthesize(text: str, lang: str) -> SynthResult:
    """Wire your real provider here. We leave the stub-WAV behavior intact
    rather than ship a misleading "live" path until the team picks a vendor."""
    raise RuntimeError(
        "VOICE_PROVIDER=live but no live TTS provider is wired yet. "
        "Implement _live_synthesize in services/voice/tts.py against Bhashini, "
        "IndicTTS, or another Indic-capable provider, then call it from here."
    )
