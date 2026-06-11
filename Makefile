.PHONY: help setup up dev down logs ps test build demo-candidates freeze-demo freeze-demo-strict freeze-demo-current pull push

help:
	@echo "TrustSci-Agent development commands"
	@echo "  make setup  - create .env from .env.example if missing"
	@echo "  make up     - start production-like compose stack"
	@echo "  make dev    - start hot-reload compose stack"
	@echo "  make down   - stop compose stack"
	@echo "  make logs   - follow compose logs"
	@echo "  make test   - run backend tests locally"
	@echo "  make build  - run frontend production build locally"
	@echo "  make demo-candidates - list demo run readiness checks"
	@echo "  make freeze-demo RUN_ID=<run_id> - create a submission freeze package"
	@echo "  make freeze-demo-strict RUN_ID=<run_id> - create a package and fail on warnings"
	@echo "  make freeze-demo-current RUN_ID=<run_id> - accept current verified set and strict-package it"
	@echo "  make pull   - fetch and pull origin/main"
	@echo "  make push   - push current branch"

setup:
	@test -f .env || cp .env.example .env

up: setup
	docker compose up --build

dev: setup
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build

down:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml down

logs:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml logs -f

ps:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml ps

test:
	python -m pytest

build:
	cd frontend && npm run build

demo-candidates:
	python scripts/freeze_demo_case.py --list-candidates

freeze-demo:
	@test -n "$(RUN_ID)" || (echo "RUN_ID is required, e.g. make freeze-demo RUN_ID=run_abc123" && exit 1)
	python scripts/freeze_demo_case.py "$(RUN_ID)"

freeze-demo-strict:
	@test -n "$(RUN_ID)" || (echo "RUN_ID is required, e.g. make freeze-demo-strict RUN_ID=run_abc123" && exit 1)
	python scripts/freeze_demo_case.py --strict "$(RUN_ID)"

freeze-demo-current:
	@test -n "$(RUN_ID)" || (echo "RUN_ID is required, e.g. make freeze-demo-current RUN_ID=run_abc123" && exit 1)
	python scripts/freeze_demo_case.py --accept-current-verified --strict "$(RUN_ID)"

pull:
	git fetch origin main --prune
	git pull --ff-only origin main

push:
	git push
