# ADR-0005 — Docker-First Local Runtime

- **Status:** Accepted
- **Date:** 2026-09-13

## Context

ChainSignal is a polyglot monorepo containing Java, Python, TypeScript and Go workloads plus PostgreSQL/PostGIS. Requiring a developer to manually install and start each application runtime independently would weaken local reproducibility and increase setup drift.

Phase 0 prioritizes a repeatable local environment over early CI/cloud infrastructure.

## Decision

Docker Compose is the single integrated local runtime entrypoint.

The repository-root `compose.yml` owns the developer-facing stack.

Default runtime:

- PostgreSQL/PostGIS
- Spring Boot backend
- Next.js frontend

On-demand profiles/workloads:

- Python data pipeline via the `batch` profile
- Go replay-service skeleton via the `streaming` profile
- Kafka remains deferred until the Phase 6 streaming gate is explicitly opened

Each subproject retains its native dependency manifest and can still be built/tested independently.

## Rationale

This gives the project one reproducible bootstrap path without erasing language/service boundaries.

Docker is solving local-environment consistency; it is not being used to justify Kubernetes, cloud deployment or premature microservice infrastructure.

## Alternatives rejected

- Manually start Java, Node, Python and Go processes: rejected as the normal integrated workflow because it creates environment drift and repetitive setup.
- Add Kubernetes: rejected as unnecessary orchestration complexity.
- Add Kafka now: rejected by the batch-first architecture decision.

## Consequences

Positive:

- clean clone can be validated with a small number of commands
- runtime dependencies are explicit
- developers do not need every language toolchain installed on the host for the integrated stack
- service health/dependency ordering is visible

Negative:

- Docker Desktop / Docker Engine becomes a local-development prerequisite
- image builds take longer than running some processes directly
- hot-reload development workflows may require later Compose overrides or bind mounts