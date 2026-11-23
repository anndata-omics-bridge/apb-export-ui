# Deployment

The standalone image is `ghcr.io/anndata-omics-bridge/apb-export-ui`. It builds from this repository and its committed lock; no sibling source checkouts are required.

## Build and release

```bash
uv sync --locked --group dev
make check-full
make image IMAGE_TAG=local
```

The image builds the Lit/Vite frontend with Node 22, then installs the Python application using `uv sync --locked --no-dev --no-editable`. Node is absent from the runtime image. A label records the UI revision; the image's `uv.lock` records the APB versions and the report application's commit. The publication workflow publishes linux/arm64 and linux/amd64 images on UI version tags or manual dispatch; normal quality runs do not publish images.

## Run the published image

```bash
mkdir -p apb-export/examples apb-export/store
docker run --rm -v "$PWD/apb-export/examples:/examples" \
  --entrypoint apb-export-web ghcr.io/anndata-omics-bridge/apb-export-ui:v0.3.0 \
  examples index /examples
docker run -d --name apb-export -p 8770:8000 \
  -v "$PWD/apb-export/store:/data/store" -v "$PWD/apb-export/examples:/examples:ro" \
  ghcr.io/anndata-omics-bridge/apb-export-ui:v0.3.0 /examples
```

Open http://localhost:8770. The server listens on port 8000 inside the container; `-p 8770:8000` publishes it on the host's port 8770, and `-p 127.0.0.1:8770:8000` keeps it to this computer. The first command indexes an empty examples folder with the image's own packages, since `serve` refuses an index built elsewhere; rerun it after changing the image tag. Jobs and uploads stay in `apb-export/store`. `docker stop apb-export` stops the app, and `docker start apb-export` starts it again. Unlike the PyPI install, the image includes the pMultiQC report.

## Deployment interface

| Item | Configuration |
| --- | --- |
| Entrypoint | `apb-export-web serve --host 0.0.0.0 --port 8000 --store /data/store` |
| Arguments | `/examples --max-upload-mb 2048 --ttl-hours 24 --timeout-minutes 60` |
| Job store | `/data/store`, writable |
| Temporary uploads | `/data/tmp`, writable disk, set through `TMPDIR` |
| Example data | `/examples`, a staged and indexed directory, read-only; indexed with the image's installed APB commits |
| Health endpoint | `GET /api/options.json` |
| Public URL | https://apps-dev.bfabric.org/apb-export/ |

The proxy strips the public path prefix and redirects its bare prefix to a trailing slash. Frontend assets and API calls stay relative. The smoke checks exercise this through a local stripping proxy.

## Migration and rollback

1. Keep the currently deployed image reference and store/example mounts
2. Test the new UI image before changing the FGCZ portal descriptor
3. Stop the old service before starting the UI image against the same store; never share one writable store between concurrent services
4. Change only the image reference to a tested UI image; retain the public URL, command arguments and mounts
5. Verify options, uploads, QC and downloads; restore the previous image reference if rollback is needed

Completed jobs retain their existing layout. On restart, existing unfinished jobs are marked failed as before. The extraction does not deploy or publish a production image.

## Examples

`apb-export-web examples build` stages the packaged web selection plus five supplementary examples; `make web-examples` delegates to the same command. Optional positional arguments select the destination directory and APB workspace; dataset keys resolve through Studio's managed fixture manifest. The selection includes the two complete FGCZ MaxQuant DDA folders from Studio's `apb_examples` inventory and excludes peptide-entrapment data. Selection, supplementary metadata and annotations ship with this package. The build ends by indexing the folder for the installation that ran it; the server refuses an index from other APB commits, so stage with the locked environment of the image you deploy, or rerun `apb-export-web examples index` with it.

Text tables and annotations are unpacked from gzip without changing their contents. No real fixtures are committed.

The [complete MetaMorpheus/IonStar example](metamorpheus-example.md) comes from the shared APB Zenodo collection through APB Studio's Fixture Manager. Acquire the `routine` or `apb_examples` inventory in Studio before staging. The UI has no dataset downloader or feature-sampling step.
