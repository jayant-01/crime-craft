import { useEffect, useState } from "react";
import { analyticsApi } from "../api/endpoints";
import type { HotspotsResponse, TopLocalitiesResponse, TrendsResponse } from "../api/types";

export default function DashboardPage() {
  const [trends, setTrends] = useState<TrendsResponse | null>(null);
  const [locs, setLocs] = useState<TopLocalitiesResponse | null>(null);
  const [hots, setHots] = useState<HotspotsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      analyticsApi.trends({ granularity: "week" }),
      analyticsApi.topLocalities(10),
      analyticsApi.hotspots(10, 30),
    ])
      .then(([t, l, h]) => { setTrends(t); setLocs(l); setHots(h); })
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <p className="text-rose-600">{error}</p>;

  const recent = hots?.hotspots.reduce((s, h) => s + h.recent_count, 0);
  const peakWeek = trends ? Math.max(0, ...trends.buckets.map((b) => b.count)) : undefined;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Stat label="Total cases" value={locs?.total_cases} />
        <Stat label={`Recent (${hots?.window_days ?? 30}d)`} value={recent} accent="saffron" />
        <Stat label="Localities" value={locs?.localities.length} />
        <Stat label="Peak week" value={peakWeek} accent="green" />
      </div>

      <div className="card card-pad">
        <CardTitle>Crime trend — weekly</CardTitle>
        {trends ? <TrendChart data={trends} /> : <ChartSkeleton />}
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <div className="card card-pad">
          <CardTitle>Top localities</CardTitle>
          {locs ? <RankedBars items={locs.localities.map((l) => ({ label: l.locality, value: l.count, sub: l.top_crime_types.join(", ") }))} /> : <ListSkeleton />}
        </div>
        <div className="card card-pad">
          <CardTitle>Hotspots · last {hots?.window_days ?? 30} days</CardTitle>
          {hots ? (
            <ol className="space-y-2.5">
              {hots.hotspots.map((h, i) => (
                <li key={h.locality} className="flex items-center justify-between text-sm">
                  <span className="flex items-center gap-2 min-w-0">
                    <span className="text-subtle w-4 text-right tabular-nums">{i + 1}</span>
                    <span className="truncate text-ink">{h.locality}</span>
                    {h.crime_type && <span className="chip">{h.crime_type}</span>}
                  </span>
                  <span className="tabular-nums shrink-0">
                    <span className="badge bg-saffron/15 text-saffron">▲ {h.recent_count}</span>
                    <span className="text-subtle ml-2">/ {h.count}</span>
                  </span>
                </li>
              ))}
            </ol>
          ) : <ListSkeleton />}
        </div>
      </div>
    </div>
  );
}

function Stat({ label, value, accent }: { label: string; value?: number; accent?: "saffron" | "green" }) {
  const color = accent === "saffron" ? "text-saffron" : accent === "green" ? "text-flaggreen" : "text-ink";
  return (
    <div className="stat">
      <div className="stat-label">{label}</div>
      <div className={`stat-value ${color}`}>
        {value === undefined ? <span className="skeleton inline-block h-7 w-12 align-middle" /> : value}
      </div>
    </div>
  );
}

const CardTitle = ({ children }: { children: React.ReactNode }) => (
  <h3 className="mb-4 text-sm font-semibold text-ink">{children}</h3>
);

function TrendChart({ data }: { data: TrendsResponse }) {
  if (data.buckets.length === 0) return <p className="text-sm text-subtle">No data yet.</p>;
  const max = Math.max(...data.buckets.map((b) => b.count));
  return (
    <div className="flex gap-1.5 h-40">
      {data.buckets.map((b) => {
        const h = max ? (b.count / max) * 100 : 0;
        return (
          <div key={b.bucket_start} className="group flex-1 flex flex-col gap-1" title={`${b.bucket_start}: ${b.count}`}>
            {/* flex-1 gives this track a definite height, so the bar's % height resolves */}
            <div className="relative w-full flex-1 flex items-end">
              <div className="relative w-full rounded-t-md bg-gradient-to-t from-brand-500 to-brand-500/60 group-hover:from-saffron group-hover:to-saffron/70 transition-colors"
                style={{ height: `${Math.max(h, 3)}%` }}>
                <span className="absolute -top-4 inset-x-0 text-center text-[10px] text-subtle opacity-0 group-hover:opacity-100 transition tabular-nums">{b.count}</span>
              </div>
            </div>
            <div className="text-[9px] text-subtle truncate w-full text-center">{b.bucket_start.slice(5)}</div>
          </div>
        );
      })}
    </div>
  );
}

function RankedBars({ items }: { items: { label: string; value: number; sub?: string }[] }) {
  const max = Math.max(1, ...items.map((i) => i.value));
  return (
    <ol className="space-y-2.5">
      {items.map((it, i) => (
        <li key={it.label} className="text-sm">
          <div className="flex items-center justify-between">
            <span className="flex items-center gap-2 min-w-0">
              <span className="text-subtle w-4 text-right tabular-nums">{i + 1}</span>
              <span className="truncate text-ink">{it.label}</span>
              {it.sub && <span className="chip truncate max-w-[10rem]">{it.sub}</span>}
            </span>
            <span className="tabular-nums font-medium">{it.value}</span>
          </div>
          <div className="mt-1 ml-6 h-1.5 rounded-full bg-surface-2 overflow-hidden">
            <div className="h-full rounded-full bg-brand-500" style={{ width: `${(it.value / max) * 100}%` }} />
          </div>
        </li>
      ))}
    </ol>
  );
}

const ChartSkeleton = () => (
  <div className="flex items-end gap-1.5 h-40">
    {Array.from({ length: 14 }).map((_, i) => (
      <div key={i} className="skeleton flex-1 rounded-t-md" style={{ height: `${20 + ((i * 37) % 70)}%` }} />
    ))}
  </div>
);
const ListSkeleton = () => (
  <div className="space-y-3">{Array.from({ length: 6 }).map((_, i) => <div key={i} className="skeleton h-4 w-full" />)}</div>
);
