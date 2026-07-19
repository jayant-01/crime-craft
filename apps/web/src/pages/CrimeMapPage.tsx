import { useEffect, useMemo, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { mapApi } from "../api/endpoints";
import type { MapPoint } from "../api/types";
import { useTheme } from "../theme/ThemeContext";

const CRIME_COLORS: Record<string, string> = {
  theft: "#3949ab", burglary: "#8e24aa", "vehicle theft": "#00897b",
  robbery: "#e53935", assault: "#fb8c00", cybercrime: "#1e88e5",
  fraud: "#6d4c41", kidnapping: "#d81b60",
};
const DEFAULT_COLOR = "#607d8b";

export default function CrimeMapPage() {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const [points, setPoints] = useState<MapPoint[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [type, setType] = useState("all");
  const { theme } = useTheme();

  useEffect(() => {
    mapApi.points().then((r) => setPoints(r.points)).catch((e) => setError(e.message));
  }, []);

  const crimeTypes = useMemo(
    () => (points ? Array.from(new Set(points.map((p) => p.crime_type))).sort() : []),
    [points],
  );

  useEffect(() => {
    if (!containerRef.current || !points || mapRef.current) return;
    const tiles = [
      `https://a.basemaps.cartocdn.com/${theme === "dark" ? "dark_all" : "light_all"}/{z}/{x}/{y}.png`,
    ];
    const map = new maplibregl.Map({
      container: containerRef.current,
      style: {
        version: 8,
        sources: { base: { type: "raster", tiles, tileSize: 256, attribution: "© OpenStreetMap © CARTO" } },
        layers: [{ id: "base", type: "raster", source: "base" }],
      },
      center: [77.5946, 12.9716],
      zoom: 11,
    });
    mapRef.current = map;
    map.addControl(new maplibregl.NavigationControl(), "top-right");

    map.on("load", () => {
      map.addSource("cases", { type: "geojson", data: toGeoJSON(points) });
      const colorMatch: unknown[] = ["match", ["get", "crime_type"]];
      Object.entries(CRIME_COLORS).forEach(([k, v]) => colorMatch.push(k, v));
      colorMatch.push(DEFAULT_COLOR);
      map.addLayer({
        id: "cases",
        type: "circle",
        source: "cases",
        paint: {
          "circle-radius": 6,
          "circle-color": colorMatch as maplibregl.DataDrivenPropertyValueSpecification<string>,
          "circle-stroke-width": 1.5,
          "circle-stroke-color": "#ffffff",
          "circle-opacity": 0.9,
        },
      });
      map.on("click", "cases", (e) => {
        const f = e.features?.[0];
        if (!f) return;
        const p = f.properties as Record<string, string>;
        const coords = (f.geometry as unknown as { coordinates: [number, number] }).coordinates;
        new maplibregl.Popup({ closeButton: true })
          .setLngLat(coords)
          .setHTML(
            `<div style="font:13px system-ui;line-height:1.4"><b>${p.case_id}</b><br/>` +
            `${p.crime_type} · ${p.locality}<br/><span style="color:#666">${p.occurred_on} · ${p.status}</span></div>`,
          )
          .addTo(map);
      });
      map.on("mouseenter", "cases", () => (map.getCanvas().style.cursor = "pointer"));
      map.on("mouseleave", "cases", () => (map.getCanvas().style.cursor = ""));

      const bounds = new maplibregl.LngLatBounds();
      points.forEach((p) => bounds.extend([p.lng, p.lat]));
      if (!bounds.isEmpty()) map.fitBounds(bounds, { padding: 60, maxZoom: 13 });
    });

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, [points, theme]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.getLayer("cases")) return;
    map.setFilter("cases", type === "all" ? null : ["==", ["get", "crime_type"], type]);
  }, [type]);

  if (error) return <p className="text-rose-600">{error}</p>;

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3 flex-wrap">
        <select value={type} onChange={(e) => setType(e.target.value)} className="input max-w-[12rem] capitalize">
          <option value="all">All crime types</option>
          {crimeTypes.map((t) => <option key={t} value={t} className="capitalize">{t}</option>)}
        </select>
        <span className="text-sm text-muted">{points ? `${points.length} cases plotted` : "loading…"}</span>
        <div className="ml-auto hidden md:flex flex-wrap gap-2">
          {crimeTypes.map((t) => (
            <span key={t} className="chip capitalize">
              <span className="inline-block h-2 w-2 rounded-full" style={{ background: CRIME_COLORS[t] ?? DEFAULT_COLOR }} />
              {t}
            </span>
          ))}
        </div>
      </div>
      <div className="card overflow-hidden">
        <div ref={containerRef} className="h-[68vh] w-full" />
      </div>
    </div>
  );
}

function toGeoJSON(points: MapPoint[]) {
  return {
    type: "FeatureCollection" as const,
    features: points.map((p) => ({
      type: "Feature" as const,
      geometry: { type: "Point" as const, coordinates: [p.lng, p.lat] },
      properties: {
        case_id: p.case_id, crime_type: p.crime_type, locality: p.locality,
        occurred_on: p.occurred_on, status: p.status,
      },
    })),
  };
}
