.PHONY: setup fixture seed api worker test lint typecheck pipeline-baseline eval demo

setup:
	python -m pip install -e ".[dev,ml,stores]"
	docker compose up -d postgres minio chroma ollama mlflow
	python -m app.db.migrate
	python -m app.db.seed

fixture:
	python -m pipeline.ingest.synthetic --out data/fixtures/swat_mini.csv

seed:
	python -m app.db.seed

api:
	uvicorn app.main:app --reload --port 8000

worker:
	python -m app.workers.main

test:
	python -m pytest -q

lint:
	python -m ruff check app pipeline eval tests

typecheck:
	python -m mypy app pipeline

pipeline-baseline: fixture
	python -m eval.experiments --exp EXP-01 --dataset-run local

eval:
	python -m eval.experiments --all

demo:
	python -m eval.demo_runner
