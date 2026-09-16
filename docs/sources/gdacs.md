# GDACS Source Contract

## Purpose

GDACS is the first external disaster source used by the ChainSignal data pipeline.

Phase 1 supports the following GDACS event types:

| GDACS event type | ChainSignal event type |
| ---------------- | ---------------------- |
| `EQ`             | `EARTHQUAKE`           |
| `FL`             | `FLOOD`                |

Other GDACS event types are intentionally outside the Phase 1 scope.

## API

Discovery uses the GDACS SEARCH endpoint:

`https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH`

The response is GeoJSON with a top-level `FeatureCollection`.

Each feature contains provider properties and GeoJSON geometry.

## Query Contract

Phase 1 requests the following alert levels explicitly:

`Green;Orange;Red`

The provider must not be queried with an implicit alert-level default.

The SEARCH API returns a maximum of 100 records per response. Requests that may exceed this limit must use pagination through `pagenumber` and `pagesize`.

Observed discovery queries returned events whose `fromdate` predates the requested search start date. Therefore the request `fromdate` must not be interpreted as a guaranteed lower bound for the event's actual start time.

## Pagination

Discovery verified multi-page responses using a page size of 100.

A one-week discovery window returned 116 combined events.

The ingestion adapter must support pagination and must stop when a page contains fewer records than the requested page size.

The adapter must also protect against repeated-page responses so a provider pagination failure cannot silently create an infinite loop or duplicate collection.

## Event Identity

The GDACS event-level identity is represented using:

`{eventtype}:{eventid}`

Examples:

`EQ:1566315`

`FL:1103888`

ChainSignal canonical identity is therefore:

`(source, sourceEventId)`

where:

`source = GDACS`

and:

`sourceEventId = {eventtype}:{eventid}`

`episodeid` is not part of the canonical event identity.

GDACS uses `episodeid` for episode/sublevel resources such as event geometry and reports, while event-level detail resources use `eventtype` and `eventid`.

`episodeid` is retained as provider metadata.

## Canonical Mapping Draft

| GDACS value               | Canonical Event v1     | Decision           |
| ------------------------- | ---------------------- | ------------------ |
| constant `GDACS`          | `source`               | Required           |
| `{eventtype}:{eventid}`   | `sourceEventId`        | Required           |
| `EQ`                      | `eventType=EARTHQUAKE` | Required           |
| `FL`                      | `eventType=FLOOD`      | Required           |
| `fromdate`                | `occurredAt`           | Required           |
| `geometry.coordinates[1]` | `latitude`             | Required           |
| `geometry.coordinates[0]` | `longitude`            | Required           |
| `alertlevel`              | `severity`             | Normalize          |
| `country`                 | `country`              | Nullable           |
| selected provider fields  | `metadata`             | Supplementary      |
| complete feature          | Bronze                 | Preserve unchanged |

## Occurrence Time

`fromdate` represents the event occurrence/start time used by ChainSignal.

For earthquakes, discovery showed `fromdate` and `todate` representing the same event instant.

For floods, `fromdate` and `todate` represent an event interval.

GDACS event resource pages present event times as UTC. The API values observed during discovery do not include an explicit timezone offset.

Normalization must therefore interpret valid GDACS event timestamps using GDACS UTC semantics and produce timezone-aware canonical timestamps.

`datemodified` must never replace `fromdate` as the canonical occurrence time.

The ingestion timestamp must never replace a missing or invalid provider occurrence time.

A missing or invalid `fromdate` is a data-quality failure and must result in quarantine during canonical normalization.

## Geometry

Discovery observations used GeoJSON `Point` geometry.

GeoJSON coordinate order is:

`[longitude, latitude]`

Canonical mapping is therefore:

`longitude = coordinates[0]`

`latitude = coordinates[1]`

Normalization must validate coordinate structure and range.

Invalid or missing coordinates are preserved in Bronze but must not produce a canonical Event v1 record.

They must be quarantined with an explicit data-quality reason.

## Severity

GDACS exposes the alert levels:

`Green`

`Orange`

`Red`

The Phase 1 normalization draft is:

| GDACS    | Canonical |
| -------- | --------- |
| `Green`  | `LOW`     |
| `Orange` | `MEDIUM`  |
| `Red`    | `HIGH`    |

`CRITICAL` is not synthesized from GDACS in Phase 1.

The original `alertlevel`, `alertscore`, `episodealertlevel`, and `episodealertscore` values must remain available in metadata or Bronze for traceability.

This mapping is source-specific and belongs to Python normalization rather than the Java backend.

## Country

GDACS exposes `country`, `iso3`, and `affectedcountries`.

Discovery showed that these fields are not universally populated.

The canonical `country` value therefore remains nullable.

Phase 1 does not perform reverse geocoding.

A missing country must not cause an otherwise valid event to be quarantined.

Provider country-related fields remain available in Bronze and selected metadata.

## Provider Metadata

The GDACS property named `source` describes an upstream provider such as `NEIC` or `GLOFAS`.

It must not replace the ChainSignal canonical source.

Canonical:

`source = GDACS`

Provider metadata may include fields such as:

`episodeid`, upstream `source`, `alertscore`, `episodealertlevel`, `episodealertscore`, `severitydata`, `iso3`, `affectedcountries`, `iscurrent`, and `istemporary`.

The complete original GDACS feature remains in Bronze.

## Data Quality Observations

The final Day 2 discovery dataset contained 116 events.

Observed event distribution:

| Event type | Count |
| ---------- | ----: |
| `EQ`       |    91 |
| `FL`       |    25 |

Observed upstream source distribution:

| Source   | Count |
| -------- | ----: |
| `NEIC`   |    91 |
| `GLOFAS` |    25 |

No exact duplicates, duplicate event identities, or duplicate episode identities were observed in the final discovery dataset.

Blank strings were observed separately from null values.

Notably, `eventname` and `sourceid` were blank throughout the sample, while `country` and `iso3` were missing for some events.

Blank strings must therefore not be treated as equivalent to valid populated source data merely because Pandas does not report them as null.

## HTTP Reliability

During discovery, repeated paginated calls eventually encountered an HTTP-level failure before a response status was received.

The production GDACS adapter therefore requires bounded retry behavior.

Phase 1 retry behavior will apply to transient failures such as connection failures, timeouts, HTTP 429 responses, and HTTP 5xx responses.

Retries must be bounded and must not hide permanent provider or payload errors.

## Bronze Boundary

Bronze storage preserves the source-oriented GDACS representation and ingestion metadata.

Bronze does not contain canonical Event fields produced by normalization.

The responsibility boundary is:

`ingestion preserves data`

`normalization interprets data`

Raw provider records must remain reproducible even if future normalization rules change.

## Attribution

GDACS data usage must acknowledge the source as:

`Global Disaster Awareness and Coordination System, GDACS`

The project must continue to follow the current GDACS terms of use when source integration evolves.
