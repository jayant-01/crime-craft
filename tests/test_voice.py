"""Voice tests. We test the stub end-to-end — the live paths are wired but
not exercised here (they require model downloads / vendor accounts)."""

from __future__ import annotations

import pytest

from services.voice import synthesize, transcribe, stt_provider_name, tts_provider_name


class TestStt:
    def test_default_provider_is_stub(self):
        assert stt_provider_name() == "stub"

    def test_rejects_empty_audio(self):
        with pytest.raises(ValueError):
            transcribe(b"")

    def test_stub_returns_placeholder_text(self):
        result = transcribe(b"\x00" * 32_000)
        assert result.provider == "stub"
        assert result.language == "en"
        assert result.duration_seconds >= 1.0
        assert "stub transcription" in result.text


class TestTts:
    def test_default_provider_is_stub(self):
        assert tts_provider_name() == "stub"

    def test_rejects_empty_text(self):
        with pytest.raises(ValueError):
            synthesize("")

    def test_returns_well_formed_wav(self):
        result = synthesize("hello", language="en")
        assert result.media_type == "audio/wav"
        assert result.audio.startswith(b"RIFF")
        assert b"WAVE" in result.audio[:12]
        # Duration scales with text length.
        long_result = synthesize("hello " * 100, language="en")
        assert len(long_result.audio) > len(result.audio)

    def test_falls_back_to_english_for_unknown_language(self):
        result = synthesize("hello", language="zz")
        assert "en" in result.voice

    def test_supports_hindi_and_kannada_voices(self):
        for lang in ("hi", "kn"):
            result = synthesize("नमस्ते" if lang == "hi" else "ನಮಸ್ಕಾರ", language=lang)
            assert lang in result.voice
