# ChainSignal — Canonical Event Contract

## Purpose

The canonical Event contract isolates the rest of the system from source-specific schemas. Python source adapters and normalizers translate supported public-source records into this contract.

## CanonicalEvent v1

| Field | Required | Meaning |
|---|---|---|
| `source` | yes | Stable external source identifier |
| `sourceEventId` | yes | Event identifier within that source |
| `eventType` | yes | Controlled ChainSignal EventType |
| `occurredAt` | yes | Best supported real-world occurrence time |
| `latitude` | yes | Point latitude |
| `longitude` | yes | Point longitude |
| `severity` | yes | `LOW`, `MEDIUM`, `HIGH`, or `CRITICAL` |
| `country` | yes | ISO 3166-1 alpha-2 country code |
| `metadata` | no | Selected supplementary normalized/source-specific fields |
| `schemaVersion` | yes | Canonical schema version |

## External identity and idempotency key

The source identity is the tuple:

```text
(source, sourceEventId)
```

`sourceEventId` is not assumed to be globally unique across providers.

## Validation rules

- unknown V1 event type -> quarantine, not `OTHER`
- missing latitude/longitude -> retained in raw/Bronze but rejected from canonical risk processing in V1
- missing reliable `occurredAt` -> do not invent it from a publication timestamp; quarantine the record
- complete provider payload -> raw/Bronze storage, not canonical `metadata`
- `metadata` -> only selected supplementary fields needed after normalization

## Temporal distinction

Do not conflate:

- event occurrence time
- provider publication/reporting time
- pipeline ingestion time

`occurredAt` is part of the canonical business event contract. Pipeline ingestion timestamps belong to pipeline operational metadata unless a later design decision promotes them into another documented contract.

## Location simplification

V1 canonical geospatial matching uses point coordinates. Area geometries (polygon/multipolygon) for floods, conflicts or other disruptions are intentionally deferred until the point-based core is proven.
