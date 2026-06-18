"""Analytics tests. Focus is the math, not the API surface — the route is a
thin wrapper around these functions."""

from __future__ import annotations

from datetime import date

import pytest

from models import Case, CaseStatus
from services import datastore
from services.analytics import crime_trends, hotspots, top_localities


@pytest.fixture(autouse=True)
def fresh_repo():
    datastore.reset_for_tests()
    yield
    datastore.reset_for_tests()


def _seed():
    rows = [
        ("FIR-1", "theft",        "HSR Layout",   date(2025, 11, 3)),
        ("FIR-2", "theft",        "HSR Layout",   date(2025, 11, 10)),
        ("FIR-3", "burglary",     "Indiranagar",  date(2025, 11, 10)),
        ("FIR-4", "burglary",     "HSR Layout",   date(2025, 12, 1)),
        ("FIR-5", "vehicle theft","Koramangala",  date(2025, 12, 1)),
        ("FIR-6", "theft",        "Koramangala",  date(2025, 12, 8)),
    ]
    for case_id, ctype, loc, dt in rows:
        datastore.case_repo().upsert(
            Case(
                case_id=case_id,
                crime_type=ctype,
                locality=loc,
                occurred_on=dt,
                status=CaseStatus.OPEN,
            )
        )


class TestTopLocalities:
    def test_orders_by_case_count_descending(self):
        _seed()
        resp = top_localities(limit=10)
        names = [l.locality for l in resp.localities]
        assert names[0] == "HSR Layout"  # 3 cases
        assert resp.total_cases == 6

    def test_top_crime_types_present(self):
        _seed()
        resp = top_localities()
        hsr = next(l for l in resp.localities if l.locality == "HSR Layout")
        assert "theft" in hsr.top_crime_types

    def test_limit_caps_result(self):
        _seed()
        resp = top_localities(limit=2)
        assert len(resp.localities) == 2


class TestCrimeTrends:
    def test_weekly_buckets_align_to_monday(self):
        _seed()
        resp = crime_trends(granularity="week")
        for b in resp.buckets:
            assert b.bucket_start.weekday() == 0  # Monday

    def test_monthly_buckets_align_to_first(self):
        _seed()
        resp = crime_trends(granularity="month")
        for b in resp.buckets:
            assert b.bucket_start.day == 1

    def test_filter_by_crime_type(self):
        _seed()
        resp = crime_trends(crime_type="theft")
        assert resp.total == 3
        for b in resp.buckets:
            assert b.by_crime_type.get("theft", 0) == b.count

    def test_filter_by_locality(self):
        _seed()
        resp = crime_trends(locality="HSR Layout")
        assert resp.total == 3

    def test_filter_by_date_range(self):
        _seed()
        resp = crime_trends(from_date=date(2025, 12, 1))
        assert resp.total == 3

    def test_invalid_granularity_raises(self):
        with pytest.raises(ValueError):
            crime_trends(granularity="day")


class TestHotspots:
    def test_orders_by_recent_then_total(self):
        _seed()
        resp = hotspots(limit=10, window_days=30, as_of=date(2025, 12, 8))
        # All cases are within the 30-day window of 2025-12-08, so the order
        # falls back to total count → HSR Layout (3) leads.
        assert resp.hotspots[0].locality == "HSR Layout"

    def test_recent_window_filters_count(self):
        _seed()
        # Only Dec cases fall in the 14-day window of 2025-12-08.
        resp = hotspots(window_days=14, as_of=date(2025, 12, 8))
        koramangala = next(h for h in resp.hotspots if h.locality == "Koramangala")
        assert koramangala.recent_count == 2
        hsr = next(h for h in resp.hotspots if h.locality == "HSR Layout")
        assert hsr.recent_count == 1  # only FIR-4 (Dec 1) falls in the window

    def test_empty_corpus_returns_empty(self):
        resp = hotspots()
        assert resp.hotspots == []
