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
- [x] Alert lifecycle documented
- [x] StatisticalAnomaly separated from operational risk
- [x] MLAnomaly separated from operational risk
- [x] Canonical Event v1 draft documented
- [x] Event and severity taxonomy documented
- [x] Canonical identity `(source, sourceEventId)` documented
- [x] Quarantine rules documented

## Architecture

- [x] Python responsibility documented
- [x] Spring Boot responsibility documented
- [x] Go responsibility documented and Phase 6 gated
- [x] Frontend responsibility documented
- [x] PostgreSQL/PostGIS responsibility documented
- [x] Table/data ownership matrix documented
- [x] Cross-language canonical schema contract documented
- [x] Batch-first / streaming-later decision documented
- [x] Data-flow diagram draft created
- [x] Domain diagram draft created

## ADRs

- [x] ADR-0001 service/language responsibilities
- [x] ADR-0002 canonical Event model
- [x] ADR-0003 database ownership
- [x] ADR-0004 batch-first before streaming

## Repository / runtime skeleton

- [x] `/backend`
- [x] `/data-pipeline`
- [x] `/frontend`
- [x] `/replay-service`
- [x] `/infra`
- [x] `/docs`
- [x] `.env.example`
- [x] `.gitignore`
- [x] Docker Compose PostgreSQL/PostGIS skeleton
- [x] PostgreSQL healthcheck configured
- [ ] `.env` copied locally from `.env.example`
- [ ] Docker Compose starts successfully on developer machine
- [ ] PostgreSQL reports healthy
- [ ] `SELECT PostGIS_Version();` succeeds
- [ ] Clean-clone bootstrap instructions verified manually

## Git / phase closeout

- [ ] `git status` reviewed
- [ ] Phase 0 files committed
- [ ] GitHub remote configured
- [ ] Branch pushed
- [ ] Phase 0 acceptance reviewed line by line
- [ ] Learning summary produced
- [ ] PHASE_HANDOFF produced
