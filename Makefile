.PHONY: up down logs seed seed-bulk test migrate

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

test:
	cd backend && uv --cache-dir .uv-cache run --frozen pytest

migrate:
	docker compose exec api alembic upgrade head

