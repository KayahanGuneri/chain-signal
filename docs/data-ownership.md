# ChainSignal — Data Ownership Matrix

Business-data ownership means responsibility for writes and lifecycle semantics. Schema migration authority is managed separately through Flyway. Read access does not imply write ownership.

| Data | Owner | Python | Spring Boot |
|---|---|---:|---:|
| Raw ingestion metadata / Bronze references | Python | RW | - |
| Canonical Events | Python | RW | R |
| Quarantine / data-quality records | Python | RW | - |
| Statistical Anomalies | Python | RW | R |
| ML Anomalies | Python | RW | R |
| Supply Assets | Spring Boot | optional R | RW |
| Risk Snapshots | Spring Boot | optional R | RW |
| Risk Reasons | Spring Boot | - | RW |
| Alerts | Spring Boot | - | RW |

## Rules

1. Flyway is the single authority for operational PostgreSQL/PostGIS schema migrations.
2. Business-data ownership is independent from schema migration authority.
3. Python owns canonical Event business-data writes.
4. Spring Boot must never insert/update/delete canonical event rows as part of normal application behavior.
5. Spring Boot owns SupplyAsset, RiskSnapshot, RiskReason and Alert business-data writes.
6. Python must never own RiskSnapshot or Alert writes.
7. Java must not reinterpret source-specific normalization rules.
8. Shared PostgreSQL/PostGIS is a V1 simplification, not permission for shared write ownership.
9. The Java-readable canonical event persistence shape is a documented cross-language contract.
