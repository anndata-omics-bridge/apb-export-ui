# Deployment

The standalone image is `ghcr.io/anndata-omics-bridge/apb-export-ui`. It builds from this repository and its committed lock; no sibling source checkouts are required.

## Build and release

```bash
uv sync --locked --group dev
make check-full
make image IMAGE_TAG=local
```

The image builds the Lit/Vite frontend with Node 22, then installs the Python application using `uv sync --locked --no-dev --no-editable`. Node is absent from the runtime image. Labels record the UI, locked exporter and report-application revisions. The publication workflow publishes linux/arm64 and linux/amd64 images on UI version tags or manual dispatch; normal quality runs do not publish images.

## Existing deployment interface

| Item | Preserved value |
| --- | --- |
| Entrypoint | `apb-export-web --host 0.0.0.0 --port 8000 --store /data/store` |
| Arguments | `--max-upload-mb 2048 --ttl-hours 24 --timeout-minutes 60 --examples /examples/examples.csv --examples-root /examples/data --examples-sdrf /examples/sdrf` |
| Job store | `/data/store`, writable |
| Temporary uploads | `/data/tmp`, writable disk, set through `TMPDIR` |
| Example data | `/examples`, existing staged directory, read-only |
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

`make web-examples` stages the routine corpus plus five extra examples. Corpus dataset keys resolve through the Fixture Manager's `downloads.csv` under the configured data root; `--manifest` can name another manifest relative to that root or by absolute path. Text tables and annotations are unpacked from gzip without changing their contents. Existing deployed manifest and mount interfaces remain unchanged. No real fixtures are committed.

The [complete MetaMorpheus/IonStar example](metamorpheus-example.md) comes from the shared APB Zenodo collection through APB Studio's Fixture Manager. Acquire the `routine` or `apb_examples` inventory in Studio before staging. The UI has no dataset downloader or feature-sampling step.
