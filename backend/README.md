# ChainSignal Backend

Spring Boot control-plane / deterministic risk-domain skeleton.

Phase 0 contains bootstrap/runtime code only. Business capabilities such as SupplyAsset lifecycle, RiskEngine, RiskSnapshot and Alert behavior are implemented in later phases.

## Dependency management

- Java 21
- Spring Boot 4.1.1
- Maven

## Local build

```text
mvn clean verify
```

The integrated project workflow is Docker-first from the repository root.