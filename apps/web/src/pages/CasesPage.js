import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { casesApi } from "../api/endpoints";
export default function CasesPage() {
    const [cases, setCases] = useState(null);
    const [error, setError] = useState(null);
    useEffect(() => {
        casesApi.list().then(setCases).catch((e) => setError(e.message));
    }, []);
    if (error)
        return _jsx("p", { className: "text-rose-600", children: error });
    if (!cases)
        return _jsx("p", { className: "text-muted", children: "Loading cases\u2026" });
    if (cases.length === 0) {
        return (_jsxs("div", { className: "rounded border border-dashed border-line p-6 text-muted", children: ["No cases yet. Ingest a CSV via ", _jsx("code", { children: "/admin/ingest" }), " or", " ", _jsx("code", { children: "python -m services.ingest data/sample_cases.csv" }), "."] }));
    }
    return (_jsxs("div", { className: "space-y-3", children: [_jsx("h2", { className: "text-lg font-semibold", children: "Cases" }), _jsx("div", { className: "bg-card shadow rounded overflow-hidden", children: _jsxs("table", { className: "w-full text-sm", children: [_jsx("thead", { className: "bg-surface text-muted", children: _jsxs("tr", { children: [_jsx(Th, { children: "Case ID" }), _jsx(Th, { children: "Type" }), _jsx(Th, { children: "Locality" }), _jsx(Th, { children: "Occurred" }), _jsx(Th, { children: "Status" })] }) }), _jsx("tbody", { children: cases.map((c) => (_jsxs("tr", { className: "border-t hover:bg-surface", children: [_jsx(Td, { children: _jsx(Link, { to: `/cases/${c.case_id}`, className: "text-brand-600 hover:underline", children: c.case_id }) }), _jsx(Td, { children: c.crime_type }), _jsx(Td, { children: c.locality }), _jsx(Td, { children: c.occurred_on }), _jsx(Td, { children: c.status })] }, c.case_id))) })] }) })] }));
}
const Th = ({ children }) => (_jsx("th", { className: "text-left font-medium px-3 py-2", children: children }));
const Td = ({ children }) => (_jsx("td", { className: "px-3 py-2", children: children }));
