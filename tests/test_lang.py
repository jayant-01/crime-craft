"""Language detection tests. Script-based detection is deterministic — these
tests are the spec."""

from __future__ import annotations

from services.lang import Language, detect


class TestDetect:
    def test_english(self):
        assert detect("any thefts in HSR Layout?") == Language.EN

    def test_hindi_devanagari(self):
        assert detect("एचएसआर लेआउट में चोरी") == Language.HI

    def test_kannada(self):
        assert detect("ಎಚ್ಎಸ್ಆರ್ ಲೇಔಟ್ ಕಳ್ಳತನ") == Language.KN

    def test_mixed_hindi_english_picks_hindi(self):
        # Native script wins even with English brand names mixed in.
        assert detect("HSR Layout में चोरी की रिपोर्ट") == Language.HI

    def test_empty_defaults_to_english(self):
        assert detect("") == Language.EN

    def test_digits_only_defaults_to_english(self):
        assert detect("12345 67890") == Language.EN

    def test_kannada_wins_over_hindi_when_more_kannada_chars(self):
        # Edge case — should not be confused if both scripts appear.
        text = "ಕ" * 10 + "क" * 2
        assert detect(text) == Language.KN
