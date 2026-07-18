import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { casesApi } from "../api/endpoints";
export default function CaseDetailPage() {
    const { id } = useParams();
    const [c, setCase] = useState(null);
    const [error, setError] = useState(null);
    useEffect(() => {
        if (!id)
            return;
        casesApi.get(id).then(setCase).catch((e) => setError(e.message));
    }, [id]);
    if (error)
        return _jsx("p", { className: "text-rose-600", children: error });
    if (!c)
        return _jsx("p", { className: "text-muted", children: "Loading\u2026" });
    const isOfficer = "mo_details" in c || "narrative" in c;
    return (_jsxs("div", { className: "space-y-4", children: [_jsx(Link, { to: "/cases", className: "text-sm text-brand-600 hover:underline", children: "\u2190 back to cases" }), _jsxs("div", { className: "bg-card shadow rounded p-6", children: [_jsxs("div", { className: "flex items-baseline justify-between", children: [_jsx("h2", { className: "text-xl font-semibold", children: c.case_id }), _jsx("span", { className: "text-xs uppercase bg-surface-2 px-2 py-0.5 rounded", children: c.status })] }), _jsxs("dl", { className: "mt-4 grid grid-cols-2 gap-x-4 gap-y-2 text-sm", children: [_jsx(Field, { label: "Crime type", value: c.crime_type }), _jsx(Field, { label: "Locality", value: c.locality }), _jsx(Field, { label: "Occurred", value: c.occurred_on }), isOfficer && "street_address" in c && (_jsx(Field, { label: "Street address", value: c.street_address ?? "—" }))] }), isOfficer && "mo_details" in c && c.mo_details && (_jsx(Section, { title: "MO details", children: c.mo_details })), isOfficer && "narrative" in c && c.narrative && (_jsx(Section, { title: "Narrative", children: c.narrative })), !isOfficer && (_jsx("p", { className: "mt-6 text-xs text-subtle", children: "Public view \u2014 additional fields are visible to authorized officers only." }))] })] }));
}
function Field({ label, value }) {
    return (_jsxs(_Fragment, { children: [_jsx("dt", { className: "text-muted", children: label }), _jsx("dd", { children: value })] }));
}
function Section({ title, children }) {
    return (_jsxs("div", { className: "mt-6", children: [_jsx("h3", { className: "text-sm font-semibold text-ink", children: title }), _jsx("p", { className: "mt-1 text-sm text-muted whitespace-pre-wrap", children: children })] }));
}
