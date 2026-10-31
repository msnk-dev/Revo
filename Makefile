.PHONY: up down logs seed seed-bulk perf test migrate

up:
	@python -c "from pathlib import Path; p=Path('.env'); p.exists() or p.write_bytes(Path('.env.example').read_bytes())"
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f web api postgres mailhog

seed:
	docker compose exec api python -m app.seed.demo

seed-bulk:
	docker compose exec api python -m app.seed.bulk

perf:
	docker compose exec -e REVO_PERF_INTERNAL_AUTH=1 -e REVO_PERF_OUTPUT=/tmp/perf.md api python scripts/perf_smoke.py
	docker compose cp api:/tmp/perf.md docs/perf.md

test:
	cd backend && uv --cache-dir .uv-cache run --frozen pytest

migrate:
	docker compose exec api alembic upgrade head

