"""Generate a richer synthetic case corpus for demos / data visualisation.

Run:  python -m data.generate_demo_cases    (writes data/demo_cases.csv)

The output is deterministic (fixed RNG seed) so the dashboard, network graph
and recidivism screens look the same on every machine. It is shaped on purpose
to make each visualisation meaningful:

  * trends      — cases spread across ~18 months, denser in recent weeks
  * hotspots    — a recent cluster (May–Jun 2026) in a few localities
  * top-localities — locality volumes deliberately uneven
  * network     — recurring suspects who co-offend, forming small rings
  * recidivism  — repeat offenders with varied prior counts / crime mixes
  * PII redaction — phones / Aadhaar / PAN / email / vehicle-reg in narratives

NONE of this is real data. All names, numbers and IDs are fabricated.
"""

from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from pathlib import Path

OUT = Path(__file__).resolve().parent / "demo_cases.csv"
COLUMNS = [
    "case_id", "crime_type", "locality", "street_address", "occurred_on",
    "status", "mo_details", "victim_names", "suspect_names", "phone_numbers",
    "narrative",
]

rng = random.Random(42)

# --- vocab ----------------------------------------------------------------

LOCALITIES = [
    "HSR Layout", "Koramangala", "Whitefield", "Indiranagar", "Marathahalli",
    "Jayanagar", "BTM Layout", "JP Nagar", "Electronic City", "Rajajinagar",
    "Banashankari", "Yelahanka", "Malleshwaram", "Hebbal",
]
STREETS = [
    "27th Main", "100ft Road", "80ft Road", "ITPL Main Road", "4th Block",
    "1st Stage", "2nd Stage", "Sector 7", "5th Cross", "Outer Ring Road",
    "New Town", "Service Road", "Ring Road", "3rd Block",
]
VICTIM_NAMES = [
    "Ramesh Kumar", "Anita Sharma", "Suresh M", "Mohammed Ali", "Vikram Rao",
    "Lakshmi R", "Amit Verma", "Deepa Iyer", "Sridhar N", "Priya Nair",
    "Rahul Menon", "Sunita Devi", "Arjun Hegde", "Fatima Begum", "Kavya S",
    "Girish Patil", "Nandini Rao", "Thomas George", "Zoya Khan", "Harish B",
]
MO = {
    "theft": ["forced entry via balcony", "chain snatching near market",
              "shoplifting at supermarket", "pickpocketing at bus stand"],
    "burglary": ["broke shop shutter at 2am", "picked lock during daytime",
                 "entered via unlocked rear door"],
    "vehicle theft": ["bike stolen from parking", "car broken into at mall lot",
                      "scooter lifted from apartment basement"],
    "robbery": ["armed assault on cab driver", "mobile snatched at knifepoint",
                "ATM robbery attempt"],
    "assault": ["bar fight escalated", "road-rage altercation",
                "dispute over parking"],
    "cybercrime": ["UPI fraud via fake support call", "phishing link via SMS",
                   "OTP fraud impersonating bank"],
    "fraud": ["fake property listing", "investment scheme default",
              "fake job-offer advance fee"],
    "kidnapping": ["minor lured via social media", "ransom demand after abduction"],
}
STATUSES = ["open", "under_investigation", "chargesheeted", "closed"]
STATUS_WEIGHTS = [0.30, 0.40, 0.18, 0.12]


# --- PII helpers (fabricated) ---------------------------------------------

def _phone() -> str:
    return "+91 98" + "".join(str(rng.randint(0, 9)) for _ in range(8))


def _aadhaar() -> str:
    return " ".join("".join(str(rng.randint(0, 9)) for _ in range(4)) for _ in range(3))


def _pan() -> str:
    L = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    return ("".join(rng.choice(L) for _ in range(5))
            + "".join(str(rng.randint(0, 9)) for _ in range(4)) + rng.choice(L))


def _vehicle() -> str:
    L = "ABCDEFGHJKLMNPQRSTUVWXYZ"
    return f"KA-{rng.randint(1,53):02d}-{rng.choice(L)}{rng.choice(L)}-{rng.randint(1000,9999)}"


def _email(name: str) -> str:
    return name.lower().replace(" ", ".") + "@example.com"


def _narrative(crime: str, victim: str, phone: str | None) -> str:
    """Embed a couple of PII tokens so the redaction pipeline has work to do."""
    bits = []
    if crime == "vehicle theft":
        bits.append(f"Vehicle {_vehicle()} reported stolen.")
    if crime in ("cybercrime", "fraud"):
        bits.append(f"Victim transferred {rng.choice([15000,42000,80000,120000])} INR after contact on {_phone()}.")
    if crime in ("theft", "burglary", "robbery") and rng.random() < 0.6:
        bits.append(f"Aadhaar {_aadhaar()} recovered near the scene.")
    if rng.random() < 0.35:
        bits.append(f"PAN {_pan()} found on suspect.")
    if phone:
        bits.append(f"Complainant phone {phone} on file.")
    if rng.random() < 0.3:
        bits.append(f"Follow-up email sent to {_email(victim)}.")
    if not bits:
        bits.append("No identifying details recorded; witnesses being canvassed.")
    return " ".join(bits)


# --- structured cases: recurring offenders form small rings ---------------
# (subject names recur across cases → network edges + recidivism signal)

RINGS: list[dict] = [
    # property-crime ring centred on Ravi Kumar
    dict(crime="theft",         locality="HSR Layout",   suspects=["Ravi Kumar", "Manoj Setty"]),
    dict(crime="burglary",      locality="HSR Layout",   suspects=["Ravi Kumar", "Manoj Setty"]),
    dict(crime="burglary",      locality="Koramangala",  suspects=["Ravi Kumar", "Pradeep Kamath"]),
    dict(crime="theft",         locality="BTM Layout",   suspects=["Ravi Kumar"]),
    dict(crime="theft",         locality="Jayanagar",    suspects=["Manoj Setty"]),
    dict(crime="vehicle theft", locality="BTM Layout",   suspects=["Pradeep Kamath"]),
    dict(crime="theft",         locality="JP Nagar",     suspects=["Pradeep Kamath"]),
    # vehicle-theft ring: Imran Pasha + Salim Khan
    dict(crime="vehicle theft", locality="Koramangala",  suspects=["Imran Pasha", "Salim Khan"]),
    dict(crime="vehicle theft", locality="Marathahalli", suspects=["Imran Pasha", "Salim Khan"]),
    dict(crime="vehicle theft", locality="Whitefield",   suspects=["Imran Pasha"]),
    dict(crime="robbery",       locality="Marathahalli", suspects=["Salim Khan"]),
    # violent repeat offender: Bashir Khan
    dict(crime="robbery",       locality="Whitefield",   suspects=["Bashir Khan"]),
    dict(crime="assault",       locality="Indiranagar",  suspects=["Bashir Khan"]),
    dict(crime="kidnapping",    locality="Banashankari", suspects=["Bashir Khan"]),
    # cyber / fraud cell: Naveen Reddy + Kiran Gowda
    dict(crime="cybercrime",    locality="Electronic City", suspects=["Naveen Reddy", "Kiran Gowda"]),
    dict(crime="fraud",         locality="Electronic City", suspects=["Naveen Reddy", "Kiran Gowda"]),
    dict(crime="cybercrime",    locality="JP Nagar",        suspects=["Naveen Reddy"]),
    dict(crime="cybercrime",    locality="HSR Layout",      suspects=["Kiran Gowda"]),
]

# locality weights for the random "filler" cases (uneven on purpose)
FILLER_WEIGHTS = [9, 8, 7, 5, 5, 5, 4, 4, 4, 3, 3, 2, 2, 2]
FILLER_TYPES = ["theft", "burglary", "vehicle theft", "robbery", "assault",
                "cybercrime", "fraud"]
FILLER_TYPE_WEIGHTS = [9, 6, 6, 3, 3, 5, 4]


def _date_recent_biased() -> date:
    """Random date in [2025-01-01, 2026-06-22], biased toward recent months."""
    span_days = (date(2026, 6, 22) - date(2025, 1, 1)).days
    # square the uniform draw so larger offsets (recent) are favoured
    frac = rng.random() ** 0.55
    return date(2025, 1, 1) + timedelta(days=int(frac * span_days))


def build_rows() -> list[dict]:
    rows: list[dict] = []
    seq = {2025: 1000, 2026: 1000}

    def next_id(d: date) -> str:
        seq[d.year] += 1
        return f"FIR-{d.year}-{seq[d.year]:04d}"

    # 1) structured ring cases (spread across the whole window)
    for spec in RINGS:
        d = _date_recent_biased()
        crime = spec["crime"]
        victim = rng.choice(VICTIM_NAMES)
        phone = _phone() if rng.random() < 0.7 else ""
        rows.append({
            "case_id": next_id(d),
            "crime_type": crime,
            "locality": spec["locality"],
            "street_address": rng.choice(STREETS),
            "occurred_on": d.isoformat(),
            "status": rng.choices(STATUSES, STATUS_WEIGHTS)[0],
            "mo_details": rng.choice(MO[crime]),
            "victim_names": victim,
            "suspect_names": "|".join(spec["suspects"]),
            "phone_numbers": phone,
            "narrative": _narrative(crime, victim, phone or None),
        })

    # 2) a recent cluster so hotspots clearly light up (late May–Jun 2026)
    recent_locs = ["HSR Layout", "Koramangala", "Whitefield", "Marathahalli"]
    for _ in range(12):
        d = date(2026, 5, 24) + timedelta(days=rng.randint(0, 29))
        crime = rng.choices(FILLER_TYPES, FILLER_TYPE_WEIGHTS)[0]
        loc = rng.choice(recent_locs)
        victim = rng.choice(VICTIM_NAMES)
        phone = _phone() if rng.random() < 0.6 else ""
        rows.append({
            "case_id": next_id(d),
            "crime_type": crime,
            "locality": loc,
            "street_address": rng.choice(STREETS),
            "occurred_on": d.isoformat(),
            "status": rng.choices(STATUSES, STATUS_WEIGHTS)[0],
            "mo_details": rng.choice(MO[crime]),
            "victim_names": victim,
            "suspect_names": rng.choice(["unknown", "unknown", "REDACTED", rng.choice(VICTIM_NAMES)]),
            "phone_numbers": phone,
            "narrative": _narrative(crime, victim, phone or None),
        })

    # 3) filler cases for overall volume / trend shape
    for _ in range(35):
        d = _date_recent_biased()
        crime = rng.choices(FILLER_TYPES, FILLER_TYPE_WEIGHTS)[0]
        loc = rng.choices(LOCALITIES, FILLER_WEIGHTS)[0]
        victim = rng.choice(VICTIM_NAMES)
        phone = _phone() if rng.random() < 0.5 else ""
        rows.append({
            "case_id": next_id(d),
            "crime_type": crime,
            "locality": loc,
            "street_address": rng.choice(STREETS),
            "occurred_on": d.isoformat(),
            "status": rng.choices(STATUSES, STATUS_WEIGHTS)[0],
            "mo_details": rng.choice(MO[crime]),
            "victim_names": victim,
            "suspect_names": rng.choice(["unknown", "unknown", "unknown", "REDACTED"]),
            "phone_numbers": phone,
            "narrative": _narrative(crime, victim, phone or None),
        })

    rows.sort(key=lambda r: r["occurred_on"])
    return rows


def main() -> None:
    rows = build_rows()
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows)} cases -> {OUT}")


if __name__ == "__main__":
    main()
