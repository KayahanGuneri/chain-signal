# ADR-0004 — Batch First, Streaming Later

- **Status:** Accepted
- **Date:** 2026-09-13

## Context

Kafka and Go are familiar/useful technologies, but the core product hypothesis can be proven without streaming. Introducing them before ingestion, canonical data, geospatial matching, risk explainability and alert lifecycle are stable would increase complexity without validating more product value.

## Decision

Build and stabilize the batch/data/risk path first. Kafka and the Go replay service remain a gated Phase 6 extension.

If Phase 0-5 acceptance is not stable, Phase 6 time is used to harden the core instead of forcing streaming into the project.

Any future streaming path must reuse the same canonical Event semantics and Java RiskEngine concepts rather than creating parallel business logic.

## Rationale

The simplest architecture that proves the core product should come first. Streaming should solve a demonstrated replay/latency problem, not serve as a portfolio decoration.

## Alternatives rejected

- Kafka from day one: rejected as premature infrastructure and failure-mode complexity.
- Separate streaming-specific risk model: rejected because it would duplicate business logic.

## Consequences

Positive:

- faster validation of core product behavior
- fewer moving parts during early learning
- reusable contracts make later streaming safer

Negative:

- real-time behavior is intentionally deferred
- later streaming integration still requires explicit idempotency and replay design
