"""Crime Map + Person Dossier aggregations (officer-facing)."""

from __future__ import annotations

from models import DossierCase, MapPoint, MapResponse, PersonDossier
from services.datastore import case_repo
from services.geo import coords_for_case

_ANON = {"unknown", "redacted", ""}


def build_map(limit: int = 5000) -> MapResponse:
    """Every case as a geo point (officer view — locations are SENSITIVE)."""
    points: list[MapPoint] = []
    for c in case_repo().list(limit=limit):
        lat, lng = coords_for_case(c)
        points.append(
            MapPoint(
                case_id=c.case_id, crime_type=c.crime_type, locality=c.locality,
                status=c.status, occurred_on=c.occurred_on, lat=lat, lng=lng,
            )
        )
    return MapResponse(points=points, total=len(points))


def build_dossier(name: str) -> PersonDossier | None:
    """Aggregate everything known about one suspect across the corpus."""
    needle = name.strip().lower()
    if needle in _ANON:
        return None
    all_cases = case_repo().list(limit=100_000)
    mine = [c for c in all_cases if needle in [s.strip().lower() for s in c.suspect_names]]
    if not mine:
        return None

    dates = [c.occurred_on for c in mine]
    co_accused = sorted({
        s for c in mine for s in c.suspect_names
        if s.strip().lower() != needle and s.strip().lower() not in _ANON
    })

    band = score = None
    try:
        from services.predictive import score_subject

        r = score_subject(name)
        band, score = r.band.value, r.score
    except Exception:  # noqa: BLE001 — recidivism is best-effort in the dossier
        pass

    cases = [
        DossierCase(case_id=c.case_id, crime_type=c.crime_type, locality=c.locality,
                    occurred_on=c.occurred_on, status=c.status)
        for c in sorted(mine, key=lambda c: c.occurred_on, reverse=True)
    ]
    return PersonDossier(
        name=name,
        case_count=len(mine),
        localities=sorted({c.locality for c in mine}),
        crime_types=sorted({c.crime_type for c in mine}),
        co_accused=co_accused,
        first_seen=min(dates),
        last_seen=max(dates),
        recidivism_band=band,
        recidivism_score=score,
        cases=cases,
    )
