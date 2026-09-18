# Phase 2 geospatial API

Spring Boot owns the public API and SupplyAsset writes. Canonical events remain
Python-owned and read-only in Spring. Flyway V1-V3 initializes PostgreSQL/PostGIS;
neither runtime writes generated geography columns.

See the [acceptance checklist](phase-2-checklist.md) and
[visual overview](phase-2-overview.md), which separates actual UI from concept art.

## Events

- `GET /api/events?limit=100&eventType=FLOOD&severity=HIGH&country=Türkiye`
- `GET /api/events/{id}`

The collection is a JSON array ordered by `occurredAt DESC, id DESC`. The optional
filters combine with AND; enums are case-sensitive, and country matches exact
provider text without trimming. Country can be null on events. There is no
pagination in Phase 2: each collection request returns a bounded recent subset.

The response contains `id`, `source`, `sourceEventId`, `eventType`, `occurredAt`
(UTC ISO 8601), `latitude`, `longitude`, `severity`, `country`, `metadata` (JSON
object), and `schemaVersion`. Internal geography is excluded. Supported event
types are EARTHQUAKE, FLOOD, CONFLICT, PROTEST and STRIKE; severities are LOW,
MEDIUM, HIGH and CRITICAL. The GDACS adapter currently normalizes earthquakes
and floods only; the canonical taxonomy and database support all five types.

## Nearby events

`GET /api/supply-assets/{id}/nearby-events?radiusKm=100&limit=100`

Only active assets support operational nearby lookup. Missing and inactive
assets return 404; inactive responses explain that an active asset was not found.
CRUD/admin get and list still include inactive assets. DELETE deactivates an asset
and preserves its row, and PUT does not reactivate it.

The response is an array of `{ "event": <event response>, "distanceMeters": <number> }`.
Distance is spheroidal geography distance in meters. Radius input is kilometers
and is explicitly multiplied by 1000. Radius inclusion uses `ST_DWithin` on
`event.location` and `supply_asset.location`, including the boundary. Results are
ordered by distance ascending, then occurrence time descending and id descending.

| Setting | Environment variable | Default | Validation |
|---|---|---|---|
| Collection/nearby default limit | `EVENT_DEFAULT_LIMIT` | 100 | Positive, no greater than maximum |
| Collection/nearby maximum limit | `EVENT_MAX_LIMIT` | 500 | Positive |
| Default radius in km | `EVENT_DEFAULT_RADIUS_KM` | 100 | Positive, finite, no greater than maximum |
| Maximum radius in km | `EVENT_MAX_RADIUS_KM` | 1000 | Positive, finite |

Omitting limit/radius uses the configured default. Invalid ids, limits, radii,
filters, enum values and malformed request bodies return 400. Missing ids return
404. One shared error handler returns `timestamp`, `status`, `error`, `message`
and `path`, preserving the existing SupplyAsset error format.

## Frontend

The Next.js dashboard loads all supply assets and the latest 100 events, and retrieves up to
100 closest events for the selected asset. Nearby results outside the latest
event subset are also shown on the map. The demo radius form supports up to
1000 km; backend validation remains authoritative if deployment limits differ.
Suppliers and ports use distinct letter markers; events use severity colors and
show their type. Inactive assets appear faded and cannot perform nearby lookup.

Leaflet is imported after client mount, with a client-only Next component.
Leaflet point arguments use `[latitude, longitude]`; GeoJSON and database point
construction use `[longitude, latitude]`. Tooltips use text nodes to preserve
provider text safely. Tiles use OpenStreetMap with visible attribution and no
token, following its [tile usage policy](https://operations.osmfoundation.org/policies/tiles/).
Tile failure leaves the lists usable. This is a development/demo map.

The browser uses same-origin `/api/...` GET routes. The server proxies only the
documented read paths to `BACKEND_URL` (host default `http://localhost:8080`,
Compose `http://backend:8080`), with a 10-second upstream timeout and no caching.
Set host frontend variables in `frontend/.env.local` or the process environment;
Next does not automatically load the repository-root `.env`.

## Repeatable verification

Build the backend and frontend, then from the repository root:

```powershell
./scripts/phase2-smoke.ps1 -RunTests
```

The script uses the project Python 3.12 venv, creates a disposable PostGIS 16/3.5
container with a dynamically published host port, starts the backend jar and
production Next server on free ports, and cleans up only the resources it creates.
Flyway initializes this database through Spring. It does not touch the existing
Windows PostgreSQL service or the existing Compose database. Live GDACS ingestion
runs through Bronze and CLI normalization/persistence, followed by deterministic
Python-owned fixtures for distance checks. `-SkipLiveSource` permits offline
fixture verification and is explicitly distinct from live integration acceptance.

`-RunTests` also runs the full Python suite against the disposable database using
a fresh short Temp path to avoid Windows ACL reuse and native Parquet path limits. Java
PostGIS integration tests run with `mvn verify -Ppostgis` using Testcontainers;
`mvn test` covers domain and application tests. Docker image builds run the unit
suite; the integration profile runs outside the build where Docker is available.

The smoke inserts 50,000 globally distributed disposable canonical events through
Python and runs ANALYZE. It extracts the exact nearby SELECT from
`JdbcEventRepository`, then runs `EXPLAIN (ANALYZE, BUFFERS)` without planner
overrides and asserts `idx_event_location_gist` and an index condition appear.
The full plan is saved in ignored `.smoke/nearby-explain.txt`. Retained acceptance
evidence is in [phase-2-verification.md](phase-2-verification.md).

For container acceptance, run `./scripts/phase2-compose-smoke.ps1`. This builds
and starts a separate disposable Compose project with dynamically published
ports, checks all three services are healthy, verifies Flyway and PostGIS, and
removes that project's containers and volume. It disables optional Compose Bake
only within the script because the local Windows Bake path can fail with a
closed-pipe error. Existing Compose services and data are preserved.

`-RunSmoke` additionally runs the live-source/full-chain smoke against these
containers. `-HoldForBrowser` adds explicitly named disposable demo assets and
holds the stack for up to five minutes for manual browser verification; creating
`.smoke/compose-browser-check.done` ends the hold early. It never touches existing
project data. Use both switches to reproduce the actual dashboard capture.

Repository PostgreSQL defaults remain 5432. If a host service occupies it, set
`POSTGRES_PORT` locally for Compose. Smoke tooling obtains the actual Docker
binding from `docker inspect`, including dynamically allocated ports.
