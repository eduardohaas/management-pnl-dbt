# One-command local run: make all
PY := .venv/bin/python
DBT := .venv/bin/dbt --profiles-dir .

setup:
	python3.11 -m venv .venv && .venv/bin/pip install -r requirements.txt && $(DBT) deps

ingest:
	$(PY) ingestion/generate_erp_data.py
	$(PY) ingestion/load_bcb_ipca.py

build:
	$(DBT) build

docs:
	$(DBT) docs generate --static && open target/static_index.html

all: ingest build
