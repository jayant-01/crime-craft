import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState } from "react";
import { predictiveApi } from "../api/endpoints";
const BAND_COLOR = {
    low: "text-emerald-700 bg-emerald-50 border-emerald-200",
    medium: "text-amber-700 bg-amber-50 border-amber-200",
    high: "text-rose-700 bg-rose-50 border-rose-200",
};
export default function RecidivismPage() {
    const [subject, setSubject] = useState("");
    const [reason, setReason] = useState("");
    const [resp, setResp] = useState(null);
    const [error, setError] = useState(null);
    const [submitting, setSubmitting] = useState(false);
    async function submit(e) {
        e.preventDefault();
        setError(null);
        setResp(null);
        setSubmitting(true);
        try {
            setResp(await predictiveApi.recidivism({ subject: subject.trim(), reason: reason.trim() }));
        }
        catch (err) {
            setError(err instanceof Error ? err.message : "scoring failed");
        }
        finally {
            setSubmitting(false);
        }
    }
    return (_jsxs("div", { className: "space-y-4 max-w-3xl", children: [_jsx("h2", { className: "text-lg font-semibold", children: "Recidivism risk scoring" }), _jsxs("p", { className: "text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded p-3", children: [_jsx("strong", { children: "Advisory only." }), " Scores are decision aids for senior officers, never a basis for action by themselves. Every score view is audit-logged with the reason you supply below."] }), _jsxs("form", { onSubmit: submit, className: "bg-card shadow rounded p-4 space-y-3", children: [_jsxs("label", { className: "block text-sm", children: [_jsx("span", { className: "text-ink", children: "Subject (suspect name from a case)" }), _jsx("input", { value: subject, onChange: (e) => setSubject(e.target.value), required: true, minLength: 1, className: "mt-1 w-full rounded border-line border px-2 py-1.5 text-sm", placeholder: "Ravi Kumar" })] }), _jsxs("label", { className: "block text-sm", children: [_jsx("span", { className: "text-ink", children: "Reason for this scoring (logged)" }), _jsx("textarea", { value: reason, onChange: (e) => setReason(e.target.value), required: true, minLength: 4, rows: 3, className: "mt-1 w-full rounded border-line border px-2 py-1.5 text-sm", placeholder: "Reviewing active investigation in HSR Layout for parole eligibility decision." })] }), _jsx("button", { disabled: submitting || !subject || reason.length < 4, className: "bg-brand-600 text-white rounded px-3 py-1.5 text-sm hover:bg-brand-700 disabled:opacity-50", children: submitting ? "Scoring…" : "Score subject" })] }), error && _jsx("p", { className: "text-rose-600 text-sm", children: error }), resp && (_jsxs("div", { className: "bg-card shadow rounded p-4 space-y-3", children: [_jsxs("div", { className: "flex items-center justify-between", children: [_jsx("h3", { className: "font-semibold", children: resp.subject }), _jsxs("span", { className: `text-xs uppercase border rounded px-2 py-0.5 ${BAND_COLOR[resp.band]}`, children: [resp.band, " \u00B7 ", (resp.score * 100).toFixed(0), "%"] })] }), _jsxs("p", { className: "text-xs text-muted", children: ["Model: ", _jsx("code", { children: resp.model_version }), resp.is_stub && _jsx("span", { className: "ml-2 text-amber-600", children: "(stub \u2014 not a trained model)" }), "\u00B7 ", resp.case_count, " cases linked"] }), _jsx("p", { className: "text-xs text-amber-700", children: resp.decision_note }), _jsxs("div", { children: [_jsx("h4", { className: "text-sm font-semibold mb-2", children: "Top contributing features" }), _jsx("ul", { className: "text-sm space-y-2", children: resp.top_contributions.map((c) => (_jsxs("li", { className: "border-l-2 border-line pl-3", children: [_jsxs("div", { className: "flex justify-between text-xs text-muted", children: [_jsx("span", { className: "font-mono", children: c.name }), _jsxs("span", { className: c.contribution > 0 ? "text-rose-600" : "text-emerald-600", children: [c.contribution > 0 ? "+" : "", c.contribution.toFixed(3)] })] }), _jsx("div", { children: c.explanation })] }, c.name))) })] })] }))] }));
}
