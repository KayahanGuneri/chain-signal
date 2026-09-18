# ChainSignal Frontend

Next.js geospatial supply-chain dashboard.

Phase 2 provides a Leaflet map, SupplyAsset selection, recent events and nearby
lookup with loading, empty and error states. Risk history, anomaly signals and
alerts remain future work. See [the API contract](../docs/phase-2-api.md).

Host development uses `npm ci`, `npm run dev`, and the server-side `BACKEND_URL`
setting (default `http://localhost:8080`). Use `npm run lint`, `npm run typecheck`,
`npm test`, and `npm run build` for quality checks. Tests use Node's built-in test
runner and TypeScript stripping, with no additional test framework. Node 24 is
the repository runtime baseline; Node 22.17 also supports these commands.

## Dependency management

- Node.js 24 LTS
- Next.js 16.3.3
- React 19.3.0
- TypeScript 5.9.2
- npm lockfile

## Integrated local runtime

The frontend is started by the root Docker Compose stack and is available on port 3000 by default.

Static branding is stored under `public/brand` and `public/og`. Social metadata
defaults to the local origin `http://localhost:3000`; set `FRONTEND_ORIGIN` to the
actual deployment origin in the frontend build environment when sharing a deployment.
Compose passes this setting as a frontend image build argument because the page's
social metadata is generated during the production build.
There is no configured production domain. Generated artwork is conceptual; see
[the visual overview](../docs/phase-2-overview.md) for the actual dashboard capture.

ESLint is pinned to 9.39.5 because the React rules bundled with this Next.js
configuration fail under ESLint 10. npm's ESLint support/deprecation warning is
nonblocking; lint rules remain enabled and the installed dependencies audit clean.
