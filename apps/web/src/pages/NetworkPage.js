import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import cytoscape from "cytoscape";
import { networkApi } from "../api/endpoints";
export default function NetworkPage() {
    const [params, setParams] = useSearchParams();
    const initialMode = params.get("mode") || "case";
    const initialQuery = params.get("q") || "";
    const initialDepth = Number(params.get("depth") || "1");
    const [mode, setMode] = useState(initialMode);
    const [query, setQuery] = useState(initialQuery);
    const [depth, setDepth] = useState(initialDepth);
    const [data, setData] = useState(null);
    const [error, setError] = useState(null);
    const [loading, setLoading] = useState(false);
    const containerRef = useRef(null);
    const cyRef = useRef(null);
    async function load() {
        if (!query.trim())
            return;
        setLoading(true);
        setError(null);
        try {
            const fetcher = mode === "case" ? networkApi.forCase : networkApi.forSuspect;
            const result = await fetcher(query.trim(), depth);
            setData(result);
            setParams({ mode, q: query.trim(), depth: String(depth) }, { replace: true });
        }
        catch (e) {
            setError(e instanceof Error ? e.message : "fetch failed");
            setData(null);
        }
        finally {
            setLoading(false);
        }
    }
    useEffect(() => {
        if (initialQuery)
            void load();
        // load only on first render with URL params; subsequent loads are user-driven
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);
    useEffect(() => {
        if (!data || !containerRef.current)
            return;
        cyRef.current?.destroy();
        const cy = cytoscape({
            container: containerRef.current,
            elements: [
                ...data.nodes.map((n) => ({
                    data: { id: n.id, label: n.label, kind: n.kind, ...n.properties },
                })),
                ...data.edges.map((e) => ({
                    data: { id: e.id, source: e.source, target: e.target, kind: e.kind, weight: e.weight },
                })),
            ],
            style: [
                {
                    selector: "node",
                    style: {
                        label: "data(label)",
                        "text-wrap": "wrap",
                        "text-max-width": "100px",
                        "font-size": "10px",
                        "text-valign": "bottom",
                        "text-margin-y": 4,
                        color: "#1e293b",
                        width: 28,
                        height: 28,
                    },
                },
                { selector: 'node[kind="case"]', style: { "background-color": "#2f4988", shape: "round-rectangle" } },
                { selector: 'node[kind="suspect"]', style: { "background-color": "#b91c1c", shape: "ellipse" } },
                {
                    selector: 'node[id="' + data.center_id + '"]',
                    style: { "border-width": 3, "border-color": "#facc15" },
                },
                {
                    selector: "edge",
                    style: {
                        "curve-style": "bezier",
                        "target-arrow-shape": "triangle",
                        "line-color": "#94a3b8",
                        "target-arrow-color": "#94a3b8",
                        width: 1.5,
                    },
                },
                {
                    selector: 'edge[kind="co_suspect"]',
                    style: {
                        "line-style": "dashed",
                        "line-color": "#fb7185",
                        "target-arrow-shape": "none",
                    },
                },
            ],
            layout: { name: "cose", animate: false, padding: 30 },
        });
        cyRef.current = cy;
        return () => {
            cy.destroy();
        };
    }, [data]);
    return (_jsxs("div", { className: "space-y-4", children: [_jsx("h2", { className: "text-lg font-semibold", children: "Criminal network" }), _jsxs("form", { className: "flex flex-wrap gap-2 items-center bg-card shadow rounded p-3", onSubmit: (e) => {
                    e.preventDefault();
                    void load();
                }, children: [_jsxs("select", { value: mode, onChange: (e) => setMode(e.target.value), className: "rounded border-line border px-2 py-1 text-sm", children: [_jsx("option", { value: "case", children: "By case" }), _jsx("option", { value: "suspect", children: "By suspect" })] }), _jsx("input", { value: query, onChange: (e) => setQuery(e.target.value), placeholder: mode === "case" ? "FIR-2025-1001" : "Ravi Kumar", className: "flex-1 min-w-[14rem] rounded border-line border px-2 py-1 text-sm" }), _jsxs("label", { className: "text-sm text-muted flex items-center gap-1", children: ["depth", _jsx("input", { type: "number", min: 0, max: 3, value: depth, onChange: (e) => setDepth(Number(e.target.value)), className: "w-14 rounded border-line border px-2 py-1 text-sm" })] }), _jsx("button", { className: "bg-brand-600 text-white rounded px-3 py-1 text-sm hover:bg-brand-700", children: loading ? "Loading…" : "Render" })] }), error && _jsx("p", { className: "text-rose-600 text-sm", children: error }), _jsxs("div", { className: "bg-card shadow rounded p-2", children: [_jsx("div", { ref: containerRef, className: "w-full h-[28rem] bg-surface rounded" }), data && (_jsxs("p", { className: "text-xs text-subtle mt-2", children: [data.nodes.length, " nodes \u00B7 ", data.edges.length, " edges \u00B7 depth ", data.depth] }))] }), _jsxs("div", { className: "text-xs text-muted", children: ["Legend: ", _jsx("span", { className: "text-brand-700", children: "\u25A0 case" }), " \u00B7", _jsx("span", { className: "text-rose-700 ml-1", children: "\u25CF suspect" }), " \u00B7 solid arrow = mentions \u00B7 ", _jsx("span", { className: "text-rose-600", children: "dashed" }), " = co-suspect."] })] }));
}
