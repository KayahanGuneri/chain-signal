"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useState } from "react";
import { fetchList, parseAsset, parseEvent, parseNearby, type CanonicalEvent, type NearbyEvent, type SupplyAsset } from "@/lib/api";

const AssetMap = dynamic(() => import("./asset-map"), { ssr: false, loading: () => <div className="map placeholder">Loading map…</div> });
type Load<T> = { status: "loading" } | { status: "error"; message: string } | { status: "loaded"; data: T };
const message = (error: unknown) => error instanceof Error ? error.message : "Request failed";

function Nearby({ asset, radiusKm, onLoaded }: { asset: SupplyAsset; radiusKm: number; onLoaded: (events: NearbyEvent[]) => void }) {
  const [state, setState] = useState<Load<NearbyEvent[]>>({ status: "loading" });
  useEffect(() => {
    const controller = new AbortController();
    fetchList(`/api/supply-assets/${asset.id}/nearby-events?radiusKm=${radiusKm}&limit=100`, parseNearby, controller.signal)
      .then((data) => { if (!controller.signal.aborted) { setState({ status: "loaded", data }); onLoaded(data); } })
      .catch((error: unknown) => { if (!controller.signal.aborted) setState({ status: "error", message: message(error) }); });
    return () => controller.abort();
  }, [asset.id, radiusKm, onLoaded]);
  if (state.status === "loading") return <p role="status">Finding nearby events…</p>;
  if (state.status === "error") return <p className="error" role="alert">{state.message}</p>;
  return <><p className="muted">{state.data.length} events within {radiusKm} km{state.data.length === 100 ? " · First 100 closest results" : ""}</p>
    {state.data.length === 0 ? <p>No events within this radius. Try a wider search.</p> : <ul className="event-list">{state.data.map(({ event, distanceMeters }) =>
      <li key={event.id}><EventSummary event={event} /><strong>{(distanceMeters / 1000).toFixed(2)} km</strong></li>)}</ul>}</>;
}

function EventSummary({ event }: { event: CanonicalEvent }) {
  return <div><span className={`badge ${event.severity.toLowerCase()}`}>{event.severity}</span> <strong>{event.eventType}</strong>
    <p className="muted">{event.country ?? "Country unavailable"} · {new Date(event.occurredAt).toLocaleString()}<br />{event.source} / {event.sourceEventId}</p></div>;
}

export default function Dashboard() {
  const [state, setState] = useState<Load<{ assets: SupplyAsset[]; events: CanonicalEvent[] }>>({ status: "loading" });
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [radiusKm, setRadiusKm] = useState(100);
  const [radiusInput, setRadiusInput] = useState("100");
  const [radiusError, setRadiusError] = useState("");
  const [nearby, setNearby] = useState<NearbyEvent[]>([]);
  const [attempt, setAttempt] = useState(0);
  const mapEvents = useMemo(() => state.status === "loaded"
    ? [...new Map([...state.data.events, ...nearby.map((item) => item.event)].map((event) => [event.id, event])).values()]
    : [], [state, nearby]);
  useEffect(() => {
    const controller = new AbortController();
    Promise.all([fetchList("/api/supply-assets", parseAsset, controller.signal), fetchList("/api/events?limit=100", parseEvent, controller.signal)])
      .then(([assets, events]) => { if (!controller.signal.aborted) {
        setState({ status: "loaded", data: { assets, events } });
        setSelectedId(assets.find((asset) => asset.active)?.id ?? null);
      } })
      .catch((error: unknown) => { if (!controller.signal.aborted) setState({ status: "error", message: message(error) }); });
    return () => controller.abort();
  }, [attempt]);
  const select = useCallback((id: number) => {
    if (id !== selectedId) { setSelectedId(id); setNearby([]); }
  }, [selectedId]);
  const loaded = useCallback((events: NearbyEvent[]) => setNearby(events), []);

  if (state.status === "loading") return <main><h1>ChainSignal</h1><p role="status">Loading assets and events…</p></main>;
  if (state.status === "error") return <main><h1>ChainSignal</h1><p className="error" role="alert">{state.message}</p>
    <button onClick={() => { setState({ status: "loading" }); setAttempt(attempt + 1); }}>Retry connection</button></main>;
  const { assets, events } = state.data;
  const selected = assets.find((asset) => asset.id === selectedId) ?? null;
  return <main>
    <header><div><p className="eyebrow">Supply chain risk intelligence</p><h1>ChainSignal</h1><p className="muted">Explore disruptions around your suppliers and ports.</p></div>
      <div className="stats"><strong>{assets.filter((asset) => asset.active).length}<span>Active assets</span></strong><strong>{events.length}<span>Recent events</span></strong></div></header>
    <div className="workspace"><aside className="panel"><h2>Supply assets</h2><p className="muted">Select an asset to explore nearby events.</p>
      {assets.length === 0 ? <p>No supply assets yet. Create an asset through the SupplyAsset API to begin.</p> :
        <ul className="asset-list">{assets.map((asset) => <li key={asset.id}><button className={selectedId === asset.id ? "asset-card chosen" : "asset-card"} onClick={() => select(asset.id)} aria-pressed={selectedId === asset.id}>
          <span className={`type-icon ${asset.type.toLowerCase()}`}>{asset.type === "PORT" ? "P" : "S"}</span><span><strong>{asset.name}</strong><small>{asset.type} · {asset.city}, {asset.country}</small><small>Criticality {asset.criticality}/5 · {asset.active ? "Active" : "Inactive"}</small></span></button></li>)}</ul>}
    </aside><section className="panel map-panel"><div className="panel-heading"><h2>Geospatial overview</h2><span className="muted">Latest 100 events + nearby results</span></div>
      <AssetMap assets={assets} events={mapEvents} selected={selected} radiusKm={radiusKm} onSelect={select} />
      <div className="legend"><span><i className="supplier" /> Supplier</span><span><i className="port" /> Port</span>{["LOW", "MEDIUM", "HIGH", "CRITICAL"].map((severity) => <span key={severity}><i className={severity.toLowerCase()} /> {severity}</span>)}</div>
    </section></div>
    <div className="details"><section className="panel"><h2>{selected ? `Nearby · ${selected.name}` : "Nearby events"}</h2>
      <form className="radius-form" onSubmit={(event) => { event.preventDefault(); const radius = Number(radiusInput);
        if (!Number.isFinite(radius) || radius <= 0 || radius > 1000) { setRadiusError("Enter a radius greater than 0 and at most 1000 km."); return; }
        setRadiusError(""); if (radius !== radiusKm) { setNearby([]); setRadiusKm(radius); } }}>
        <label htmlFor="radius">Search radius (km)</label><input id="radius" type="number" min="0.01" max="1000" step="any" value={radiusInput} onChange={(event) => setRadiusInput(event.target.value)} /><button type="submit">Search</button></form>
      {radiusError && <p className="error" role="alert">{radiusError}</p>}
      {!selected ? <p>Select an active supply asset to search.</p> : !selected.active ? <p>This asset is inactive. Nearby lookup is available for active assets only.</p> :
        <Nearby key={`${selected.id}:${radiusKm}`} asset={selected} radiusKm={radiusKm} onLoaded={loaded} />}
    </section><section className="panel"><h2>Recent disruptions</h2><p className="muted">Newest first · up to 100 events</p>
      {events.length === 0 ? <p>No canonical events yet. Run the GDACS ingestion and normalization pipeline.</p> : <ul className="event-list">{events.map((event) => <li key={event.id}><EventSummary event={event} /></li>)}</ul>}
    </section></div>
  </main>;
}
