import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { casesApi } from "../api/endpoints";
import type { Case } from "../api/types";

const STATUS_STYLE: Record<string, string> = {
  open: "bg-saffron/15 text-saffron",
  under_investigation: "bg-brand-500/15 text-brand-600",
  chargesheeted: "bg-flaggreen/15 text-flaggreen",
  closed: "bg-surface-2 text-muted",
};

export default function CasesPage() {
  const [cases, setCases] = useState<Case[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [q, setQ] = useState("");

  useEffect(() => {
    casesApi.list().then(setCases).catch((e) => setError(e.message));
  }, []);

  const filtered = useMemo(() => {
    if (!cases) return null;
    const s = q.trim().toLowerCase();
    if (!s) return cases;
    return cases.filter((c) =>
      [c.case_id, c.crime_type, c.locality, c.status].some((v) => String(v).toLowerCase().includes(s)),
    );
  }, [cases, q]);

  if (error) return <p className="text-rose-600">{error}</p>;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search cases…" className="input max-w-xs" />
        <span className="text-sm text-muted">{filtered ? `${filtered.length} cases` : ""}</span>
      </div>

      <div className="card overflow-hidden">
        {!filtered ? (
          <div className="p-5 space-y-3">{Array.from({ length: 8 }).map((_, i) => <div key={i} className="skeleton h-5 w-full" />)}</div>
        ) : filtered.length === 0 ? (
          <div className="p-8 text-center text-muted">No matching cases.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="table">
              <thead>
                <tr><th>Case ID</th><th>Type</th><th>Locality</th><th>Occurred</th><th>Status</th></tr>
              </thead>
              <tbody>
                {filtered.map((c) => (
                  <tr key={c.case_id}>
                    <td>
                      <Link to={`/cases/${c.case_id}`} className="font-medium text-brand-600 hover:underline">{c.case_id}</Link>
                    </td>
                    <td className="capitalize">{c.crime_type}</td>
                    <td>{c.locality}</td>
                    <td className="tabular-nums text-muted">{c.occurred_on}</td>
                    <td>
                      <span className={`badge capitalize ${STATUS_STYLE[c.status] ?? "bg-surface-2 text-muted"}`}>
                        {String(c.status).replace(/_/g, " ")}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
