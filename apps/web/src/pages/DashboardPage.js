import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect, useState } from "react";
import { analyticsApi } from "../api/endpoints";
export default function DashboardPage() {
    const [trends, setTrends] = useState(null);
    const [locs, setLocs] = useState(null);
    const [hots, setHots] = useState(null);
    const [error, setError] = useState(null);
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
    if (error)
        return _jsx("p", { className: "text-rose-600", children: error });
    return (_jsxs("div", { className: "space-y-6", children: [_jsx("h2", { className: "text-lg font-semibold", children: "Officer dashboard" }), _jsx(Card, { title: "Crime trend \u2014 weekly", children: trends ? (_jsx(TrendChart, { data: trends })) : (_jsx(Loading, {})) }), _jsxs("div", { className: "grid md:grid-cols-2 gap-6", children: [_jsx(Card, { title: "Top localities", children: locs ? (_jsx("ol", { className: "text-sm space-y-1", children: locs.localities.map((l, i) => (_jsxs("li", { className: "flex justify-between", children: [_jsxs("span", { children: [_jsxs("span", { className: "text-subtle mr-2", children: [i + 1, "."] }), l.locality, l.top_crime_types.length > 0 && (_jsxs("span", { className: "ml-2 text-xs text-muted", children: ["(", l.top_crime_types.join(", "), ")"] }))] }), _jsx("span", { className: "font-mono", children: l.count })] }, l.locality))) })) : (_jsx(Loading, {})) }), _jsx(Card, { title: `Hotspots (last ${hots?.window_days ?? 30} days)`, children: hots ? (_jsx("ol", { className: "text-sm space-y-1", children: hots.hotspots.map((h, i) => (_jsxs("li", { className: "flex justify-between", children: [_jsxs("span", { children: [_jsxs("span", { className: "text-subtle mr-2", children: [i + 1, "."] }), h.locality, h.crime_type && (_jsxs("span", { className: "ml-2 text-xs text-muted", children: ["(", h.crime_type, ")"] }))] }), _jsxs("span", { className: "font-mono", children: [_jsx("span", { className: "text-rose-600", children: h.recent_count }), _jsxs("span", { className: "text-subtle", children: [" / ", h.count] })] })] }, h.locality))) })) : (_jsx(Loading, {})) })] })] }));
}
function Card({ title, children }) {
    return (_jsxs("div", { className: "bg-card shadow rounded p-4", children: [_jsx("h3", { className: "text-sm font-semibold text-ink mb-3", children: title }), children] }));
}
function Loading() {
    return _jsx("p", { className: "text-sm text-subtle", children: "Loading\u2026" });
}
function TrendChart({ data }) {
    if (data.buckets.length === 0) {
        return _jsx("p", { className: "text-sm text-subtle", children: "No data yet." });
    }
    const max = Math.max(...data.buckets.map((b) => b.count));
    return (_jsx("div", { className: "flex items-end gap-1 h-32", children: data.buckets.map((b) => {
            const h = max ? (b.count / max) * 100 : 0;
            return (_jsxs("div", { className: "flex-1 flex flex-col items-center justify-end", title: `${b.bucket_start}: ${b.count}`, children: [_jsx("div", { className: "w-full bg-brand-500 rounded-t", style: { height: `${h}%` } }), _jsx("div", { className: "text-[10px] text-subtle mt-1 truncate w-full text-center", children: b.bucket_start.slice(5) })] }, b.bucket_start));
        }) }));
}
