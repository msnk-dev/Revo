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

## Demo credentials

The demo seed creates a local admin account. Its email and password are documented in the seed command output; replace them before any shared deployment.
