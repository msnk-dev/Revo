.PHONY: up down logs seed test migrate

up:
	@python -c "from pathlib import Path; p=Path('.env'); p.exists() or p.write_bytes(Path('.env.example').read_bytes())"
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f api postgres mailhog

seed:
	docker compose exec api python -m app.seed.demo

test:
	cd backend && uv --cache-dir .uv-cache run --frozen pytest

migrate:
	docker compose exec api alembic upgrade head

