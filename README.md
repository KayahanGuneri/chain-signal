# ChainSignal

**Supply Chain Risk Intelligence Platform**

ChainSignal is a local-first decision-support platform for manufacturer/importer supply-chain operations and risk teams. It converts real public disruption data into explainable operational risk for tracked suppliers and ports. It is intentionally not a news aggregator.

## Phase 0 status

Phase 0 establishes the Product Definition & Architecture Contract plus a buildable Docker-first monorepo skeleton. Business features are intentionally deferred.

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

- **Python** — ingestion, raw/Bronze preservation, validation, canonical normalization, data quality/quarantine, statistical anomaly and ML anomaly.
- **Java 21 / Spring Boot** — SupplyAsset lifecycle, geospatial matching orchestration, deterministic RiskEngine, RiskSnapshot, Alert lifecycle and REST APIs.
- **Next.js / TypeScript** — operational dashboard and visualization.
- **PostgreSQL / PostGIS** — local persistence and geospatial querying with explicit table ownership.
- **Go** — gated replay/stream simulation workload for Phase 6.
- **Kafka** — intentionally absent until the batch-first core is stable.

## Toolchain baseline

- Java: 21
- Spring Boot: 4.1.1
- Maven: 3.9.x
- Python: 3.12
- Node.js: 24 LTS
- Next.js: 16.3.3
- React: 19.3.0
- TypeScript: 5.9.2
- Go: 1.27.1
- Docker Desktop / Docker Compose v2
- PostgreSQL: 16
- PostGIS: 3.5

Each subproject owns its dependency manifest independently.

## Repository structure

```text
chain-signal/
├── compose.yml
├── backend/                  # Spring Boot + Maven
├── data-pipeline/            # Python package / batch workloads
├── frontend/                 # Next.js + TypeScript
├── replay-service/           # Go module; Phase 6 gate
├── infra/                    # PostgreSQL initialization
├── docs/
│   ├── adr/
│   └── diagrams/
├── .env.example
├── .gitignore
└── README.md
```

## Docker-first bootstrap

Docker Desktop / Docker Engine must be running.

From the repository root:

```powershell
Copy-Item .env.example .env
docker compose up -d --build --wait
docker compose ps
```

Default services:

- PostgreSQL/PostGIS: `localhost:5432`
- Spring Boot health: `http://localhost:8080/actuator/health`
- Next.js skeleton: `http://localhost:3000`

Verify PostGIS:

```powershell
docker compose exec postgres psql -U chainsignal -d chainsignal -c "SELECT PostGIS_Version();"
```

Run the Python batch skeleton:

```powershell
docker compose --profile batch run --rm data-pipeline
```

Build/run the gated Go skeleton without introducing Kafka:

```powershell
docker compose --profile streaming build replay-service
docker compose --profile streaming run --rm replay-service
```

Stop the default runtime:

```powershell
docker compose down
```

Reset local database data only when intentionally required:

```powershell
docker compose down -v
```

## Phase 0 acceptance

See [`docs/phase-0-checklist.md`](docs/phase-0-checklist.md).