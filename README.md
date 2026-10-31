# Revo

Subscription management for Brightloop Software.

## Local development

Requirements: Docker Desktop with Docker Compose. The web image builds the frontend and serves it with nginx, so Node.js is not required on the host. Backend-only development needs CPython 3.12 and `uv`.

1. Run `docker compose up --build -d`. Compose starts PostgreSQL, MailHog, the API, and the built frontend. The API runs database migrations on startup.
2. Run `docker compose exec api python -m app.seed.demo` to load demo data and create the first admin account. Save the one-time credentials printed by the command; generated passwords meet the project password rules. Any password supplied through `REVO_DEMO_ADMIN_PASSWORD` or `REVO_DEMO_CUSTOMER_PASSWORD` must also meet those rules or seeding stops.
3. Open the app at <http://localhost:5173>, API docs at <http://localhost:8000/docs>, and MailHog at <http://localhost:8025>.

To follow startup, run `docker compose logs -f api web`. Stop the demo with `docker compose down`.

The seed creates one sample customer, an active monthly subscription, a matching catalog product and plan, and payment methods. The customer account credentials printed during the first seed run can be used to exercise the read-only portal. The scheduler generates invoices daily at 01:00 UTC. For an immediate billing preview, call `POST /api/v1/admin/jobs/generate_invoices/run` with the admin session cookies and an `X-CSRF-Token` header matching the `csrf_token` cookie. Email previews are available in MailHog at <http://localhost:8025>.

The API-backed demo includes customer, catalog, staff, subscription, invoice, payment, reporting, and customer portal flows. Staff can create subscriptions from a plan or quotation template, preview and run invoice generation, review invoice breakdowns, record payments, and manage subscription lifecycle actions. The dashboard shows overdue invoices and the latest daily brief. The assistant answers from permission-scoped Revo tools; if no provider credentials are configured, it uses deterministic local answers. Billing and reminder actions remain pending until a staff member confirms them in the assistant panel. The customer account can be used to demonstrate its read-only portal and account-scoped assistant.

For a frontend-only preview, build the web image with `VITE_USE_MOCKS=true` and use the demo login shown on the sign-in screen. Mock mode is an in-memory preview: changes are not persisted and assistant actions are not executed. Use the API-backed flow above for the integrated demo.

For backend tests outside Docker, run `cd backend && uv --cache-dir .uv-cache sync --frozen && uv --cache-dir .uv-cache run --frozen pytest`.

Useful commands: `make down`, `make logs`, `make migrate`, and `make test`.

The data model is documented in [docs/erd.md](docs/erd.md).

## GitHub workflow

Pull requests to `main` run the backend test suite and frontend production build.

For measured performance results, run `make seed-bulk` after demo seeding, then `make perf` against the running Compose stack. The smoke tool uses short-lived signed tokens for the local seeded identities, does not change or print their passwords, measures all list/report endpoints, and writes observed p50/p95 timings to `docs/perf.md`. It exits with an error if any endpoint exceeds 2 seconds p95. Reset the development database before repeating the bulk seed. The API container enables APScheduler for subscription activation, expiry, invoice generation, reminder counts, and the optional daily AI brief. The scheduler is off by default when running the API directly outside Compose.

## Demo credentials

The demo seed creates a local admin account with a generated random password that meets the project password rule. Its email and password are documented in the first seed command output; replace them before any shared deployment.

For a database created before the password rule was enforced, rotate both local demo credentials with `docker compose exec api python -m app.seed.demo --reset-credentials`. This invalidates existing sessions and prints new compliant random passwords once; save them securely.

For the requested classroom/demo login only, the seed supports `admin@example.com` / `admin123` and `customer@example.com` / `user123` when `APP_ENV=demo` and `--use-legacy-demo-passwords` is explicitly passed. Set `APP_ENV=demo` in the local `.env`, then run `docker compose up -d api` and `docker compose exec api python -m app.seed.demo --reset-credentials --use-legacy-demo-passwords`. These passwords are not accepted by signup or reset and must not be used outside a disposable demo environment.

For deployment, set a private `APP_SECRET_KEY`, `APP_ENV=production`, production `CORS_ORIGINS`, and real SMTP settings. Production startup rejects the built-in or example secret. Demo credentials are generated for a new local database and printed once by the seed command.
