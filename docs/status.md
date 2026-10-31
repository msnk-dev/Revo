# Project verification status

Verification run on 2026-10-31 against the current project tree. Backend and frontend checks ran in their supported containers because this workstation has an unusable Python 3.12 host interpreter and Node 22.16.0, below the frontend package's declared engine requirement. Docker's `node:22-alpine` image supplied Node 22.23.4.

## Baseline results

| Check | Command / execution | Result |
|---|---|---|
| Backend tests | `docker compose run --rm --no-deps -v "C:/Rithun/Github/Revo/backend:/workspace" -w /workspace -e UV_PROJECT_ENVIRONMENT=/tmp/revo-test-venv --entrypoint sh api -c "uv sync --frozen && uv run --frozen pytest -q"` | **181 passed**, 0 failed, 1 deprecation warning, 24.95 s |
| Frontend tests | `npm test -- --maxWorkers=1` during the `web` image build, using Node 22.23.4 | **15 passed** across 5 files; 0 failed |
| Frontend production build | `npm run build` during the `web` image build | **Passed**: `tsc -b` and Vite 8.3.5 production bundle (104 modules) |
| Compose configuration | `docker compose config --quiet` | **Passed** |
| API and frontend images | `docker compose build api web` | API image built; web image built after correcting the Vitest CLI flag |

The deprecation warning is from Starlette's `TestClient` importing `httpx` through its deprecated compatibility path. It does not fail the test suite.

## Demo stack checks

Pending: run `docker compose up --build -d` from a clean clone; verify Alembic migrations, demo seed, `http://localhost:5173/`, API health through nginx, and MailHog. Record observed output here after the clean-stack run.
