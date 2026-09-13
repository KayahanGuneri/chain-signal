# ChainSignal

**Supply Chain Risk Intelligence Platform**

ChainSignal is a local-first decision-support platform for manufacturer/importer supply-chain operations and risk teams. It converts real public disruption data into explainable operational risk for tracked suppliers and ports. It is intentionally not a news aggregator.

## Phase 0 status

This repository currently contains only the **Product Definition & Architecture Contract** skeleton. Business logic is intentionally deferred.

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
├── backend/                  # Spring Boot risk/control plane (later phase)
├── data-pipeline/            # Python ingestion/data/ML pipeline (later phase)
├── frontend/                 # Next.js dashboard (later phase)
├── replay-service/           # Go replay service (Phase 6 gate)
├── infra/                    # Local infrastructure
├── docs/                     # Product/domain/architecture docs
│   ├── adr/
│   └── diagrams/
├── .env.example
├── .gitignore
└── README.md
```

## Local database bootstrap

From the repository root:

```powershell
Copy-Item .env.example .env
docker compose --env-file .env -f infra/docker-compose.yml up -d
docker compose --env-file .env -f infra/docker-compose.yml ps
```

Verify PostgreSQL readiness:

```powershell
docker compose --env-file .env -f infra/docker-compose.yml exec postgres pg_isready -U chainsignal -d chainsignal
```

Verify PostGIS:

```powershell
docker compose --env-file .env -f infra/docker-compose.yml exec postgres psql -U chainsignal -d chainsignal -c "SELECT PostGIS_Version();"
```

Stop the local database:

```powershell
docker compose --env-file .env -f infra/docker-compose.yml down
```

Remove the local database volume only when intentionally resetting local data:

```powershell
docker compose --env-file .env -f infra/docker-compose.yml down -v
```

## Phase 0 acceptance

See [`docs/phase-0-checklist.md`](docs/phase-0-checklist.md).

Do not mark runtime acceptance items as complete until the commands have actually been executed successfully.
