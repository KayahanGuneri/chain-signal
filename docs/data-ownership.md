# ChainSignal — Data Ownership Matrix

Ownership means responsibility for writes, lifecycle semantics and schema/migrations. Read access does not imply ownership.

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

1. Python owns migrations for Python-owned tables.
2. Spring Boot owns migrations for backend-owned tables.
3. Spring Boot must never insert/update/delete canonical event rows.
4. Python must never own RiskSnapshot or Alert writes.
5. Java must not reinterpret source-specific normalization rules.
6. Shared PostgreSQL/PostGIS is a V1 simplification, not permission for shared write ownership.
7. The Java-readable canonical event persistence shape is a documented cross-language contract.
