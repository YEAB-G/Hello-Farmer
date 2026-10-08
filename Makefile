.PHONY: help build up down test lint logs clean

help:
	@echo "Hello Farmer Automation"
	@echo "  make up      - Start the entire stack in Docker"
	@echo "  make down    - Stop all containers"
	@echo "  make test    - Run test suite"
	@echo "  make lint    - Run linter (ruff)"
	@echo "  make logs    - Follow container logs"

up:
	docker compose up --build -d

down:
	docker compose down

test:
	python -m pytest tests/ -v

lint:
	python -m ruff check .

logs:
	docker compose logs -f

clean:
	docker compose down -v
