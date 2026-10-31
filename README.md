# Revo

Subscription management for Brightloop Software.

## Local development

Requirements: Docker Desktop with Compose for the full stack, or Python 3.12 and `uv` for backend development.

1. Copy `.env.example` to `.env` if `make up` has not done so.
2. Run `make up` to start PostgreSQL, MailHog, and the API.
3. Open the API docs at <http://localhost:8000/docs> and MailHog at <http://localhost:8025>.
4. In another terminal, run `make seed` to load the demo data.

For backend tests outside Docker, run `cd backend && uv --cache-dir .uv-cache sync --frozen && uv --cache-dir .uv-cache run --frozen pytest`.

Useful commands: `make down`, `make logs`, `make migrate`, and `make test`.

For the performance fixture, run `make seed-bulk` after demo seeding. The demo seed generates local-only credentials and prints them on first creation; save the admin password as `REVO_ADMIN_PASSWORD`, then run `python backend/scripts/perf_smoke.py` against the running API. It reports p95 timings and fails endpoints over two seconds. The API container enables APScheduler for subscription activation, expiry, invoice generation, reminder counts, and the optional daily AI brief. The scheduler is off by default when running the API directly outside Compose.

## Demo credentials

The demo seed creates a local admin account. Its email and password are documented in the seed command output; replace them before any shared deployment.

For deployment, set a private `APP_SECRET_KEY`, `APP_ENV=production`, production `CORS_ORIGINS`, and real SMTP settings. Production startup rejects the built-in or example secret. Demo credentials are generated for a new local database and printed once by the seed command.
