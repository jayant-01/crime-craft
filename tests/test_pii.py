"""PII redaction is the highest-risk path in this codebase. A false negative
here can leak victim data to the public-facing view. Tests are aggressive on
purpose — over-redacting is fine, under-redacting is a P0.
"""

from __future__ import annotations

from services.pii import detect, detect_names, redact_text, mask_phone


# --- detection ------------------------------------------------------------

class TestDetectPhone:
    def test_indian_phone_with_country_code(self):
        findings = detect("call me at +91 9845012345 today")
        kinds = [f.kind for f in findings]
        assert "phone" in kinds

    def test_indian_phone_bare_10_digits(self):
        findings = detect("number is 9845012345")
        assert any(f.kind == "phone" for f in findings)

    def test_phone_with_zero_prefix(self):
        findings = detect("dial 09845012345 immediately")
        assert any(f.kind == "phone" for f in findings)

    def test_phone_not_detected_in_random_digits(self):
        # 9-digit number — too short for Indian mobile
        assert detect("ref id 123456789") == []


class TestDetectAadhaar:
    def test_aadhaar_with_spaces(self):
        assert any(f.kind == "aadhaar" for f in detect("Aadhaar 1234 5678 9012"))

    def test_aadhaar_with_dashes(self):
        assert any(f.kind == "aadhaar" for f in detect("aadhaar 1234-5678-9012"))

    def test_aadhaar_contiguous(self):
        assert any(f.kind == "aadhaar" for f in detect("123456789012 is the number"))

    def test_aadhaar_wins_over_phone_for_12_digit_span(self):
        # 12 contiguous digits should be classified as Aadhaar, not chunked into phone.
        findings = detect("number 123456789012")
        kinds = [f.kind for f in findings]
        assert "aadhaar" in kinds
        # Should not also produce a phone finding inside the same span.
        assert kinds.count("phone") == 0


class TestDetectPan:
    def test_pan_standard(self):
        assert any(f.kind == "pan" for f in detect("PAN ABCDE1234F was used"))

    def test_pan_only_uppercase(self):
        # Real PAN is always uppercase; lowercase shouldn't match.
        assert detect("abcde1234f") == []


class TestDetectEmail:
    def test_email_basic(self):
        assert any(f.kind == "email" for f in detect("contact alice@example.com please"))


class TestDetectVehicle:
    def test_vehicle_with_dashes(self):
        assert any(f.kind == "vehicle" for f in detect("KA-01-AB-1234 reported stolen"))

    def test_vehicle_with_spaces(self):
        assert any(f.kind == "vehicle" for f in detect("KA 01 AB 1234 reported stolen"))


# --- redaction ------------------------------------------------------------

class TestRedactText:
    def test_none_passthrough(self):
        text, findings = redact_text(None)
        assert text is None and findings == []

    def test_empty_passthrough(self):
        text, findings = redact_text("")
        assert text == "" and findings == []

    def test_no_pii_returns_input(self):
        original = "Resident reported jewellery missing."
        text, findings = redact_text(original)
        assert text == original and findings == []

    def test_phone_redacted(self):
        text, _ = redact_text("Victim phone +91 9845012345 on file.")
        assert "9845012345" not in text
        assert "[REDACTED-PHONE]" in text

    def test_aadhaar_redacted(self):
        text, _ = redact_text("Aadhaar 1234 5678 9012 found at scene.")
        assert "1234" not in text or "5678" not in text  # span gone
        assert "[REDACTED-AADHAAR]" in text

    def test_multiple_kinds_in_one_string(self):
        original = "Call 9845012345 or email john@example.com about PAN ABCDE1234F."
        text, findings = redact_text(original)
        kinds = {f.kind for f in findings}
        assert {"phone", "email", "pan"} <= kinds
        for raw in ["9845012345", "john@example.com", "ABCDE1234F"]:
            assert raw not in text

    def test_idempotent(self):
        original = "Number 9845012345."
        once, _ = redact_text(original)
        twice, _ = redact_text(once)
        assert once == twice

    def test_preserves_surrounding_text(self):
        text, _ = redact_text("before 9845012345 after")
        assert text.startswith("before ")
        assert text.endswith(" after")


# --- masking helper -------------------------------------------------------

class TestDetectNames:
    def test_honorific_plus_name(self):
        findings = detect_names("Suspect was identified as Mr Ramesh Kumar.")
        assert any(f.kind == "name" and "Ramesh" in f.value for f in findings)

    def test_indian_honorifics(self):
        for honorific in ["Shri", "Smt", "Sri", "Insp", "Sgt"]:
            findings = detect_names(f"{honorific} Anil Sharma arrived.")
            assert any(f.kind == "name" for f in findings), f"missed {honorific}"

    def test_capitalized_pair(self):
        findings = detect_names("The victim Vikram Rao filed a complaint.")
        names = [f.value for f in findings if f.kind == "name"]
        assert any("Vikram" in n for n in names)

    def test_stopword_locations_not_redacted(self):
        findings = detect_names("The incident occurred in HSR Layout in Karnataka State.")
        names = [f.value for f in findings if f.kind == "name"]
        assert names == [], f"false-positive on locations: {names}"

    def test_stopword_orgs_not_redacted(self):
        findings = detect_names("Karnataka State Police is investigating.")
        names = [f.value for f in findings if f.kind == "name"]
        assert names == [], f"false-positive on org: {names}"

    def test_redact_removes_honorific_name(self):
        text, _ = redact_text("Mr Ramesh Kumar was charged.")
        assert "Ramesh" not in text
        assert "Kumar" not in text
        assert "[REDACTED-NAME]" in text

    def test_redact_preserves_non_names(self):
        text, _ = redact_text("Incident at HSR Layout reported by Karnataka Police.")
        # Geography + orgs should survive — only names redacted.
        assert "HSR Layout" in text
        assert "Karnataka" in text


class TestMaskPhone:
    def test_keeps_last_four(self):
        assert mask_phone("9845012345").endswith("2345")
        assert "9845" not in mask_phone("9845012345")[:-4]

    def test_strips_non_digits(self):
        assert mask_phone("+91-9845-012345") == mask_phone("919845012345")

    def test_short_input(self):
        assert mask_phone("12") == "****"
