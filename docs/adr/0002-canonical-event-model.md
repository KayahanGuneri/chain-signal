# ADR-0002 — Canonical Event Model

- **Status:** Accepted
- **Date:** 2026-09-13

## Context

External disruption sources use heterogeneous field names, identifiers, timestamps, categories and severity concepts. Allowing provider schemas to leak into the risk domain would couple Spring Boot and the frontend to source-specific behavior.

## Decision

Python normalizes supported records into a versioned CanonicalEvent v1 contract with at least:

- source
- sourceEventId
- eventType
- occurredAt
- latitude
- longitude
- severity
- country
- metadata
- schemaVersion

External identity is `(source, sourceEventId)`.

Unknown event types, missing required geospatial coordinates or missing reliable occurrence time are preserved in raw/Bronze storage but quarantined from canonical risk processing.

Complete provider payloads remain in raw/Bronze storage; canonical metadata contains only selected supplementary fields.

## Rationale

This gives every downstream component one stable event language while preserving source fidelity for reprocessing.

## Alternatives rejected

- Use provider payloads directly: rejected because downstream services would become provider-aware.
- Map unknown categories to `OTHER`: rejected because it weakens the controlled taxonomy and hides unsupported semantics.
- Substitute publication time for unknown occurrence time: rejected because it fabricates temporal meaning.

## Consequences

Positive:

- simpler downstream contracts
- easier multi-source expansion
- explicit validation/quarantine boundary

Negative:

- normalization logic must be maintained carefully
- schema/taxonomy evolution requires compatibility discipline
