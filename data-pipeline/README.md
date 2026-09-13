# Data Pipeline

Future Python data/ML pipeline.

Phase 0 contains no ingestion implementation.

Planned ownership:

- source adapters and ingestion
- raw/Bronze preservation
- validation and quarantine
- canonical Event normalization
- data-quality checks
- historical baselines
- StatisticalAnomaly
- MLAnomaly

Python owns writes to pipeline/event data and publishes a version-aware canonical event contract for read-only Java consumption.
