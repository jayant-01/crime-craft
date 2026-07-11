import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { casesApi } from "../api/endpoints";
import type { Case } from "../api/types";

export default function CaseDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [c, setCase] = useState<Case | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    casesApi.get(id).then(setCase).catch((e) => setError(e.message));
  }, [id]);

  if (error) return <p className="text-rose-600">{error}</p>;
  if (!c) return <p className="text-muted">Loading…</p>;

  const isOfficer = "mo_details" in c || "narrative" in c;
  return (
    <div className="space-y-4">
      <Link to="/cases" className="text-sm text-brand-600 hover:underline">← back to cases</Link>
      <div className="bg-card shadow rounded p-6">
        <div className="flex items-baseline justify-between">
          <h2 className="text-xl font-semibold">{c.case_id}</h2>
          <span className="text-xs uppercase bg-surface-2 px-2 py-0.5 rounded">{c.status}</span>
        </div>
        <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
          <Field label="Crime type" value={c.crime_type} />
          <Field label="Locality" value={c.locality} />
          <Field label="Occurred" value={c.occurred_on} />
          {isOfficer && "street_address" in c && (
            <Field label="Street address" value={c.street_address ?? "—"} />
          )}
        </dl>
        {isOfficer && "mo_details" in c && c.mo_details && (
          <Section title="MO details">{c.mo_details}</Section>
        )}
        {isOfficer && "narrative" in c && c.narrative && (
          <Section title="Narrative">{c.narrative}</Section>
        )}
        {!isOfficer && (
          <p className="mt-6 text-xs text-subtle">
            Public view — additional fields are visible to authorized officers only.
          </p>
        )}
      </div>
    </div>
  );
}

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <>
      <dt className="text-muted">{label}</dt>
      <dd>{value}</dd>
    </>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mt-6">
      <h3 className="text-sm font-semibold text-ink">{title}</h3>
      <p className="mt-1 text-sm text-muted whitespace-pre-wrap">{children}</p>
    </div>
  );
}
