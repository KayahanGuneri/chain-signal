export const eventTypes = ["EARTHQUAKE", "FLOOD", "CONFLICT", "PROTEST", "STRIKE"] as const;
export const severities = ["LOW", "MEDIUM", "HIGH", "CRITICAL"] as const;
export type EventType = (typeof eventTypes)[number];
export type Severity = (typeof severities)[number];
export type JsonValue = null | boolean | number | string | JsonValue[] | { [key: string]: JsonValue };
export interface CanonicalEvent {
  id: number; source: string; sourceEventId: string; eventType: EventType;
  occurredAt: string; latitude: number; longitude: number; severity: Severity;
  country: string | null; metadata: { [key: string]: JsonValue }; schemaVersion: string;
}
export interface SupplyAsset {
  id: number; type: "SUPPLIER" | "PORT"; name: string; country: string; city: string;
  latitude: number; longitude: number; criticality: number; active: boolean;
}
export interface NearbyEvent { event: CanonicalEvent; distanceMeters: number }

function object(value: unknown): Record<string, unknown> {
  if (value === null || typeof value !== "object" || Array.isArray(value)) throw new Error("Invalid API object");
  return value as Record<string, unknown>;
}
function text(value: unknown): string {
  if (typeof value !== "string" || !value.trim()) throw new Error("Invalid API text");
  return value;
}
function numeric(value: unknown, min: number, max: number): number {
  if (typeof value !== "number" || !Number.isFinite(value) || value < min || value > max) throw new Error("Invalid API number");
  return value;
}
function id(value: unknown): number {
  const result = numeric(value, 1, Number.MAX_SAFE_INTEGER);
  if (!Number.isSafeInteger(result)) throw new Error("Invalid API id");
  return result;
}
function enumeration<T extends string>(value: unknown, values: readonly T[]): T {
  if (typeof value !== "string" || !values.includes(value as T)) throw new Error("Invalid API enum");
  return value as T;
}
function json(value: unknown): JsonValue {
  if (value === null || typeof value === "boolean" || typeof value === "string") return value;
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (Array.isArray(value)) return value.map(json);
  return Object.fromEntries(Object.entries(object(value)).map(([key, item]) => [key, json(item)]));
}
export function parseEvent(value: unknown): CanonicalEvent {
  const row = object(value);
  const occurredAt = text(row.occurredAt);
  if (!/(Z|[+-]\d{2}:\d{2})$/.test(occurredAt) || !Number.isFinite(Date.parse(occurredAt))) throw new Error("Invalid API timestamp");
  return {
    id: id(row.id), source: text(row.source), sourceEventId: text(row.sourceEventId),
    eventType: enumeration(row.eventType, eventTypes), occurredAt,
    latitude: numeric(row.latitude, -90, 90), longitude: numeric(row.longitude, -180, 180),
    severity: enumeration(row.severity, severities), country: row.country === null ? null : text(row.country),
    metadata: Object.fromEntries(Object.entries(object(row.metadata)).map(([key, item]) => [key, json(item)])),
    schemaVersion: text(row.schemaVersion),
  };
}
export function parseAsset(value: unknown): SupplyAsset {
  const row = object(value);
  if (typeof row.active !== "boolean") throw new Error("Invalid API active state");
  const criticality = numeric(row.criticality, 1, 5);
  if (!Number.isInteger(criticality)) throw new Error("Invalid API criticality");
  return { id: id(row.id), type: enumeration(row.type, ["SUPPLIER", "PORT"]),
    name: text(row.name), country: text(row.country), city: text(row.city),
    latitude: numeric(row.latitude, -90, 90), longitude: numeric(row.longitude, -180, 180),
    criticality, active: row.active };
}
export function parseNearby(value: unknown): NearbyEvent {
  const row = object(value);
  return { event: parseEvent(row.event), distanceMeters: numeric(row.distanceMeters, 0, Number.MAX_VALUE) };
}
export async function fetchList<T>(path: string, parse: (value: unknown) => T, signal: AbortSignal): Promise<T[]> {
  const response = await fetch(path, { signal, cache: "no-store" });
  const payload: unknown = await response.json();
  if (!response.ok) {
    const error = object(payload);
    throw new Error(typeof error.message === "string" ? error.message : `API request failed (${response.status})`);
  }
  if (!Array.isArray(payload)) throw new Error("Invalid API collection");
  return payload.map(parse);
}
