# ADR-0006 — Single Flyway Migration Authority

- **Status:** Accepted
- **Date:** 2026-09-17
- **Supersedes:** ADR-0003 migration-ownership decision only

## Context

ChainSignal V1 uses one shared PostgreSQL/PostGIS database instance.

ADR-0003 established explicit business-data ownership:

- Python owns canonical event and pipeline data writes.
- Spring Boot owns SupplyAsset, RiskSnapshot, RiskReason and Alert data writes.

ADR-0003 also assigned schema migrations according to those table owners.

Phase 2 introduces the first real operational database schema shared by Python and Spring Boot. Allowing Python and Spring Boot to maintain independent migration histories against one physical database would create ambiguous ordering, startup dependencies and schema-version ownership.

Business-data ownership and physical-schema migration authority are separate concerns.

## Decision

Use Flyway as the single authority for operational PostgreSQL/PostGIS schema migrations.

Flyway migrations live at:

`backend/src/main/resources/db/migration`

Spring Boot executes Flyway migrations during application startup.

The Python data pipeline does not independently create or migrate operational database tables.

PostgreSQL container initialization scripts do not independently create application schema objects.

This decision changes schema migration authority only.

It does not change business-data ownership.

## Data Ownership After This Decision

Python remains the only business-data writer for pipeline-owned canonical event data.

Spring Boot remains read-only for canonical event business data.

Spring Boot remains the business-data writer for backend-owned SupplyAsset, RiskSnapshot, RiskReason and Alert data.

## Rationale

A single migration history provides:

- deterministic migration ordering,
- one database schema version history,
- one place to review cross-language persistence changes,
- explicit PostGIS extension lifecycle,
- simpler local startup behavior,
- reduced risk of independent schema mutation.

This is especially important because Spring Boot reads a persistence contract written by Python.

## Alternatives Rejected

### Independent Python and Spring migration histories

Rejected because both would mutate one physical PostgreSQL/PostGIS schema while maintaining separate ordering and lifecycle rules.

### PostgreSQL container initialization as schema authority

Rejected because `/docker-entrypoint-initdb.d` runs as database bootstrap behavior rather than as a versioned application migration lifecycle.

It also does not naturally evolve an already-initialized persistent database volume.

### Dedicated standalone migration service

Rejected for V1 because it would add another runtime component without providing enough value beyond Flyway.

## Consequences

Positive:

- one migration authority,
- one ordered schema history,
- explicit compatibility boundary,
- easier schema review,
- simpler local operations.

Negative:

- Flyway migrations are physically packaged with the Spring Boot application even for Python-owned event tables,
- the backend repository contains schema definitions for data it must not mutate at the business level,
- schema changes to the event table require coordination with Python persistence code.

These consequences are accepted because schema authority does not imply business-data ownership.
