# ADR-0001 — Service and Language Responsibilities

- **Status:** Accepted
- **Date:** 2026-09-13

## Context

ChainSignal is intentionally polyglot for learning and architectural fit, but duplicated business responsibility across Python, Java and Go would make the system inconsistent and difficult to explain.

## Decision

- Python owns ingestion, raw/Bronze preservation, validation, canonical normalization, data quality, statistical baselines, StatisticalAnomaly and MLAnomaly.
- Java/Spring Boot owns SupplyAsset lifecycle, geospatial risk orchestration, deterministic RiskEngine, RiskSnapshot, Alert lifecycle and public application APIs.
- Go is deferred to the gated replay/streaming phase and owns only historical replay / Kafka production concerns.
- Next.js/TypeScript owns presentation and operational interaction.
- PostgreSQL/PostGIS provides local persistence and spatial querying.

## Rationale

The split aligns each technology with a real workload while preventing technology-count-driven duplication.

## Alternatives rejected

- Implement everything in Java: simpler stack, but removes the intended real data/statistics/ML learning boundary.
- Implement risk rules in both Python and Java: rejected because deterministic business truth would diverge.
- Use Go from Phase 0: rejected because there is no current replay/streaming requirement.

## Consequences

Positive:

- clear ownership
- explainable boundaries
- no duplicated normalization or risk rules

Negative:

- cross-language data contract must be documented and version-aware
- local toolchain includes multiple languages even before all are actively implemented
