# ADR-0003 — Shared Database with Explicit Ownership

- **Status:** Accepted
- **Date:** 2026-09-13

## Context

V1 runs locally and does not require the operational complexity of independent databases or an extra Python HTTP service. However, a shared PostgreSQL/PostGIS instance can easily become an uncontrolled shared-write database.

## Decision

Use one local PostgreSQL/PostGIS instance with explicit ownership:

- Python owns writes/migrations for event/pipeline/anomaly data.
- Spring Boot owns writes/migrations for SupplyAsset, RiskSnapshot, RiskReason and Alert data.
- Spring Boot may read the documented canonical event persistence contract directly.
- Spring Boot must not write Python-owned canonical event data.
- Python must not write backend-owned risk/alert lifecycle data.

The Java-readable canonical event shape is a version-aware cross-language contract.

## Rationale

This keeps V1 operationally simple while preserving a meaningful ownership boundary.

## Alternatives rejected

- Python REST API between Java and the database: rejected for V1 because it adds service lifecycle, HTTP contracts, retries/timeouts and failure modes without a current independent deployment/scaling need.
- Database per service: rejected as premature operational complexity for the local-first V1.
- Unrestricted shared writes: rejected because ownership and migrations would become ambiguous.

## Consequences

Positive:

- simple local runtime
- explicit ownership
- easy PostGIS access for risk-domain queries

Negative:

- deliberate database-level coupling
- schema compatibility discipline is required for Java-readable Python-owned tables
