# Project verification status

Verification run on 2026-10-31 against the current project tree. Backend and frontend checks ran in their supported containers because this workstation has an unusable Python 3.12 host interpreter and Node 22.16.0, below the frontend package's declared engine requirement. Docker's `node:22-alpine` image supplied Node 22.23.4.

## Baseline results

| Check | Command / execution | Result |
|---|---|---|
| Backend tests | `docker compose run --rm --no-deps -v "C:/Rithun/Github/Revo/backend:/workspace" -w /workspace -e UV_PROJECT_ENVIRONMENT=/tmp/revo-test-venv --entrypoint sh api -c "uv sync --frozen && uv run --frozen pytest -q"` | **181 passed**, 0 failed, 1 deprecation warning, 24.95 s |
| Frontend tests | `npm test -- --maxWorkers=1` during the `web` image build, using Node 22.23.4 | **15 passed** across 5 files; 0 failed |
| Frontend production build | `npm run build` during the `web` image build | **Passed**: `tsc -b` and Vite 8.3.5 production bundle (104 modules) |
| Compose configuration | `docker compose config --quiet` | **Passed** |
| API and frontend images | `docker compose up --build -d` | **Passed**: both images built, including the frontend tests and production bundle |

The deprecation warning is from Starlette's `TestClient` importing `httpx` through its deprecated compatibility path. It does not fail the test suite.

## Clean-clone demo stack

The committed tree was cloned into an empty local folder with `git clone --no-local . .fresh-clone-check`. The existing demo already occupied the default host ports, so the isolated clone used alternate ports in its temporary `.env` file; the Compose services and images were otherwise unchanged.

| Check | Command / result |
|---|---|
| Start all services and build from clone | `docker compose --project-directory C:/Rithun/Github/Revo/.fresh-clone-check --project-name revo-fresh-clone up --build -d` — **passed**, all four services started |
| Container health | `docker compose ... ps` — PostgreSQL healthy, API healthy, web running, MailHog running |
| Database migration | `docker compose ... exec -T api alembic current` — `0004_invoice_line_snapshots (head)` |
| Demo seed | `docker compose ... exec -T api python -m app.seed.demo` — **passed**, created admin/customer demo accounts and sample data |
| UI through nginx | `http://localhost:5174/` — HTTP **200**, built asset reference present |
| API proxy through nginx | `http://localhost:5174/health` — HTTP **200**, `{"status":"ok"}` |
| API docs | `http://localhost:8001/docs` — HTTP **200** |

The same committed checkout was then started on the default ports with `docker compose up --build -d` — **passed**. `http://localhost:5173/` returned HTTP **200** with a built asset reference, and `http://localhost:5173/health` returned HTTP **200** with `{"status":"ok"}`. API health reported healthy and Alembic remained at head. A pre-existing temporary Vite container initially held port 5173; after stopping that old container and recreating the Compose network (without deleting the PostgreSQL volume), the standard stack started successfully.

No host Node install was used. The normal ports are web `5173`, API `8000`, PostgreSQL `5432`, and MailHog `8025`.
