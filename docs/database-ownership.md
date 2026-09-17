# Database Ownership

## Purpose

ChainSignal V1 uses one shared PostgreSQL/PostGIS instance while preserving explicit data-write and lifecycle ownership between the Python data pipeline and the Spring Boot control plane.

A shared database does not imply shared write ownership.

Database schema migrations have one authority: Flyway migrations shipped with the Spring Boot backend.

## Migration Authority

All operational PostgreSQL/PostGIS schema changes are managed through Flyway.

Migration location:

`backend/src/main/resources/db/migration`

Neither the Python data pipeline nor PostgreSQL container initialization scripts independently create or evolve application tables.

This is intentionally separate from data ownership.

Schema authority answers:

> Who changes the physical database schema?

Data ownership answers:

> Which application is allowed to create or modify business data in a table?

These are different responsibilities.

## Ownership Matrix

| Data / Table | Data Write Owner | Other Access | Schema Authority |
|---|---|---|---|
| `event` | Python data pipeline | Spring Boot read-only | Flyway |
| `supply_asset` | Spring Boot | Spring Boot read/write | Flyway |
| future `risk_snapshot` | Spring Boot | Spring Boot read/write | Flyway |
| future `alert` | Spring Boot | Spring Boot read/write | Flyway |
| Bronze / normalized filesystem artifacts | Python data pipeline | no direct Spring mutation | not applicable |

## Canonical Event Ownership

The `event` table is pipeline-owned business data.

Python is responsible for:

- canonical normalization,
- canonical event validation,
- event persistence,
- duplicate-safe writes,
- event update semantics,
- schema-version compatibility before persistence.

Spring Boot is allowed to:

- read canonical events,
- filter and paginate canonical events,
- use canonical events for geospatial matching,
- expose canonical event data through application APIs.

Spring Boot must not:

- reinterpret GDACS-specific semantics,
- create canonical events,
- modify canonical event business fields,
- delete canonical events as part of ordinary application behavior.

Canonical event identity remains:

`(source, sourceEventId)`

The relational representation uses:

`(source, source_event_id)`

as its unique business key.

The database-generated `id` is an internal persistence identifier and does not replace canonical event identity.

## SupplyAsset Ownership

The `supply_asset` table is backend-owned business data.

Spring Boot owns:

- Supplier and Port creation,
- updates,
- validation,
- criticality,
- activation state,
- soft deactivation,
- persistence lifecycle.

The Python data pipeline must not write SupplyAsset business data.

## Geospatial Representation

Canonical events and SupplyAssets persist latitude and longitude as explicit business-visible coordinates.

PostgreSQL derives:

`geography(Point, 4326)`

from longitude and latitude using a stored generated column.

The generated geography value is used for PostGIS spatial predicates and distance calculations.

Application writers do not independently provide the generated location value.

This prevents latitude/longitude and the spatial Point from drifting apart.

## Migration Lifecycle

The migration sequence begins with:

1. `V1__enable_postgis.sql`
2. `V2__create_event_table.sql`
3. `V3__create_supply_asset_table.sql`

Future schema changes must be introduced through new forward-only Flyway migrations.

Existing applied migrations must not be edited after they become part of a shared development history.

## Cross-Language Contract

The Java-readable event persistence shape is a version-aware cross-language contract.

Python writes the canonical representation.

Spring Boot reads the documented representation without applying provider-specific interpretation.

Canonical Event v1 fields remain:

- `source`
- `sourceEventId`
- `eventType`
- `occurredAt`
- `latitude`
- `longitude`
- `severity`
- `country`
- `metadata`
- `schemaVersion`

Database naming uses snake_case where appropriate.

A breaking change to this persistence contract requires explicit versioning and compatibility handling.

## Failure Policy

Schema incompatibility must fail fast.

Python must not silently write a canonical schema version that the database persistence contract does not support.

Spring Boot must not silently reinterpret an unsupported canonical schema version.

Compatibility failures should be visible operational failures rather than implicit coercion.

## Transaction Boundary

Pipeline database writes use one transaction per logical persistence batch.

A successful batch commits as one unit.

A failed batch rolls back as one unit.

Individual commits per event are intentionally avoided because they can expose partially persisted ingestion batches and add unnecessary transaction overhead.

The concrete bulk upsert implementation is defined by the Python persistence writer.

## Architecture Evolution

Phase 0 originally assigned migration ownership according to table/data ownership:

- Python migrations for Python-owned tables.
- Spring Boot migrations for backend-owned tables.

Phase 2 replaces that migration model with a single Flyway schema authority.

The reason is to prevent independent migration histories from mutating one shared PostgreSQL/PostGIS schema.

This changes schema authority only.

It does not change business data ownership.
