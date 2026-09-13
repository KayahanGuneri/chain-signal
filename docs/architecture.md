# ChainSignal ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Architecture

## Architectural objective

Use the smallest architecture that cleanly separates data engineering, business risk logic, presentation and optional replay/streaming concerns while keeping the entire core runtime local and reproducible.

## Responsibilities

### Python data pipeline

**Why here?** Python is the project's data engineering/statistics/ML environment and owns source-specific transformation concerns.

Responsibilities:

- source adapters and ingestion
- raw/Bronze preservation
- validation and quarantine
- canonical Event normalization
- data quality
- historical baselines
- StatisticalAnomaly
- MLAnomaly

Python must not implement the deterministic operational RiskEngine or Alert lifecycle.

### Java / Spring Boot

**Why here?** Java/Spring Boot owns stable business rules, lifecycle logic, geospatial risk orchestration and public application APIs.

Responsibilities:

- SupplyAsset lifecycle
- read-only consumption of the canonical Event persistence contract
- geospatial event/asset matching orchestration
- deterministic operational RiskEngine
- RiskSnapshot and RiskReason lifecycle
- Alert lifecycle
- REST/API contracts
- dashboard aggregation APIs
- optional future Kafka consumer

Java must not duplicate source normalization or anomaly-model training.

### Go replay service

**Why here?** Go is reserved for a later workload where concurrency, rate control and graceful stream replay are real requirements.

Responsibilities only if Phase 6 gate is reached:

- historical canonical event replay
- rate-controlled Kafka producer
- replay concurrency
- graceful shutdown
- replay metrics

Go must not reimplement Python normalization or Java risk logic.

### Frontend

**Why here?** Next.js/TypeScript provides the operational decision-support UI.

Responsibilities:

- dashboard
- map
- asset detail
- event list
- risk reasons/history
- anomaly signals
- alerts
- loading/error/empty states

### PostgreSQL / PostGIS

**Why here?** One local relational/geospatial store is sufficient for V1 and supports spatial queries without introducing extra infrastructure.

A single database instance does not imply shared write ownership.

## Batch-first architecture

Phase 0-5 uses the batch-first path:

```text
Public Sources
  -> Python ingestion/validation/raw/normalization
  -> PostgreSQL/PostGIS canonical event data
  -> Spring Boot read-only event consumption
  -> geospatial matching
  -> deterministic risk calculation
  -> RiskSnapshot / Alert
  -> Next.js dashboard
```

Kafka and Go are intentionally deferred. They may be introduced only when the core batch/data/risk product is stable and replay/streaming adds a real capability.

## Cross-language contract

Python owns canonical event persistence and migrations. Spring Boot may read the documented Java-visible portion of that schema but must never write to it.

Because this creates deliberate database-level coupling, the Java-readable canonical event schema is a version-aware cross-language contract. Python-owned migrations that break that contract require explicit compatibility handling.

## No silent technology expansion

Do not introduce Kubernetes, cloud deployment, Spark, Airflow, MinIO, ClickHouse, dbt, MLflow, FastAPI model serving, LLM/RAG, authentication/multi-tenancy or Redis without first documenting the problem, simplest alternative, justification and operational cost.

## Docker-first local runtime

Docker Compose is the single integrated local-runtime entrypoint for ChainSignal.

The repository root owns the developer-facing `compose.yml`. Infrastructure implementation details remain under `/infra`.

The target developer workflow is:

```text
clean clone
  -> create local .env from .env.example
  -> docker compose up -d --build
  -> healthy local stack
```

As application subprojects are initialized, Spring Boot, Python and Next.js services will be containerized and added to the same Compose project. The Go replay service and Kafka remain optional Phase 6 components and must not be required for the batch-first core runtime.

Containers may use `restart: unless-stopped` for local resilience, but Docker Desktop / the Docker daemon must still be running.

This decision exists for local reproducibility and developer ergonomics. It does not imply Kubernetes, cloud deployment or production orchestration.

## Technical project skeleton

Phase 0 creates buildable technical boundaries without implementing business features:

- `/backend`: Java 21 + Spring Boot + Maven bootstrap
- `/data-pipeline`: Python 3.12 package bootstrap
- `/frontend`: Node.js 24 LTS + Next.js/TypeScript bootstrap
- `/replay-service`: Go 1.27 module bootstrap, still gated for Phase 6
- root `compose.yml`: integrated Docker-first local runtime

The default Compose runtime starts PostgreSQL/PostGIS, backend and frontend. Python remains an on-demand batch workload. Go remains an on-demand/gated workload. Kafka is not introduced in Phase 0.

A buildable skeleton is not permission to implement responsibilities early: normalization remains Python-owned, deterministic operational risk remains Java-owned, and replay/streaming remains gated.