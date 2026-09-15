# ChainSignal Data Pipeline

Python data engineering pipeline for ChainSignal.

## Runtime

- Python 3.12
- `src/` package layout
- Package: `chainsignal_pipeline`

## Project Structure

```text
data-pipeline/
â”œâ”€â”€ src/
â”‚   â””â”€â”€ chainsignal_pipeline/
â”‚       â”œâ”€â”€ __init__.py
â”‚       â”œâ”€â”€ __main__.py
â”‚       â”œâ”€â”€ config.py
â”‚       â””â”€â”€ logging_config.py
â”œâ”€â”€ tests/
â”œâ”€â”€ Dockerfile
â”œâ”€â”€ pyproject.toml
â””â”€â”€ README.md
```

The package structure grows incrementally as Phase 1 introduces real source ingestion, Bronze storage, normalization, and data-quality processing.

## Local Development

Create the virtual environment:

```powershell
py -V:3.12 -m venv .venv
```

Activate it on Windows:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install the project with development dependencies:

```powershell
python -m pip install -e ".[dev]"
```

## Quality Commands

Run tests:

```powershell
python -m pytest -q
```

Run lint checks:

```powershell
python -m ruff check .
```

Format Python code:

```powershell
python -m ruff format .
```

Verify formatting without changing files:

```powershell
python -m ruff format --check .
```

Run static type checking:

```powershell
python -m mypy src tests
```

Run the pipeline:

```powershell
python -m chainsignal_pipeline
```

## Coding Standards

- Python 3.12 is the supported runtime.
- Type hints are required for application code.
- `mypy` runs in strict mode.
- `ruff` owns Python formatting, linting, and import ordering.
- `pytest` is the test framework.
- Configuration is accessed through typed settings rather than reading environment variables directly throughout the application.
- Invalid configuration must fail explicitly instead of silently falling back to unsafe values.
- Application logs use structured logging.
- Prefer small, explicit modules over framework-heavy abstractions.
- Do not introduce generic `utils`, `common`, or `service` packages without a concrete responsibility.
- Raw source ingestion, normalization, and data-quality concerns must remain separate.
- Source-specific concepts must not leak into canonical models without an explicit mapping decision.
- Invalid source records must not silently disappear.

## Configuration

Configuration uses environment variables with the `CHAIN_SIGNAL_` prefix.

Current settings include:

```text
CHAIN_SIGNAL_ENVIRONMENT
CHAIN_SIGNAL_LOG_LEVEL
CHAIN_SIGNAL_HTTP_TIMEOUT_SECONDS
CHAIN_SIGNAL_BRONZE_PATH
```

Application modules should depend on the typed `Settings` object rather than calling environment APIs directly.

## Logging

Application logs are emitted as structured JSON.

Example:

```json
{
  "level": "INFO",
  "message": "ChainSignal data pipeline ready",
  "event": "pipeline_bootstrap",
  "version": "0.1.0",
  "environment": "local"
}
```

Future ingestion logs will include structured fields such as source, batch identity, record counts, and fetch metadata.

## Dependencies

Runtime and development dependencies are declared in `pyproject.toml`.

Runtime dependencies are dependencies required by the running pipeline.

Development dependencies include tools such as:

- pytest
- Ruff
- mypy

`requirements.lock.txt` is currently a snapshot of the local development environment. It is not treated as a portable cross-platform dependency lock contract.

## Docker

Build the data pipeline image from the repository root:

```powershell
docker build -t chainsignal-data-pipeline:phase1-day1 .\data-pipeline
```

Run the pipeline:

```powershell
docker run --rm chainsignal-data-pipeline:phase1-day1
```

The runtime container should emit a structured bootstrap log.

## Phase 1 Direction

Phase 1 will incrementally add:

1. GDACS source discovery and exploratory data analysis.
2. A source abstraction and GDACS ingestion adapter.
3. Reliable HTTP timeout and bounded retry behavior.
4. Bronze raw data preservation using Parquet.
5. Deterministic normalization to Canonical Event v1.
6. Quarantine with explicit reason codes.
7. Batch-level data-quality metrics.
8. Deterministic deduplication and reproducible reprocessing.

The first source is GDACS. Additional sources are intentionally deferred.
