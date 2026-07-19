"""Geo helpers for the crime map.

The demo corpus stores localities as names; real KSP data carries lat/long on
CaseMaster. Until that's wired, we place each case at its locality centroid with
a small deterministic jitter (so cases in the same area spread out instead of
stacking on one pin). When a Case has real latitude/longitude, we use those.
"""

from __future__ import annotations

import hashlib

from models import Case

# Approximate centroids for Bengaluru localities used in the demo corpus.
LOCALITY_COORDS: dict[str, tuple[float, float]] = {
    "hsr layout": (12.9116, 77.6389),
    "koramangala": (12.9352, 77.6245),
    "whitefield": (12.9698, 77.7500),
    "indiranagar": (12.9719, 77.6412),
    "marathahalli": (12.9569, 77.7011),
    "jayanagar": (12.9250, 77.5938),
    "btm layout": (12.9166, 77.6101),
    "jp nagar": (12.9063, 77.5857),
    "electronic city": (12.8452, 77.6602),
    "rajajinagar": (12.9910, 77.5520),
    "banashankari": (12.9255, 77.5468),
    "yelahanka": (13.1007, 77.5963),
    "malleshwaram": (13.0035, 77.5647),
    "hebbal": (13.0358, 77.5970),
}
_CITY_CENTER = (12.9716, 77.5946)  # fallback (Bengaluru)


def _jitter(seed: str) -> tuple[float, float]:
    """Deterministic ±~0.008° (~0.8 km) offset from a stable hash of the case id."""
    h = hashlib.md5(seed.encode()).digest()
    dlat = (h[0] / 255 - 0.5) * 0.016
    dlng = (h[1] / 255 - 0.5) * 0.016
    return dlat, dlng


def coords_for_case(case: Case) -> tuple[float, float]:
    if case.latitude is not None and case.longitude is not None:
        return case.latitude, case.longitude
    base = LOCALITY_COORDS.get((case.locality or "").strip().lower(), _CITY_CENTER)
    dlat, dlng = _jitter(case.case_id)
    return round(base[0] + dlat, 6), round(base[1] + dlng, 6)
