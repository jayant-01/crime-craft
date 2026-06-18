import { useState } from "react";
import { predictiveApi } from "../api/endpoints";
import type { RecidivismResponse, RiskBand } from "../api/types";

const BAND_COLOR: Record<RiskBand, string> = {
  low: "text-emerald-700 bg-emerald-50 border-emerald-200",
  medium: "text-amber-700 bg-amber-50 border-amber-200",
  high: "text-rose-700 bg-rose-50 border-rose-200",
};

export default function RecidivismPage() {
  const [subject, setSubject] = useState("");
  const [reason, setReason] = useState("");
  const [resp, setResp] = useState<RecidivismResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setResp(null);
    setSubmitting(true);
    try {
      setResp(await predictiveApi.recidivism({ subject: subject.trim(), reason: reason.trim() }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "scoring failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="space-y-4 max-w-3xl">
      <h2 className="text-lg font-semibold">Recidivism risk scoring</h2>
      <p className="text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded p-3">
        <strong>Advisory only.</strong> Scores are decision aids for senior officers,
        never a basis for action by themselves. Every score view is audit-logged
        with the reason you supply below.
      </p>

      <form onSubmit={submit} className="bg-white shadow rounded p-4 space-y-3">
        <label className="block text-sm">
          <span className="text-slate-700">Subject (suspect name from a case)</span>
          <input
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            required
            minLength={1}
            className="mt-1 w-full rounded border-slate-300 border px-2 py-1.5 text-sm"
            placeholder="Ravi Kumar"
          />
        </label>
        <label className="block text-sm">
          <span className="text-slate-700">Reason for this scoring (logged)</span>
          <textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            required
            minLength={4}
            rows={3}
            className="mt-1 w-full rounded border-slate-300 border px-2 py-1.5 text-sm"
            placeholder="Reviewing active investigation in HSR Layout for parole eligibility decision."
          />
        </label>
        <button
          disabled={submitting || !subject || reason.length < 4}
          className="bg-brand-600 text-white rounded px-3 py-1.5 text-sm hover:bg-brand-700 disabled:opacity-50"
        >
          {submitting ? "Scoring…" : "Score subject"}
        </button>
      </form>

      {error && <p className="text-rose-600 text-sm">{error}</p>}

      {resp && (
        <div className="bg-white shadow rounded p-4 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold">{resp.subject}</h3>
            <span className={`text-xs uppercase border rounded px-2 py-0.5 ${BAND_COLOR[resp.band]}`}>
              {resp.band} · {(resp.score * 100).toFixed(0)}%
            </span>
          </div>
          <p className="text-xs text-slate-500">
            Model: <code>{resp.model_version}</code>
            {resp.is_stub && <span className="ml-2 text-amber-600">(stub — not a trained model)</span>}
            · {resp.case_count} cases linked
          </p>
          <p className="text-xs text-amber-700">{resp.decision_note}</p>

          <div>
            <h4 className="text-sm font-semibold mb-2">Top contributing features</h4>
            <ul className="text-sm space-y-2">
              {resp.top_contributions.map((c) => (
                <li key={c.name} className="border-l-2 border-slate-200 pl-3">
                  <div className="flex justify-between text-xs text-slate-500">
                    <span className="font-mono">{c.name}</span>
                    <span className={c.contribution > 0 ? "text-rose-600" : "text-emerald-600"}>
                      {c.contribution > 0 ? "+" : ""}
                      {c.contribution.toFixed(3)}
                    </span>
                  </div>
                  <div>{c.explanation}</div>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}
