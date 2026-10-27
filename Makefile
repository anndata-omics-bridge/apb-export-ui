VENV_BIN := .venv/bin
IMAGE ?= ghcr.io/anndata-omics-bridge/apb-export-ui
IMAGE_TAG ?= local
UI_REVISION ?= $(shell git rev-parse --verify HEAD 2>/dev/null || echo uncommitted)
STUDIO ?= ../apb_studio
MODULES ?= ../apb-proteobench/src/apb_proteobench/data/modules
WEB_EXAMPLES ?= build/web-examples

.DEFAULT_GOAL := help
.PHONY: help sync format format-check lint typecheck deps test web frontend-check docs build image smoke-wheel smoke-container check check-full web-examples clean

help:  ## Show developer commands
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  %-20s %s\n", $$1, $$2}'

sync:  ## Install the committed application lock
	uv sync --locked --group dev

format:  ## Format and autofix Python source, tests and scripts
	$(VENV_BIN)/ruff format src tests scripts
	$(VENV_BIN)/ruff check --fix src tests scripts

format-check:  ## Check formatting without rewriting files
	$(VENV_BIN)/ruff format --check src tests scripts

lint:  ## Run Ruff
	$(VENV_BIN)/ruff check src tests scripts

typecheck:  ## Run standard Pyright strict
	$(VENV_BIN)/pyright

deps:  ## Validate dependency declarations
	$(VENV_BIN)/deptry .

test:  ## Run synthetic web, job and QC tests with branch coverage
	$(VENV_BIN)/pytest --cov --cov-branch

web:  ## Rebuild the static frontend shipped in the Python package
	cd web && npm ci && npm test && npm run build

frontend-check:  ## Test TypeScript and compare fresh and packaged assets
	cd web && npm ci && npm test
	$(VENV_BIN)/python scripts/check_frontend.py

docs:  ## Check local documentation links
	$(VENV_BIN)/python scripts/check_docs.py

build:  ## Build and validate source and wheel distributions
	uv lock --check
	uv build
	$(VENV_BIN)/twine check dist/*

image:  ## Build the application image from this repository alone
	docker build --build-arg UI_REVISION=$(UI_REVISION) --build-arg EXPORTER_REVISION=$$($(VENV_BIN)/python -c 'import tomllib; print(next(d for d in tomllib.load(open("pyproject.toml", "rb"))["project"]["dependencies"] if d.startswith("apb-export @ ")).rsplit("@", 1)[1])') --build-arg REPORT_REVISION=$$($(VENV_BIN)/python -c 'import tomllib; print(next(d for d in tomllib.load(open("pyproject.toml", "rb"))["project"]["dependencies"] if d.startswith("apb-pmultiqc @ ")).rsplit("@", 1)[1])') -t $(IMAGE):$(IMAGE_TAG) .

smoke-wheel:  ## Test a clean wheel installation and prefixed HTTP routes
	$(VENV_BIN)/python scripts/smoke.py wheel

smoke-container:  ## Test the image without source mounts
	$(VENV_BIN)/python scripts/smoke.py container --image $(IMAGE):$(IMAGE_TAG)

check:  ## Run every merge-blocking gate
	uv lock --check
	$(MAKE) format-check lint typecheck deps test frontend-check docs build

check-full: check smoke-wheel image smoke-container  ## Run every pre-push acceptance check

web-examples:  ## Stage complete Fixture Manager inputs using the routine inventory
	$(VENV_BIN)/python scripts/web_examples.py $(STUDIO)/corpuses/routine.csv $(STUDIO)/test_data_download $(MODULES) $(WEB_EXAMPLES) --extra scripts/web_examples.csv --workspace .. --fastas $(STUDIO)/workflow_tables/workflow_proteobench.csv

clean:  ## Remove generated quality and packaging output
	$(VENV_BIN)/python -c "import shutil; [shutil.rmtree(path, ignore_errors=True) for path in ('build', 'dist', '.pytest_cache', '.ruff_cache')]"
