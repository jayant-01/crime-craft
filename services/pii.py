"""PII detection and redaction.

This module is the *only* place that knows what PII looks like. Every ingest
path must run through `redact_text` before persisting free-text fields, and
every structured PII column (victim_names, phone_numbers, ...) must be
classified before storage so the role-based redactor can find it later.

Patterns target Indian formats first. False positives are fine here —
over-redacting is the safe failure mode. False negatives are not.

Coverage today:
  - Phone numbers (Indian, 10-digit with optional +91 / 0 prefix)
  - Aadhaar (XXXX XXXX XXXX or 12 contiguous digits)
  - PAN (5 letters + 4 digits + 1 letter)
  - Email addresses
  - Vehicle registration (KA-01-AB-1234 and variants)
  - Names (regex-based — honorific + capitalized pair, with stopword filter).
    The spaCy / IndicNER hook (`detect_names_with_ner`) is available as an
    opt-in upgrade when a model is loaded.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


# --- patterns -------------------------------------------------------------

PHONE_RE = re.compile(r"(?<!\d)(?:\+91[\-\s]?|0)?[6-9]\d{9}(?!\d)")
AADHAAR_RE = re.compile(r"(?<!\d)\d{4}[\s\-]?\d{4}[\s\-]?\d{4}(?!\d)")
PAN_RE = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")
EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")
VEHICLE_RE = re.compile(r"\b[A-Z]{2}[\s\-]?\d{1,2}[\s\-]?[A-Z]{1,3}[\s\-]?\d{1,4}\b")

# Honorific + 1–3 capitalized tokens. Honorifics from English + common Indian use.
HONORIFIC_NAME_RE = re.compile(
    r"\b(?:Mr|Mrs|Ms|Miss|Dr|Shri|Smt|Sri|Sgt|Insp|Capt|Col|SI|ASI|DCP|ACP|Prof)\.?\s+"
    r"([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){0,2})"
)

# Standalone Title-Case sequences of 2-3 words. Higher false-positive rate —
# guarded by a stopword list so we don't redact "Karnataka State Police".
NAME_PAIR_RE = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})\b")

# Tokens that look like names but aren't. Add liberally; over-keeping is fine,
# under-keeping causes false redactions.
NAME_STOPWORDS: set[str] = {
    # Geography
    "karnataka", "india", "bangalore", "bengaluru", "mumbai", "delhi", "chennai",
    "kolkata", "hyderabad", "pune", "jaipur", "ahmedabad", "lucknow", "kanpur",
    "nagpur", "indore", "thane", "bhopal", "patna", "vadodara", "ghaziabad",
    "ludhiana", "agra", "nashik", "ranchi", "coimbatore", "kochi", "mysore",
    "mysuru", "hubli", "dharwad", "mangalore", "mangaluru", "belgaum", "udupi",
    "asia", "europe", "africa", "america",
    # Localities (Bengaluru-heavy since that's the KSP corpus)
    "hsr", "layout", "indiranagar", "koramangala", "whitefield", "jayanagar",
    "btm", "yelahanka", "banashankari", "rajajinagar", "majestic", "marathahalli",
    "electronic", "city", "stage", "block", "sector", "main", "road", "street",
    "cross", "phase",
    # Common in case narratives
    "police", "station", "court", "officer", "victim", "suspect", "witness",
    "case", "fir", "complaint", "investigation", "chargesheet", "evidence",
    "cctv", "report", "arrested", "detained", "registered", "recovered",
    "unknown", "redacted",
    # Time
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
    "january", "february", "march", "april", "may", "june", "july", "august",
    "september", "october", "november", "december",
    # Generic capitalized
    "the", "a", "an", "and", "or", "but", "is", "was", "were", "are",
    "state", "central", "national", "supreme", "high",
}


@dataclass(frozen=True)
class Finding:
    kind: str           # "phone" | "aadhaar" | "pan" | "email" | "vehicle" | "name"
    value: str
    start: int
    end: int


# --- detection ------------------------------------------------------------

def detect(text: str) -> list[Finding]:
    """Return every PII match in `text`, in order of appearance."""
    if not text:
        return []
    findings: list[Finding] = []
    for kind, pattern in (
        ("aadhaar", AADHAAR_RE),  # check Aadhaar before phone (12-digit vs 10-digit overlap)
        ("phone", PHONE_RE),
        ("pan", PAN_RE),
        ("email", EMAIL_RE),
        ("vehicle", VEHICLE_RE),
    ):
        for m in pattern.finditer(text):
            findings.append(Finding(kind=kind, value=m.group(0), start=m.start(), end=m.end()))
    findings.extend(detect_names(text))
    findings.sort(key=lambda f: f.start)
    return _dedupe_overlaps(findings)


def detect_names(text: str) -> list[Finding]:
    """Regex-based name detector. Two strategies:
      1. Honorific + capitalized words → high precision.
      2. Capitalized pairs/triples → broader recall, filtered against a stopword list.

    For Indian languages and ambiguous names, the production pipeline should
    swap in an NER model via `detect_names_with_ner` once one is loaded.
    """
    findings: list[Finding] = []
    if not text:
        return findings

    # Strategy 1: honorific-led names. We match the full honorific span so it
    # gets redacted along with the name (otherwise "Mr [REDACTED-NAME]" would
    # still leak the honorific, which is fine but inconsistent).
    for m in HONORIFIC_NAME_RE.finditer(text):
        findings.append(Finding(kind="name", value=m.group(0), start=m.start(), end=m.end()))

    # Strategy 2: standalone Title-Case bigrams/trigrams. Skip anything that
    # collides with an existing finding or hits the stopword list.
    occupied = [(f.start, f.end) for f in findings]
    for m in NAME_PAIR_RE.finditer(text):
        s, e = m.start(), m.end()
        if any(s < oe and e > os for os, oe in occupied):
            continue
        tokens = m.group(1).split()
        if any(tok.lower() in NAME_STOPWORDS for tok in tokens):
            continue
        # Skip if every token is < 3 chars (initials, abbreviations).
        if all(len(tok) < 3 for tok in tokens):
            continue
        findings.append(Finding(kind="name", value=m.group(1), start=s, end=e))

    return findings


def detect_names_with_ner(text: str) -> list[Finding]:  # pragma: no cover — opt-in hook
    """Optional upgrade path: spaCy / IndicNER. Load a model and replace this
    body. The interface is identical to `detect_names` so it slots in cleanly.

    Example with spaCy:
        nlp = spacy.load("en_core_web_lg")
        return [
            Finding(kind="name", value=ent.text, start=ent.start_char, end=ent.end_char)
            for ent in nlp(text).ents if ent.label_ == "PERSON"
        ]
    """
    return []


def _dedupe_overlaps(findings: list[Finding]) -> list[Finding]:
    if not findings:
        return findings
    kept: list[Finding] = [findings[0]]
    for f in findings[1:]:
        last = kept[-1]
        if f.start < last.end:
            if (f.end - f.start) > (last.end - last.start):
                kept[-1] = f
            continue
        kept.append(f)
    return kept


# --- redaction ------------------------------------------------------------

_PLACEHOLDER = {
    "phone": "[REDACTED-PHONE]",
    "aadhaar": "[REDACTED-AADHAAR]",
    "pan": "[REDACTED-PAN]",
    "email": "[REDACTED-EMAIL]",
    "vehicle": "[REDACTED-VEHICLE]",
    "name": "[REDACTED-NAME]",
}


def redact_text(text: str | None) -> tuple[str | None, list[Finding]]:
    """Return (redacted_text, findings). Idempotent."""
    if not text:
        return text, []
    findings = detect(text)
    if not findings:
        return text, []

    parts: list[str] = []
    cursor = 0
    for f in findings:
        parts.append(text[cursor : f.start])
        parts.append(_PLACEHOLDER[f.kind])
        cursor = f.end
    parts.append(text[cursor:])
    return "".join(parts), findings


def mask_phone(phone: str) -> str:
    digits = re.sub(r"\D", "", phone)
    if len(digits) < 4:
        return "****"
    return "*" * (len(digits) - 4) + digits[-4:]
