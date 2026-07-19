import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { personApi } from "../api/endpoints";
import type { PersonDossier } from "../api/types";

const BAND_STYLE: Record<string, string> = {
  low: "bg-flaggreen/15 text-flaggreen",
  medium: "bg-saffron/15 text-saffron",
  high: "bg-rose-500/15 text-rose-600",
};

export default function PersonDossierPage() {
  const { name } = useParams<{ name: string }>();
  const [dossier, setDossier] = useState<PersonDossier | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    if (!name) { setDossier(null); return; }
    setError(null);
    setDossier(null);
    personApi.dossier(name).then(setDossier).catch((e) => setError(e.message));
  }, [name]);

  if (!name) {
    return (
      <div className="card card-pad max-w-md fade-in">
        <h3 className="font-semibold text-ink">Look up a person</h3>
        <p className="mt-1 text-sm text-muted">Enter a suspect's name to see their full dossier.</p>
        <form
          onSubmit={(e) => { e.preventDefault(); if (query.trim()) navigate(`/person/${encodeURIComponent(query.trim())}`); }}
          className="mt-4 flex gap-2"
        >
          <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="e.g. Ravi Kumar" className="input" autoFocus />
          <button className="btn btn-primary">Search</button>
        </form>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card card-pad">
        <p className="text-rose-600">{error}</p>
        <Link to="/person" className="mt-2 inline-block text-sm text-brand-600 hover:underline">← search again</Link>
      </div>
    );
  }
  if (!dossier) return <div className="space-y-4"><div className="skeleton h-24 w-full rounded-xl" /><div className="skeleton h-40 w-full rounded-xl" /></div>;

  return (
    <div className="space-y-5 fade-in">
      <Link to="/person" className="text-sm text-brand-600 hover:underline">← person lookup</Link>

      <div className="card card-pad flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <span className="grid h-12 w-12 place-items-center rounded-full bg-brand-600 text-white text-lg font-semibold">
            {dossier.name[0]?.toUpperCase()}
          </span>
          <div>
            <h2 className="text-xl font-semibold text-ink">{dossier.name}</h2>
            <p className="text-sm text-muted">
              {dossier.case_count} cases · {dossier.first_seen} → {dossier.last_seen}
            </p>
          </div>
        </div>
        {dossier.recidivism_band && (
          <div className="text-right">
            <div className="stat-label">Recidivism risk</div>
            <span className={`badge mt-1 capitalize ${BAND_STYLE[dossier.recidivism_band]}`}>
              {dossier.recidivism_band} · {Math.round((dossier.recidivism_score ?? 0) * 100)}%
            </span>
          </div>
        )}
      </div>

      <div className="grid md:grid-cols-3 gap-4">
        <ChipCard title="Crime types" items={dossier.crime_types} />
        <ChipCard title="Localities" items={dossier.localities} />
        <div className="card card-pad">
          <div className="stat-label mb-2">Co-accused</div>
          {dossier.co_accused.length ? (
            <div className="flex flex-wrap gap-2">
              {dossier.co_accused.map((c) => (
                <Link key={c} to={`/person/${encodeURIComponent(c)}`} className="chip hover:bg-brand-100 hover:text-brand-700 transition">
                  {c}
                </Link>
              ))}
            </div>
          ) : <p className="text-sm text-subtle">None recorded.</p>}
        </div>
      </div>

      <div className="card overflow-hidden">
        <div className="px-4 pt-4 stat-label">Case history</div>
        <div className="overflow-x-auto">
          <table className="table mt-2">
            <thead><tr><th>Case</th><th>Type</th><th>Locality</th><th>Occurred</th><th>Status</th></tr></thead>
            <tbody>
              {dossier.cases.map((c) => (
                <tr key={c.case_id}>
                  <td><Link to={`/cases/${c.case_id}`} className="font-medium text-brand-600 hover:underline">{c.case_id}</Link></td>
                  <td className="capitalize">{c.crime_type}</td>
                  <td>{c.locality}</td>
                  <td className="text-muted tabular-nums">{c.occurred_on}</td>
                  <td className="capitalize">{c.status.replace(/_/g, " ")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function ChipCard({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="card card-pad">
      <div className="stat-label mb-2">{title}</div>
      <div className="flex flex-wrap gap-2">
        {items.map((i) => <span key={i} className="chip capitalize">{i}</span>)}
      </div>
    </div>
  );
}
