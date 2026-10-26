# APB Export UI

The upload page, server, job runner and QC presentation for [APB Export](https://github.com/anndata-omics-bridge/apb-export), released independently with a locked Python environment.

## Run

```bash
uv sync --locked --group dev
uv run --locked apb-export-web --store ./web-store --port 8770
```

Open http://127.0.0.1:8770. Python 3.13 is the tested interpreter; Node 22 is used only for frontend development and builds. The installed wheel serves its packaged assets without Node.

- [Web application](docs/web.md): uploads, examples, QC and job behavior
- [Deployment](docs/deploy.md): image build, migration and rollback
- [Dependency policy](docs/dependencies.md): immutable APB revisions and deliberate upgrades
- [Source baseline](docs/source-baseline.json): committed revisions recorded before extraction

## Development

```bash
make check
make check-full
```

`make check` runs Python quality gates, synthetic web tests, frontend tests and asset freshness, documentation links, and package validation. `make check-full` also installs the wheel into a fresh environment, runs a prefixed HTTP conversion, builds the image and tests it without source mounts. `make web` deliberately rebuilds the committed frontend bundle after a frontend change.

## Ownership

Distribution: `apb-export-ui`; Python namespace: `apb_export_ui`; executable: `apb-export-web`. The HTTP and persisted job interfaces remain those of the original web application. Conversion stays in the installed `apb-export`, `apb2` and `apb-fasta` CLIs; sibling Python imports use only their public API modules.

Extracted from APB Export commit `10e1166363259f7746c8d03d9bb4c11947118e0c`. This repository includes the original MIT license and attribution. Real example data remains external.
