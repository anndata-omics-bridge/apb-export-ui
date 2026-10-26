# Web app

`apb-export-web` serves a page that converts one vendor result and shows QC before download.

## Inputs and outputs

- Inputs: a vendor result, an optional parameter file, an optional SDRF or prolfquapp sample table, an optional FASTA
- Outputs: any target on [APB Export targets](https://anndata-omics-bridge.github.io/apb-export/targets/), or an APB2 result as h5ad/h5mu, Parquet or DuckDB
- QC: intensity density per sample, CV per feature within each annotation group, detected and missing counts

## pMultiQC / QPX

Choose this output to convert the upload into an APB result and immediately run the locked `apb-pmultiqc` application. Optional sample annotation and FASTA verification run before the report; grouping, organism, FASTA and SDRF are not required. RT is resolved through APB Export's chromatography catalogue, never through web-specific vendor-column mappings.

After completion, **Open pMultiQC report** opens the self-contained HTML in a new tab. Downloads include `qpx.zip` (Parquet tables and exporter provenance), `pmultiqc_report.html`, and `pmultiqc.zip` (full report, data tables, logs and installed-source provenance). Only a completed job's listed report is served inline at `api/jobs/{id}/report`; deletion and expiry remove it with the job. Failures and timeouts remain failed jobs with a job log.

```bash
uv sync --locked --group dev
uv run --locked apb-export-web --store ./web-store --port 8770
```

The page asks for the software first, then shows the files it expects: result and parameter file names from ProteoBench's module documentation, packaged as `src/apb_export_ui/web/hints.json`, and whether the parameter file is required.

## Examples

`--examples corpus.csv --examples-root DIR` offers one row per software of an APB Studio corpus CSV, three ways:

- Result file only
- With its parameter file
- With parameters and SDRF

The SDRF is an `sdrf.tsv` beside the input, else `<module>.sdrf.tsv` from `--examples-sdrf DIR`. The server links the chosen files into the job instead of uploading them; the data stays where the corpus keeps it. At startup it writes the first 20 lines of every example file to the store, and the page shows them when a file name is clicked.

## Jobs

- Each upload becomes a job folder
- One worker runs the installed conversion and report commands in its own process group
- The worker writes `status.json`, `qc.json` and the downloads; the server only serves them
- Finished jobs are deleted after `--ttl-hours`

The page is a Lit/Vite project in `web/`; `make web` rebuilds its bundle into `src/apb_export_ui/web/static`, which the wheel ships, so no Node runs in production.

## Deploy

Releasing the image, staging the examples and running the container: [Deployment](deploy.md).
