from datetime import date
from pydantic import BaseModel


class TrendBucket(BaseModel):
    bucket_start: date          # ISO-week or month start, depending on granularity
    count: int
    by_crime_type: dict[str, int]


class TrendsResponse(BaseModel):
    granularity: str            # "week" | "month"
    from_date: date | None
    to_date: date | None
    buckets: list[TrendBucket]
    total: int


class LocalityCount(BaseModel):
    locality: str
    count: int
    top_crime_types: list[str]  # up to 3, descending by count


class TopLocalitiesResponse(BaseModel):
    limit: int
    localities: list[LocalityCount]
    total_cases: int


class Hotspot(BaseModel):
    locality: str
    count: int
    crime_type: str | None      # most frequent type in this locality
    recent_count: int           # count in the last 30 days


class HotspotsResponse(BaseModel):
    limit: int
    window_days: int
    hotspots: list[Hotspot]
