# Phase 2 verification evidence

Final acceptance executed on 2026-09-18 after code, metadata, static asset and
visual integration. Branch: `feature/phase-2-geospatial-assets`; unchanged HEAD:
`37a3064 feat(backend): add supply asset CRUD API`. No commit or push was performed.
See the [checklist](phase-2-checklist.md), [API contract](phase-2-api.md) and
[visual overview](phase-2-overview.md).

## Final commands and results

All Python commands used the project Python 3.12 virtualenv, never global Python.
Root commands use `data-pipeline/.venv/Scripts/python.exe`; commands in the pipeline
use `.venv/Scripts/python.exe`. The full pytest invocation below is the literal
last run; repeat acceptance through the smoke script to obtain fresh short Temp
paths and scoped disposable database settings.

| Working directory | Command | Result |
|---|---|---|
| Root | `.\data-pipeline\.venv\Scripts\python.exe --version` | PASS — Python 3.12.10 |
| Root | `.\data-pipeline\.venv\Scripts\python.exe -m compileall -q data-pipeline/src data-pipeline/tests scripts` | PASS |
| data-pipeline | `.\.venv\Scripts\python.exe -m ruff check .` | PASS |
| data-pipeline | `.\.venv\Scripts\python.exe -m ruff format --check .` | PASS — 40 files |
| Root | `.\data-pipeline\.venv\Scripts\python.exe -m ruff check --config data-pipeline/pyproject.toml scripts` | PASS |
| Root | `.\data-pipeline\.venv\Scripts\python.exe -m ruff format --check --config data-pipeline/pyproject.toml scripts` | PASS — 2 files |
| data-pipeline | `.\.venv\Scripts\python.exe -m mypy src tests` | PASS — 38 source files |
| Root | `.\data-pipeline\.venv\Scripts\python.exe -m mypy --config-file data-pipeline/pyproject.toml scripts` | PASS — 2 source files |
| data-pipeline | `.\.venv\Scripts\python.exe -m pytest -q --basetemp C:\Users\kayah\AppData\Local\Temp\cs-ad1f27b8 -o cache_dir=C:\Users\kayah\AppData\Local\Temp\cs-ad1f27b8-cache` | PASS — 196 passed, 0 failed, 0 skipped |
| backend | `mvn -B -ntp test` | PASS — 33 unit; 0 failures/errors/skips |
| backend | `mvn -B -ntp -Ppostgis verify` | PASS — 33 unit + 28 real PostGIS integration; 0 failures/errors/skips |
| frontend | `npm ci` | PASS — 0 reported vulnerabilities |
| frontend | `npm run lint` | PASS |
| frontend | `npm run typecheck` | PASS |
| frontend | `npm test` | PASS — 8 passed; 0 failed/skipped/cancelled |
| frontend | `npm run build` | PASS — production Next build with static social metadata |
| Root | `docker compose config --quiet` | PASS |
| Root | `./scripts/phase2-compose-smoke.ps1 -RunSmoke` | PASS — rebuilt images; all three services healthy; live full-chain smoke; owned resources cleaned |
| Root | `./scripts/phase2-smoke.ps1 -RunTests` | PASS — live full chain and full Python suite including 3 real database integration tests |
| Root | `.\data-pipeline\.venv\Scripts\python.exe scripts/check_worktree.py` | PASS — staged and unstaged whitespace; 55 current text files UTF-8 without BOM/LF; real index unchanged |
| Root | `git -c safe.directory=C:/Users/kayah/Desktop/chain-signal diff --check` | PASS |
| Root | `git -c safe.directory=C:/Users/kayah/Desktop/chain-signal diff --cached --check` | PASS |

The pytest process ran with `CHAIN_SIGNAL_TEST_DATABASE=1` and settings for the
fresh Flyway-initialized smoke database. No integration test was skipped. Maven's
PostGIS profile used Testcontainers with `postgis/postgis:16-3.5`. Host frontend
checks used Node 22.17; the Compose image used the Node 24.21 runtime baseline.

## Live source and integration evidence

The final host smoke fetched a seven-day live GDACS window, preserved a raw Bronze
Parquet batch, invoked CLI canonical normalization and persisted 123 valid events
with 0 invalid, duplicate or quarantined records in that batch. This is one
acceptance dataset, not a coverage claim. The final Compose run independently
persisted 123 live events in its own disposable database. Neither used the offline
switch. The final host Bronze batch id was
`d14dcc9df18befa8277e56900c19d34e169cefe59e6de5913c01454924272914`.

Both smokes checked Flyway V1-V3, PostGIS, Python idempotent persistence, Event
reads, SupplyAsset create/get/list/update/soft deactivation, generated geography
and SRID 4326, nearby inclusion/exclusion, 0 m and approximately 1,110 m distance,
invalid radius/limit 400 responses, inactive nearby 404, frontend availability,
proxy equivalence, PNG HTTP responses and generated OG/Twitter tags.

Database ports were discovered with `docker inspect`; no portable config hardcodes
this machine's PostgreSQL workaround. Each script removed only its owned services
and disposable data and restored scoped environment variables. Existing Compose
resources and the Windows PostgreSQL service were not mutated.

## Natural GiST plan

The final smoke inserted 50,000 globally distributed disposable events through
Python, alongside 123 live events and 3 nearby fixtures, and analyzed both tables.
It extracted the exact production nearby SELECT from `JdbcEventRepository` and
executed `EXPLAIN (ANALYZE, BUFFERS)` for radius 2,000 meters and limit 100. No
planner override, including `enable_seqscan=off`, was used. The plan's event scan
uses the spatial index; the single-row asset scan naturally uses a sequential scan.
The 50,000 plan fixtures were removed before the smoke completed. The full plan
is retained below and in ignored `.smoke/nearby-explain.txt`.

```text
Limit  (cost=99.43..99.43 rows=1 width=86) (actual time=4.677..4.680 rows=2 loops=1)
  Buffers: shared hit=78
  ->  Sort  (cost=99.43..99.43 rows=1 width=86) (actual time=4.676..4.678 rows=2 loops=1)
        Sort Key: (st_distance(e.location, a.location, true)), e.occurred_at DESC, e.id DESC
        Sort Method: quicksort  Memory: 25kB
        Buffers: shared hit=78
        ->  Nested Loop  (cost=4.44..99.42 rows=1 width=86) (actual time=4.652..4.667 rows=2 loops=1)
              Buffers: shared hit=78
              ->  Seq Scan on supply_asset a  (cost=0.00..1.01 rows=1 width=32) (actual time=0.003..0.005 rows=1 loops=1)
                    Filter: (active AND (id = '1'::smallint))
                    Buffers: shared hit=1
              ->  Bitmap Heap Scan on event e  (cost=4.44..85.86 rows=5 width=110) (actual time=4.638..4.646 rows=2 loops=1)
                    Filter: st_dwithin(location, a.location, '2000'::double precision, true)
                    Heap Blocks: exact=1
                    Buffers: shared hit=77
                    ->  Bitmap Index Scan on idx_event_location_gist  (cost=0.00..4.44 rows=5 width=0) (actual time=0.020..0.020 rows=2 loops=1)
                          Index Cond: (location && _st_expand(a.location, '2000'::double precision))
                          Buffers: shared hit=4
Planning:
  Buffers: shared hit=180
Planning Time: 0.412 ms
Execution Time: 4.743 ms
```

## Visual and ownership review

PNG signatures, chunk CRCs and compressed image payloads passed for all 6 assets;
all 5 supplied images preserve their original dimensions and pixel data after
lossless recompression. README and Phase 2 documentation relative links and image
paths resolve locally; every embedded image has alt text. Conceptual captions
explicitly identify unsupported schema labels, event types, UI controls and metrics.
The authoritative API contract contains no generated infographic schema.

The actual screenshot was captured from the disposable Compose frontend, with
explicitly named demo assets and Python-owned smoke events alongside live GDACS.
Browser verification exercised the 2 km radius search, supplier selection
(approximately 0.56 km distances) and port map-marker selection (0 and 1.11 km).
No browser console errors were recorded. The capture was encoded as PNG without
changing captured content. The actual capture precedes the future dashboard concept.

All Spring production source was reviewed: exactly one `@RestControllerAdvice`,
no canonical Event DML, no JPA and no writes to generated geography. The nearby
query retains `ST_DWithin(e.location, a.location, :radiusMeters)` and meter
responses. `@EnableConfigurationProperties` remains on EventService; it is valid
and the real application integration suite confirms binding.

## Known limitations and nonblocking warnings

- Phase 2 collections are bounded subsets without pagination; the dashboard loads
  the latest 100 events plus nearby results. GDACS normalization currently supports
  earthquakes and floods, while the canonical taxonomy supports five types.
- OpenStreetMap tiles require external network access and follow its demo usage
  policy. Lists remain usable when tile loading fails; this fallback was reviewed
  in source, not forced during the browser capture.
- The generated branding and concepts contain fictional figures and future
  functionality. They are explicitly captioned and are not product evidence.
- ESLint 9.39.5 is pinned because this Next configuration's bundled React rules
  fail under ESLint 10. npm emits a support/deprecation warning; lint passes with
  all rules enabled and npm reports 0 vulnerabilities.
- Test tooling emits nonblocking Mockito dynamic-agent, Jackson deprecated test
  accessor and Node module/type-stripping warnings. No failure or skip is hidden.
- Social metadata defaults to the local origin. Set `FRONTEND_ORIGIN` at build time
  for a deployment; Compose passes it as a build argument. No production domain
  has been invented.
- Query-plan smoke extraction depends on the two Java SQL constants retaining
  their current shape. This deliberately proves the production query without a
  duplicated SQL definition and fails visibly if the source shape changes.

## Review state

All intended Phase 2 source, tests, config, documentation and six PNG assets are
staged as one reviewable patch. No commit or push was performed. Logs, build
outputs, dependency directories, data fixtures and secrets remain excluded.
The pre-existing `phase2-review.patch` is preserved locally and ignored as a
review artifact. The final status and staged count are recorded below.

Staged path count: **62**. `git status --short` contains only staged changes;
there are no unstaged changes or non-ignored untracked files.

```text
M  .env.example
M  .gitignore
M  README.md
M  backend/README.md
M  backend/pom.xml
A  backend/src/main/java/io/chainsignal/backend/event/application/EventNotFoundException.java
A  backend/src/main/java/io/chainsignal/backend/event/application/EventQueryProperties.java
A  backend/src/main/java/io/chainsignal/backend/event/application/EventRepository.java
A  backend/src/main/java/io/chainsignal/backend/event/application/EventService.java
A  backend/src/main/java/io/chainsignal/backend/event/domain/Event.java
A  backend/src/main/java/io/chainsignal/backend/event/domain/EventType.java
A  backend/src/main/java/io/chainsignal/backend/event/domain/NearbyEvent.java
A  backend/src/main/java/io/chainsignal/backend/event/domain/Severity.java
A  backend/src/main/java/io/chainsignal/backend/event/persistence/JdbcEventRepository.java
A  backend/src/main/java/io/chainsignal/backend/event/web/EventController.java
R  backend/src/main/java/io/chainsignal/backend/supplyasset/web/ApiErrorResponse.java -> backend/src/main/java/io/chainsignal/backend/shared/web/ApiErrorResponse.java
R  backend/src/main/java/io/chainsignal/backend/supplyasset/web/SupplyAssetExceptionHandler.java -> backend/src/main/java/io/chainsignal/backend/shared/web/ApiExceptionHandler.java
M  backend/src/main/java/io/chainsignal/backend/supplyasset/application/CreateSupplyAssetCommand.java
M  backend/src/main/java/io/chainsignal/backend/supplyasset/application/SupplyAssetNotFoundException.java
M  backend/src/main/java/io/chainsignal/backend/supplyasset/application/UpdateSupplyAssetCommand.java
M  backend/src/main/java/io/chainsignal/backend/supplyasset/domain/SupplyAsset.java
M  backend/src/main/resources/application.yml
D  backend/src/test/java/io/chainsignal/backend/ChainSignalApplicationTests.java
A  backend/src/test/java/io/chainsignal/backend/EventServiceTests.java
A  backend/src/test/java/io/chainsignal/backend/GeospatialApiIT.java
A  backend/src/test/java/io/chainsignal/backend/SupplyAssetTests.java
M  compose.yml
M  data-pipeline/src/chainsignal_pipeline/models/event.py
A  data-pipeline/tests/test_database_settings.py
A  data-pipeline/tests/test_event_persistence.py
A  data-pipeline/tests/test_event_persistence_integration.py
M  data-pipeline/tests/test_main.py
A  docs/assets/phase-2/dashboard-concept.png
A  docs/assets/phase-2/dashboard-phase2-actual.png
A  docs/assets/phase-2/operational-workflow-concept.png
A  docs/assets/phase-2/phase-2-architecture-concept.png
M  docs/canonical-event-contract.md
A  docs/phase-2-api.md
A  docs/phase-2-checklist.md
A  docs/phase-2-overview.md
A  docs/phase-2-verification.md
M  frontend/Dockerfile
M  frontend/README.md
A  frontend/eslint.config.mjs
M  frontend/next-env.d.ts
M  frontend/package-lock.json
M  frontend/package.json
A  frontend/public/brand/chainsignal-hero.png
A  frontend/public/og/chainsignal-phase2-og.png
A  frontend/src/app/api/[...path]/route.ts
M  frontend/src/app/globals.css
M  frontend/src/app/layout.tsx
M  frontend/src/app/page.tsx
A  frontend/src/components/asset-map.tsx
A  frontend/src/components/dashboard.tsx
A  frontend/src/lib/api.ts
A  frontend/tests/api.test.mts
M  frontend/tsconfig.json
A  scripts/check_worktree.py
A  scripts/phase2-compose-smoke.ps1
A  scripts/phase2-smoke.ps1
A  scripts/phase2_smoke.py
```
