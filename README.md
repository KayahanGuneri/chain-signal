# ChainSignal

**Supply Chain Risk Intelligence Platform**

ChainSignal is a local-first decision-support platform for manufacturer/importer supply-chain operations and risk teams. It converts real public disruption data into explainable operational risk for tracked suppliers and ports. It is intentionally not a news aggregator.

## Phase 0 status

This repository currently contains the **Product Definition & Architecture Contract** and a Docker-first local runtime skeleton. Business logic is intentionally deferred.

### V1 tracked assets

- `SUPPLIER`
- `PORT`

### V1 event taxonomy

- `EARTHQUAKE`
- `FLOOD`
- `CONFLICT`
- `PROTEST`
- `STRIKE`

## Architecture baseline

- **Python** — ingestion, raw/Bronze preservation, validation, canonical normalization, data quality/quarantine, statistical anomaly, ML anomaly.
- **Java 21 / Spring Boot** — SupplyAsset lifecycle, geospatial matching orchestration, deterministic RiskEngine, RiskSnapshot, Alert lifecycle, REST APIs.
- **Next.js / TypeScript** — operational dashboard and visualization.
- **PostgreSQL / PostGIS** — local persistence and geospatial querying with explicit table ownership.
- **Go** — Phase 6 only, for historical replay / Kafka stream simulation if the batch core is stable.
- **Kafka** — intentionally deferred until the batch-first core product is stable.

## Docker-first local runtime

ChainSignal uses Docker Compose as the single integrated local runtime entrypoint.

As later phases initialize the application subprojects, their containers will be added to the same Compose project:

```text
docker compose up -d --build
          |
          +-- PostgreSQL/PostGIS
          +-- Spring Boot backend        (later phase)
          +-- Python data pipeline       (later phase)
          +-- Next.js frontend           (later phase)
          +-- Go replay service          (Phase 6 gate)
          +-- Kafka                      (Phase 6 gate/profile)
```

For the normal integrated local workflow, developers should not need to manually start every application runtime one by one.

Kafka and the Go replay service remain gated by the batch-first architecture decision.

## Toolchain baseline

The Phase 0 baseline is:

- Java: 21
- Python: 3.12
- Node.js: 22 LTS
- TypeScript: 5.x
- Go: 1.24+
- Docker Desktop / Docker Compose v2
- PostgreSQL 16 + PostGIS 3.5 container

Exact application dependency versions will be locked when each subproject is initialized in later phases.

## Repository structure

```text
chain-signal/
├── compose.yml               # Single local Docker Compose entrypoint
├── backend/                  # Spring Boot risk/control plane (later phase)
├── data-pipeline/            # Python ingestion/data/ML pipeline (later phase)
├── frontend/                 # Next.js dashboard (later phase)
├── replay-service/           # Go replay service (Phase 6 gate)
├── infra/                    # Local infrastructure details
├── docs/                     # Product/domain/architecture docs
│   ├── adr/
│   └── diagrams/
├── .env.example
├── .gitignore
└── README.md
```

## Local bootstrap

From the repository root:

```powershell
Copy-Item .env.example .env
docker compose up -d --build
docker compose ps
```

Verify PostgreSQL readiness:

```powershell
docker compose exec postgres pg_isready -U chainsignal -d chainsignal
```

Verify PostGIS:

```powershell
docker compose exec postgres psql -U chainsignal -d chainsignal -c "SELECT PostGIS_Version();"
```

Stop the local stack:

```powershell
docker compose down
```

Remove the local database volume only when intentionally resetting local data:

```powershell
docker compose down -v
```

## Phase 0 acceptance

See [`docs/phase-0-checklist.md`](docs/phase-0-checklist.md).

Runtime acceptance items are marked complete only after the commands have actually been executed successfully.
