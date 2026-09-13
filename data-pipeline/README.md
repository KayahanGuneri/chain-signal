# ChainSignal Data Pipeline

Python data-engineering / statistics / ML package skeleton.

Phase 0 intentionally contains no ingestion adapter, normalization rule, baseline calculation or anomaly model.

## Dependency management

- Python 3.12
- `pyproject.toml`

## Integrated local execution

From the repository root:

```text
docker compose --profile batch run --rm data-pipeline
```