# Phase 0 Learning Summary

After Phase 0, the developer should be able to explain:

1. Why ChainSignal is an operational decision-support product rather than a news aggregator.
2. How a business problem is decomposed into bounded capabilities before implementation.
3. Why `SupplyAsset`, `Event`, `RiskSnapshot`, `RiskReason`, `Alert`, `StatisticalAnomaly` and `MLAnomaly` have different semantics.
4. Why domain models, canonical data models, persistence models and API models are not interchangeable.
5. Why `(source, sourceEventId)` is the external canonical event identity and how it supports idempotency.
6. Why unsupported or incomplete source records are quarantined instead of silently coerced.
7. Why Python owns ingestion/normalization/anomaly work while Java owns deterministic operational risk and alert lifecycle.
8. Why a shared PostgreSQL/PostGIS instance does not imply shared write ownership.
9. Why the project starts batch-first and keeps Kafka/Go streaming gated until it solves a demonstrated problem.
10. Why Docker Compose is used as the single integrated local runtime while every subproject still retains independent dependency management.
11. How healthchecks, clean-clone verification and immutable/documented contracts improve local reproducibility.
12. Why a buildable project skeleton is valuable even when business features are intentionally not implemented yet.