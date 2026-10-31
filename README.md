# Revo

Subscription management for Brightloop Software.

## Local development

Requirements: Docker Desktop with Compose for PostgreSQL, MailHog, and the API; Node.js 22.22.2 or newer and npm for the frontend. Backend-only development needs CPython 3.12 and `uv`.

1. Copy `.env.example` to `.env` if `make up` has not done so.
2. Run `make up` to start PostgreSQL, MailHog, and the API.
3. Open the API docs at <http://localhost:8000/docs> and MailHog at <http://localhost:8025>.
4. In another terminal, run `make seed` to load the demo data and create the first admin account. Save the one-time credentials printed by the command.
5. Copy `frontend/.env.example` to `frontend/.env.local`, set `VITE_USE_MOCKS=false`, then run `cd frontend && npm ci && npm run dev`.
6. Open <http://localhost:5173> and sign in with the admin credentials from `make seed`.

The seed creates one sample customer, an active monthly subscription, a matching catalog product and plan, and payment methods. The customer account credentials printed during the first seed run can be used to exercise the read-only portal. The scheduler generates invoices daily at 01:00 UTC. For an immediate billing preview, call `POST /api/v1/admin/jobs/generate_invoices/run` with the admin session cookies and an `X-CSRF-Token` header matching the `csrf_token` cookie. Email previews are available in MailHog at <http://localhost:8025>.

The API-backed demo includes customer, catalog, staff, subscription, invoice, payment, reporting, and customer portal flows. Staff can create subscriptions from a plan or quotation template, preview and run invoice generation, review invoice breakdowns, record payments, and manage subscription lifecycle actions. The dashboard shows overdue invoices and the latest daily brief. The assistant answers from permission-scoped Revo tools; if no provider credentials are configured, it uses deterministic local answers. Billing and reminder actions remain pending until a staff member confirms them in the assistant panel. The customer account can be used to demonstrate its read-only portal and account-scoped assistant.

For a frontend-only preview, set `VITE_USE_MOCKS=true` and use the demo login shown on the sign-in screen. Mock mode is an in-memory preview: changes are not persisted and assistant actions are not executed. Use the API-backed flow above for the integrated demo.

For backend tests outside Docker, run `cd backend && uv --cache-dir .uv-cache sync --frozen && uv --cache-dir .uv-cache run --frozen pytest`.

Useful commands: `make down`, `make logs`, `make migrate`, and `make test`.

The data model is documented in [docs/erd.md](docs/erd.md).

## GitHub workflow

Pull requests to `main` run the backend test suite and frontend production build.

For the performance fixture, run `make seed-bulk` after demo seeding. The demo seed generates local-only credentials and prints them on first creation; save the admin password as `REVO_ADMIN_PASSWORD`, then run `python backend/scripts/perf_smoke.py` against the running API. It reports p95 timings and fails endpoints over two seconds. The API container enables APScheduler for subscription activation, expiry, invoice generation, reminder counts, and the optional daily AI brief. The scheduler is off by default when running the API directly outside Compose.

## Demo credentials

The demo seed creates a local admin account. Its email and password are documented in the seed command output; replace them before any shared deployment.

For deployment, set a private `APP_SECRET_KEY`, `APP_ENV=production`, production `CORS_ORIGINS`, and real SMTP settings. Production startup rejects the built-in or example secret. Demo credentials are generated for a new local database and printed once by the seed command.
