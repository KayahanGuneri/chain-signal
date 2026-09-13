# ChainSignal — V1 Scope

## In scope

### Tracked assets

- `SUPPLIER`
- `PORT`

### Supported event taxonomy

- `EARTHQUAKE`
- `FLOOD`
- `CONFLICT`
- `PROTEST`
- `STRIKE`

### Core capabilities

- ingest real public disruption data
- preserve raw data for reprocessing
- validate and quarantine invalid/unsupported records
- normalize supported data into a canonical Event contract
- persist canonical events in PostgreSQL/PostGIS
- manage Supplier and Port assets
- geospatially match events to assets
- calculate deterministic, explainable operational risk
- persist immutable RiskSnapshot history and reasons
- manage an independent Alert lifecycle
- calculate historical statistical baselines
- expose StatisticalAnomaly separately from operational risk
- expose MLAnomaly separately from operational risk
- support a second public data source without breaking the first
- make ingestion/rerun/backfill idempotent and reliable
- run the core system locally without required paid services

## Explicitly out of V1

- shipment/container tracking
- purchase-order management
- inventory optimization
- supplier company/facility hierarchy
- automatic supplier selection
- automatic procurement actions
- automatic shipment rerouting
- predictive disruption forecasting
- authentication / authorization / multi-tenancy
- LLM/RAG/news summarization
- required paid APIs or map services
- required cloud deployment
- Kubernetes
- Spark
- Airflow
- MinIO
- ClickHouse
- dbt
- MLflow
- FastAPI model serving solely to expose ML
- Redis without a demonstrated need
- mobile application
- email/SMS notification integrations
- complex case/workflow management

Kafka and the Go replay service are not core V1 requirements. They are a gated later extension only after the batch/data/risk product is stable.

## V1 admission test

A proposed capability belongs in V1 only when at least one of the following is true:

1. It is required for the `Event -> Asset -> Risk -> Decision` core flow.
2. It is required to complete at least one documented V1 use case.
3. It is required for data correctness, explainability, reproducibility or core reliability.
4. Without it, the Phase 0-5 core acceptance criteria cannot be meaningfully satisfied.

If none apply, the capability goes to backlog rather than V1.
