"""Language detection.

For our three target languages we don't need a model — they use different
Unicode scripts. A simple script-frequency vote is fast, deterministic, and
needs no extra dependency:

  English  → Basic Latin (a–z, A–Z)
  Hindi    → Devanagari (U+0900–U+097F)
  Kannada  → Kannada    (U+0C80–U+0CFF)

For ambiguous queries (e.g. transliterated Hindi in Latin script like
"chori in HSR Layout") we fall back to English. The LLM is multilingual
enough to handle transliteration regardless.
"""

from __future__ import annotations

from enum import Enum


class Language(str, Enum):
    EN = "en"
    HI = "hi"
    KN = "kn"


def detect(text: str) -> Language:
    if not text:
        return Language.EN

    devanagari = 0
    kannada = 0
    latin = 0
    for ch in text:
        cp = ord(ch)
        if 0x0900 <= cp <= 0x097F:
            devanagari += 1
        elif 0x0C80 <= cp <= 0x0CFF:
            kannada += 1
        elif (0x41 <= cp <= 0x5A) or (0x61 <= cp <= 0x7A):
            latin += 1

    # Indian-script characters beat Latin even when fewer — a Hindi sentence
    # with a few English brand names mixed in is still Hindi.
    if kannada > 0 and kannada >= devanagari:
        return Language.KN
    if devanagari > 0:
        return Language.HI
    if latin > 0:
        return Language.EN
    return Language.EN


def language_name(lang: Language) -> str:
    return {Language.EN: "English", Language.HI: "Hindi", Language.KN: "Kannada"}[lang]
