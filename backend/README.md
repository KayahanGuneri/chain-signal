# ChainSignal Backend

Spring Boot SupplyAsset lifecycle, read-only Event API and PostGIS orchestration.

Phase 2 provides SupplyAsset CRUD, bounded Event reads and active-asset nearby
lookup. RiskEngine, RiskSnapshot and Alert behavior remain future work. See
[the API contract](../docs/phase-2-api.md).

## Dependency management

- Java 21
- Spring Boot 4.1.1
- Maven

## Local build

```text
mvn clean verify
```

The integrated project workflow is Docker-first from the repository root.
