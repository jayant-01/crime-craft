import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { casesApi } from "../api/endpoints";
import type { Case } from "../api/types";

export default function CasesPage() {
  const [cases, setCases] = useState<Case[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    casesApi.list().then(setCases).catch((e) => setError(e.message));
  }, []);

  if (error) return <p className="text-rose-600">{error}</p>;
  if (!cases) return <p className="text-slate-500">Loading cases…</p>;
  if (cases.length === 0) {
    return (
      <div className="rounded border border-dashed border-slate-300 p-6 text-slate-500">
        No cases yet. Ingest a CSV via <code>/admin/ingest</code> or{" "}
        <code>python -m services.ingest data/sample_cases.csv</code>.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <h2 className="text-lg font-semibold">Cases</h2>
      <div className="bg-white shadow rounded overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-slate-600">
            <tr>
              <Th>Case ID</Th>
              <Th>Type</Th>
              <Th>Locality</Th>
              <Th>Occurred</Th>
              <Th>Status</Th>
            </tr>
          </thead>
          <tbody>
            {cases.map((c) => (
              <tr key={c.case_id} className="border-t hover:bg-slate-50">
                <Td>
                  <Link to={`/cases/${c.case_id}`} className="text-brand-600 hover:underline">
                    {c.case_id}
                  </Link>
                </Td>
                <Td>{c.crime_type}</Td>
                <Td>{c.locality}</Td>
                <Td>{c.occurred_on}</Td>
                <Td>{c.status}</Td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

const Th = ({ children }: { children: React.ReactNode }) => (
  <th className="text-left font-medium px-3 py-2">{children}</th>
);
const Td = ({ children }: { children: React.ReactNode }) => (
  <td className="px-3 py-2">{children}</td>
);
