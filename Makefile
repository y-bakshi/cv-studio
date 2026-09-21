.PHONY: install dev-api dev-web check infrastructure

install:
	python3 -m venv .venv
	.venv/bin/pip install -r apps/api/requirements.txt
	cd apps/web && npm install

infrastructure:
	docker compose up -d postgres redis

dev-api:
	.venv/bin/uvicorn app.main:app --reload --app-dir apps/api --port 8000

dev-web:
	cd apps/web && npm run dev

check:
	.venv/bin/python -m pytest apps/api/tests
	cd apps/web && npm run build
