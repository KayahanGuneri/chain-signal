import assert from "node:assert/strict";
import { test } from "node:test";
import { fetchList, parseAsset, parseEvent, parseNearby } from "../src/lib/api.ts";

const event = { id: 1, source: "GDACS", sourceEventId: "EQ:1", eventType: "EARTHQUAKE",
  occurredAt: "2026-09-01T00:00:00Z", latitude: 41, longitude: 29, severity: "HIGH",
  country: null, metadata: { nested: [true, null, { text: "Türkiye" }] }, schemaVersion: "v1" };
const asset = { id: 1, type: "PORT", name: " Port ", country: "Türkiye", city: "İstanbul",
  latitude: 41, longitude: 29, criticality: 5, active: false };

test("canonical metadata stays structured and country stays nullable", () => {
  assert.deepEqual(parseEvent(event), event);
  assert.equal(parseEvent({ ...event, country: " Provider text " }).country, " Provider text ");
});
test("asset text and inactive state remain unchanged", () => assert.deepEqual(parseAsset(asset), asset));
test("nearby distance stays in meters", () => assert.equal(parseNearby({ event, distanceMeters: 1100 }).distanceMeters, 1100));
test("malformed event enums, ids, timestamps, coordinates and metadata are rejected", () => {
  for (const bad of [{ eventType: "OTHER" }, { severity: "OTHER" }, { metadata: "{}" }, { metadata: [] },
    { latitude: 91 }, { longitude: -181 }, { id: 1.2 }, { id: Number.MAX_SAFE_INTEGER + 1 },
    { occurredAt: "2026-09-01T00:00:00" }, { occurredAt: "invalidZ" }, { country: " " }]) {
    assert.throws(() => parseEvent({ ...event, ...bad }));
  }
});
test("invalid asset numeric, enum and active fields are rejected", () => {
  for (const bad of [{ type: "OTHER" }, { criticality: 0 }, { criticality: 2.5 }, { active: "true" }, { latitude: NaN }]) assert.throws(() => parseAsset({ ...asset, ...bad }));
});
test("invalid distances and missing nearby event are rejected", () => {
  for (const distanceMeters of [-1, NaN, Infinity]) assert.throws(() => parseNearby({ event, distanceMeters }));
  assert.throws(() => parseNearby({ distanceMeters: 0 }));
});
test("fetch parses successful arrays and forwards abort signal", async () => {
  const original = globalThis.fetch;
  const controller = new AbortController();
  globalThis.fetch = async (_input, init) => {
    assert.equal(init?.signal, controller.signal);
    return Response.json([event]);
  };
  try { assert.deepEqual(await fetchList("/api/events", parseEvent, controller.signal), [event]); }
  finally { globalThis.fetch = original; }
});
test("fetch surfaces API errors and rejects non-array successes", async () => {
  const original = globalThis.fetch;
  try {
    globalThis.fetch = async () => Response.json({ message: "Active supply asset not found: 1" }, { status: 404 });
    await assert.rejects(fetchList("/api/events", parseEvent, new AbortController().signal), /Active supply asset not found/);
    globalThis.fetch = async () => Response.json({ event });
    await assert.rejects(fetchList("/api/events", parseEvent, new AbortController().signal), /Invalid API collection/);
  } finally { globalThis.fetch = original; }
});
