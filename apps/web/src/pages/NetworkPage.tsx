import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import cytoscape from "cytoscape";
import { networkApi } from "../api/endpoints";
import type { NetworkResponse } from "../api/types";

type Mode = "case" | "suspect";

export default function NetworkPage() {
  const [params, setParams] = useSearchParams();
  const initialMode = (params.get("mode") as Mode) || "case";
  const initialQuery = params.get("q") || "";
  const initialDepth = Number(params.get("depth") || "1");

  const [mode, setMode] = useState<Mode>(initialMode);
  const [query, setQuery] = useState(initialQuery);
  const [depth, setDepth] = useState(initialDepth);
  const [data, setData] = useState<NetworkResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);

  async function load() {
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const fetcher = mode === "case" ? networkApi.forCase : networkApi.forSuspect;
      const result = await fetcher(query.trim(), depth);
      setData(result);
      setParams({ mode, q: query.trim(), depth: String(depth) }, { replace: true });
    } catch (e) {
      setError(e instanceof Error ? e.message : "fetch failed");
      setData(null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (initialQuery) void load();
    // load only on first render with URL params; subsequent loads are user-driven
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!data || !containerRef.current) return;
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

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">Criminal network</h2>
      <form
        className="flex flex-wrap gap-2 items-center bg-white shadow rounded p-3"
        onSubmit={(e) => {
          e.preventDefault();
          void load();
        }}
      >
        <select
          value={mode}
          onChange={(e) => setMode(e.target.value as Mode)}
          className="rounded border-slate-300 border px-2 py-1 text-sm"
        >
          <option value="case">By case</option>
          <option value="suspect">By suspect</option>
        </select>
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={mode === "case" ? "FIR-2025-1001" : "Ravi Kumar"}
          className="flex-1 min-w-[14rem] rounded border-slate-300 border px-2 py-1 text-sm"
        />
        <label className="text-sm text-slate-600 flex items-center gap-1">
          depth
          <input
            type="number"
            min={0}
            max={3}
            value={depth}
            onChange={(e) => setDepth(Number(e.target.value))}
            className="w-14 rounded border-slate-300 border px-2 py-1 text-sm"
          />
        </label>
        <button className="bg-brand-600 text-white rounded px-3 py-1 text-sm hover:bg-brand-700">
          {loading ? "Loading…" : "Render"}
        </button>
      </form>

      {error && <p className="text-rose-600 text-sm">{error}</p>}

      <div className="bg-white shadow rounded p-2">
        <div ref={containerRef} className="w-full h-[28rem] bg-slate-50 rounded" />
        {data && (
          <p className="text-xs text-slate-400 mt-2">
            {data.nodes.length} nodes · {data.edges.length} edges · depth {data.depth}
          </p>
        )}
      </div>

      <div className="text-xs text-slate-500">
        Legend: <span className="text-brand-700">■ case</span> ·
        <span className="text-rose-700 ml-1">● suspect</span> ·
        solid arrow = mentions · <span className="text-rose-600">dashed</span> = co-suspect.
      </div>
    </div>
  );
}
