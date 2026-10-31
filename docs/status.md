# Project verification status

Verification run on 2026-10-31 against the current project tree. Backend and frontend checks ran in their supported containers because this workstation has an unusable Python 3.12 host interpreter and Node 22.16.0, below the frontend package's declared engine requirement. Docker's `node:22-alpine` image supplied Node 22.23.4.

## Baseline results

| Check | Command / execution | Result |
|---|---|---|
| Backend tests | `docker compose run --rm --no-deps -v "C:/Rithun/Github/Revo/backend:/workspace" -w /workspace -e UV_PROJECT_ENVIRONMENT=/tmp/revo-merge-test-venv --entrypoint sh api -c "uv run --frozen pytest -q"` | **251 passed**, 0 failed, 1 deprecation warning, 30.81 s |
| Frontend tests | `docker compose build web` using Node 22.23.4 | **21 passed** across 7 files; 0 failed |
| Frontend production build | `npm run build` during the `web` image build | **Passed**: `tsc -b` and Vite 8.3.5 production bundle (104 modules) |
| Compose configuration | `docker compose config --quiet` | **Passed** |
| Frontend production build | `docker compose build web` | **Passed**: `tsc -b` and Vite 8.3.5 production bundle (104 modules) |
| API and frontend images | `docker compose up --build -d` | **Passed**: both images built, including the frontend tests and production bundle |

The deprecation warning is from Starlette's `TestClient` importing `httpx` through its deprecated compatibility path. It does not fail the test suite.

The backend run also covers the AI specialists and deterministic router (20 labeled prompts), typed tool-argument validation, Groq 429 failover, cross-customer prompt isolation, confirmation-gated writes, no-key operation, and number grounding. It includes CSV date filtering and the `=1+1` spreadsheet-injection regression, renewal-window and role checks, and security headers. The existing frontend run covers API field-error parsing, the Odoo +560 variant and 10% minimum-quantity discount UI flow, and a staff-to-admin-only-catalog guard test.

The local demo credentials were reset with `APP_ENV=demo` and the explicit `--use-legacy-demo-passwords` seed option: `admin@example.com / admin123` and `customer@example.com / user123`. The option is rejected outside demo mode; signup and password reset continue enforcing the strong-password rule.

The API and web Compose services were rebuilt after the AI orchestration changes and the API reported healthy. The Ollama tools probe was attempted, but no local Ollama service/model was available at `http://localhost:11434`; tool calling is therefore not verified on this machine. Run `backend/scripts/check_ollama_tools.py` after starting a compatible model before relying on Ollama.

The bulk-fixture performance smoke ran after the fixture-count guard confirmed 1,000 customers, 2,000 subscriptions, 20,000 invoices, and 16,000 payments. It measured every list endpoint, dashboard summary, report, and the new AI-run list endpoint; results are recorded in [perf.md](perf.md). No endpoint exceeded 2 s p95.

## Clean-clone demo stack

This clean-clone check verified the runnable Compose baseline before the current uncommitted catalog, reports, and dashboard feature changes. Repeat it after these changes are committed to verify a fresh clone of the feature-complete tree.

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
