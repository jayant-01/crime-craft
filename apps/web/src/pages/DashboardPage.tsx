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
      .then(([t, l, h]) => {
        setTrends(t);
        setLocs(l);
        setHots(h);
      })
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <p className="text-rose-600">{error}</p>;

  return (
    <div className="space-y-6">
      <h2 className="text-lg font-semibold">Officer dashboard</h2>

      <Card title="Crime trend — weekly">
        {trends ? (
          <TrendChart data={trends} />
        ) : (
          <Loading />
        )}
      </Card>

      <div className="grid md:grid-cols-2 gap-6">
        <Card title="Top localities">
          {locs ? (
            <ol className="text-sm space-y-1">
              {locs.localities.map((l, i) => (
                <li key={l.locality} className="flex justify-between">
                  <span>
                    <span className="text-slate-400 mr-2">{i + 1}.</span>
                    {l.locality}
                    {l.top_crime_types.length > 0 && (
                      <span className="ml-2 text-xs text-slate-500">
                        ({l.top_crime_types.join(", ")})
                      </span>
                    )}
                  </span>
                  <span className="font-mono">{l.count}</span>
                </li>
              ))}
            </ol>
          ) : (
            <Loading />
          )}
        </Card>

        <Card title={`Hotspots (last ${hots?.window_days ?? 30} days)`}>
          {hots ? (
            <ol className="text-sm space-y-1">
              {hots.hotspots.map((h, i) => (
                <li key={h.locality} className="flex justify-between">
                  <span>
                    <span className="text-slate-400 mr-2">{i + 1}.</span>
                    {h.locality}
                    {h.crime_type && (
                      <span className="ml-2 text-xs text-slate-500">({h.crime_type})</span>
                    )}
                  </span>
                  <span className="font-mono">
                    <span className="text-rose-600">{h.recent_count}</span>
                    <span className="text-slate-400"> / {h.count}</span>
                  </span>
                </li>
              ))}
            </ol>
          ) : (
            <Loading />
          )}
        </Card>
      </div>
    </div>
  );
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-white shadow rounded p-4">
      <h3 className="text-sm font-semibold text-slate-700 mb-3">{title}</h3>
      {children}
    </div>
  );
}

function Loading() {
  return <p className="text-sm text-slate-400">Loading…</p>;
}

function TrendChart({ data }: { data: TrendsResponse }) {
  if (data.buckets.length === 0) {
    return <p className="text-sm text-slate-400">No data yet.</p>;
  }
  const max = Math.max(...data.buckets.map((b) => b.count));
  return (
    <div className="flex items-end gap-1 h-32">
      {data.buckets.map((b) => {
        const h = max ? (b.count / max) * 100 : 0;
        return (
          <div key={b.bucket_start} className="flex-1 flex flex-col items-center justify-end" title={`${b.bucket_start}: ${b.count}`}>
            <div className="w-full bg-brand-500 rounded-t" style={{ height: `${h}%` }} />
            <div className="text-[10px] text-slate-400 mt-1 truncate w-full text-center">
              {b.bucket_start.slice(5)}
            </div>
          </div>
        );
      })}
    </div>
  );
}
