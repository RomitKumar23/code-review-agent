.PHONY: up down build logs test migrate shell-api shell-worker

## Start all services
up:
	docker compose up --build

## Start in background
up-d:
	docker compose up --build -d

## Stop all services
down:
	docker compose down

## View logs
logs:
	docker compose logs -f

## Run tests
test:
	cd api && python -m pytest ../tests/ -v

## Run database migrations
migrate:
	docker compose exec api alembic upgrade head

## Open shell in api container
shell-api:
	docker compose exec api bash

## Open shell in worker container
shell-worker:
	docker compose exec worker bash

## Pull Ollama model (e.g. make pull-model MODEL=llama3)
pull-model:
	docker compose exec ollama ollama pull $(MODEL)

## Check worker is connected to Redis
worker-status:
	docker compose exec worker celery -A tasks inspect active

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
