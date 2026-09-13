# ChainSignal — Phase 0 Checklist

A checkbox is complete only when the underlying artifact or runtime behavior has been verified.

## Product definition

- [x] Primary user defined: manufacturer/importer supply-chain operations / risk team
- [x] Main operational decision defined
- [x] Product explicitly defined as decision support, not news aggregation
- [x] Five end-to-end V1 use cases documented
- [x] V1 assets limited to Supplier and Port
- [x] V1 event taxonomy limited to Earthquake, Flood, Conflict, Protest and Strike
- [x] V1 admission test documented
- [x] Explicit non-goals/backlog documented

## Domain and data contracts

- [x] SupplyAsset semantics documented
- [x] Event semantics documented
- [x] RiskSnapshot semantics documented
- [x] RiskReason explainability documented
- [x] Alert lifecycle documented
- [x] StatisticalAnomaly separated from operational risk
- [x] MLAnomaly separated from operational risk
- [x] Canonical Event v1 draft documented
- [x] Event and severity taxonomy documented
- [x] Canonical identity `(source, sourceEventId)` documented
- [x] Quarantine rules documented
- [x] Schema/version strategy documented

## Architecture

- [x] Python responsibility documented
- [x] Spring Boot responsibility documented
- [x] Go responsibility documented and Phase 6 gated
- [x] Frontend responsibility documented
- [x] PostgreSQL/PostGIS responsibility documented
- [x] Table/data ownership matrix documented
- [x] Cross-language canonical schema contract documented
- [x] Batch-first / streaming-later decision documented
- [x] Docker-first local runtime decision documented
- [x] Data-flow diagram draft created
- [x] Domain diagram draft created
- [x] No duplicate business responsibility across Python/Java/Go

## ADRs

- [x] ADR-0001 service/language responsibilities
- [x] ADR-0002 canonical Event model
- [x] ADR-0003 database ownership
- [x] ADR-0004 batch-first before streaming
- [x] ADR-0005 Docker-first local runtime

## Repository / toolchain skeleton

- [x] `/backend` contains independent Java/Maven project skeleton
- [x] `/data-pipeline` contains independent Python project skeleton
- [x] `/frontend` contains independent Next.js/TypeScript project skeleton
- [x] `/replay-service` contains independent Go module skeleton
- [x] `/infra` exists for infrastructure details
- [x] `/docs` contains product/domain/architecture contracts
- [x] Java 21 / Spring Boot version documented
- [x] Python version documented
- [x] Node / Next.js / TypeScript versions documented
- [x] Go version documented
- [x] `.env.example` exists
- [x] `.env` is ignored
- [x] No required paid runtime service
- [x] Root-level `compose.yml` is the single integrated local runtime entrypoint

## Build / runtime verification

- [x] Docker Compose configuration validates
- [x] PostgreSQL/PostGIS image builds/starts
- [x] PostgreSQL reports healthy
- [x] `SELECT PostGIS_Version();` succeeds
- [x] Spring Boot Maven build/tests pass in Docker
- [x] Spring Boot container reports healthy
- [x] Spring Boot actuator health is reachable
- [x] Next.js TypeScript check/build passes in Docker
- [x] Next.js container reports healthy
- [x] Next.js skeleton page is reachable
- [x] Python package tests pass during Docker build and explicit container test execution
- [x] Python batch skeleton runs on demand
- [x] Go tests/build pass during Docker build
- [x] Go replay skeleton runs on demand without Kafka
- [x] Default runtime starts with `docker compose up -d --build`
- [x] Clean GitHub clone reproduces the full verified runtime

## Git / phase closeout

- [x] `git status` reviewed
- [x] Phase 0 files committed
- [x] GitHub remote configured
- [x] Branch pushed
- [x] Phase 0 acceptance reviewed line by line
- [x] Learning summary produced
- [x] PHASE_HANDOFF produced

## Phase 0 status

**PASS — Phase 0 acceptance is complete.**

Phase 1 may begin only from this documented contract. Any intentional contract change should be reviewed explicitly rather than introduced silently.