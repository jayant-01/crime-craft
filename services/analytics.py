"""Analytics — aggregate statistics over the case corpus.

All outputs are aggregate-only (counts, distributions) so they're safe for the
public role. No case-level fields ever cross this boundary.

For the 1100-case corpus we scan the entire table in-process. When that stops
being fast enough, the Catalyst path can be swapped for ZCQL aggregations.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, timedelta
from typing import Iterable

from models import (
    Case,
    Hotspot,
    HotspotsResponse,
    LocalityCount,
    TopLocalitiesResponse,
    TrendBucket,
    TrendsResponse,
)
from services.datastore import case_repo


# --- helpers --------------------------------------------------------------

def _all_cases() -> list[Case]:
    return list(case_repo().list(limit=100_000))


def _week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _month_start(d: date) -> date:
    return d.replace(day=1)


def _bucket_fn(granularity: str):
    if granularity == "month":
        return _month_start
    return _week_start  # default: week


def _filter(
    cases: Iterable[Case],
    *,
    from_date: date | None = None,
    to_date: date | None = None,
    crime_type: str | None = None,
    locality: str | None = None,
) -> list[Case]:
    out = []
    for c in cases:
        if from_date and c.occurred_on < from_date:
            continue
        if to_date and c.occurred_on > to_date:
            continue
        if crime_type and c.crime_type.lower() != crime_type.lower():
            continue
        if locality and c.locality.lower() != locality.lower():
            continue
        out.append(c)
    return out


# --- public API -----------------------------------------------------------

def crime_trends(
    *,
    granularity: str = "week",
    from_date: date | None = None,
    to_date: date | None = None,
    crime_type: str | None = None,
    locality: str | None = None,
) -> TrendsResponse:
    if granularity not in ("week", "month"):
        raise ValueError("granularity must be 'week' or 'month'")
    cases = _filter(
        _all_cases(),
        from_date=from_date,
        to_date=to_date,
        crime_type=crime_type,
        locality=locality,
    )
    bucketize = _bucket_fn(granularity)
    by_bucket: dict[date, list[Case]] = defaultdict(list)
    for c in cases:
        by_bucket[bucketize(c.occurred_on)].append(c)

    buckets = [
        TrendBucket(
            bucket_start=start,
            count=len(group),
            by_crime_type=dict(Counter(c.crime_type for c in group)),
        )
        for start, group in sorted(by_bucket.items())
    ]
    return TrendsResponse(
        granularity=granularity,
        from_date=from_date,
        to_date=to_date,
        buckets=buckets,
        total=len(cases),
    )


def top_localities(limit: int = 10) -> TopLocalitiesResponse:
    cases = _all_cases()
    by_loc: dict[str, list[Case]] = defaultdict(list)
    for c in cases:
        by_loc[c.locality].append(c)

    ranked = sorted(by_loc.items(), key=lambda kv: len(kv[1]), reverse=True)[:limit]
    items = [
        LocalityCount(
            locality=loc,
            count=len(group),
            top_crime_types=[t for t, _ in Counter(c.crime_type for c in group).most_common(3)],
        )
        for loc, group in ranked
    ]
    return TopLocalitiesResponse(limit=limit, localities=items, total_cases=len(cases))


def hotspots(limit: int = 10, window_days: int = 30, as_of: date | None = None) -> HotspotsResponse:
    """Top localities by total case count, with a recent-window count so
    callers can spot rising activity. as_of defaults to the max occurred_on
    in the corpus (so the "recent" window means something on stale data)."""
    cases = _all_cases()
    if not cases:
        return HotspotsResponse(limit=limit, window_days=window_days, hotspots=[])

    if as_of is None:
        as_of = max(c.occurred_on for c in cases)
    window_start = as_of - timedelta(days=window_days)

    by_loc: dict[str, list[Case]] = defaultdict(list)
    for c in cases:
        by_loc[c.locality].append(c)

    out: list[Hotspot] = []
    for loc, group in by_loc.items():
        types = Counter(c.crime_type for c in group)
        top_type, _ = types.most_common(1)[0] if types else (None, 0)
        recent = sum(1 for c in group if c.occurred_on >= window_start)
        out.append(Hotspot(locality=loc, count=len(group), crime_type=top_type, recent_count=recent))

    out.sort(key=lambda h: (h.recent_count, h.count), reverse=True)
    return HotspotsResponse(limit=limit, window_days=window_days, hotspots=out[:limit])
