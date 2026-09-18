"use client";

import { useEffect, useRef, useState } from "react";
import type * as Leaflet from "leaflet";
import type { CanonicalEvent, Severity, SupplyAsset } from "@/lib/api";

export const severityColors: Record<Severity, string> = {
  LOW: "#39836b", MEDIUM: "#c58a21", HIGH: "#dc633b", CRITICAL: "#bd3558",
};
interface Props { assets: SupplyAsset[]; events: CanonicalEvent[]; selected: SupplyAsset | null; radiusKm: number; onSelect: (id: number) => void }

export default function AssetMap({ assets, events, selected, radiusKm, onSelect }: Props) {
  const container = useRef<HTMLDivElement>(null);
  const instance = useRef<{ leaflet: typeof Leaflet; map: Leaflet.Map; layers: Leaflet.LayerGroup } | null>(null);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState("");
  const [tileError, setTileError] = useState(false);
  useEffect(() => {
    let cancelled = false;
    import("leaflet").then((L) => {
      if (cancelled || !container.current) return;
      const map = L.map(container.current).setView([25, 25], 2);
      L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      }).on("tileerror", () => setTileError(true)).addTo(map);
      instance.current = { leaflet: L, map, layers: L.layerGroup().addTo(map) };
      setReady(true);
    }).catch(() => { if (!cancelled) setError("Map could not load. Asset and event lists remain available."); });
    return () => { cancelled = true; instance.current?.map.remove(); instance.current = null; };
  }, []);

  useEffect(() => {
    const current = instance.current;
    if (!ready || !current) return;
    const { leaflet: L, map, layers } = current;
    layers.clearLayers();
    events.forEach((event) => {
      const label = document.createElement("span");
      label.textContent = `${event.eventType} · ${event.severity} · ${event.country ?? "Country unavailable"}`;
      L.circleMarker([event.latitude, event.longitude], { radius: 7, color: severityColors[event.severity],
        fillColor: severityColors[event.severity], fillOpacity: 0.85, weight: 2 }).bindTooltip(label).addTo(layers);
    });
    assets.forEach((asset) => {
      const popup = document.createElement("span");
      popup.textContent = `${asset.name} · ${asset.type} · Criticality ${asset.criticality}/5 · ${asset.active ? "Active" : "Inactive"}`;
      const marker = L.marker([asset.latitude, asset.longitude], { title: asset.name,
        opacity: asset.active ? 1 : 0.45,
        icon: L.divIcon({ className: `asset-marker ${asset.type.toLowerCase()} ${selected?.id === asset.id ? "selected" : ""}`,
          html: asset.type === "PORT" ? "P" : "S", iconSize: [30, 30], iconAnchor: [15, 15] }),
      }).bindTooltip(popup).addTo(layers);
      marker.on("click", () => onSelect(asset.id));
    });
    if (selected?.active) {
      const circle = L.circle([selected.latitude, selected.longitude], { radius: radiusKm * 1000,
        color: "#2258a5", weight: 1, fillOpacity: 0.06 }).addTo(layers);
      map.fitBounds(circle.getBounds(), { padding: [28, 28], maxZoom: 11 });
    } else if (assets.length || events.length) {
      map.fitBounds(L.latLngBounds([...assets, ...events].map((point) => [point.latitude, point.longitude])), { padding: [30, 30], maxZoom: 8 });
    }
  }, [assets, events, selected, radiusKm, onSelect, ready]);

  return <div className="map-wrap"><div ref={container} className="map" aria-label="Supply assets and disruption events map" />
    {!ready && <p className="map-notice" role="status">{error || "Loading map…"}</p>}
    {tileError && <p className="map-notice" role="status">Map tiles unavailable. Markers and lists remain usable.</p>}</div>;
}
