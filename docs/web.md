# Web app

`apb-export-web` without arguments shows Cyclopts help. `apb-export-web serve` starts the page that converts one vendor result and shows QC before download; `apb-export-web serve --help` lists server options.

## Inputs and outputs

- Inputs: a vendor result, an optional parameter file, an optional SDRF or prolfquapp sample table, an optional FASTA
- Outputs: any target on [APB Export targets](https://anndata-omics-bridge.github.io/apb-export/targets/), or an APB2 result as h5ad/h5mu, Parquet or DuckDB
- QC: intensity density per sample, CV per feature within each annotation group, detected and missing counts

## pMultiQC / QPX

Choose this output to convert the upload into an APB result and immediately run the locked `apb-pmultiqc` application. Optional sample annotation and FASTA verification run before the report; grouping, organism, FASTA and SDRF are not required. RT is resolved through APB Export's chromatography catalogue, never through web-specific vendor-column mappings.

After completion, **Open pMultiQC report** opens the self-contained HTML in a new tab. Downloads include `qpx.zip` (Parquet tables and exporter provenance), `pmultiqc_report.html`, and `pmultiqc.zip` (full report, data tables, logs and installed-source provenance). Only a completed job's listed report is served inline at `api/jobs/{id}/report`; deletion and expiry remove it with the job. Failures and timeouts remain failed jobs with a job log.

```bash
uv sync --locked --group dev
uv run --locked apb-export-web examples build
uv run --locked apb-export-web serve
```

Staging requires APB Studio's routine fixtures to be downloaded already. Start the server with `apb-export-web serve` and stop it with Ctrl-C.

`serve` loads the default built examples automatically when available. If no example bundle has been built, it serves uploads only; an explicit positional directory selects another bundle.

If this app already owns the requested address, `serve` gracefully stops it and waits for the port before starting the replacement. The check verifies the listening socket, process owner and installed app entry point; an unrelated or unverifiable listener is left running, and startup exits before changing the job store.

The page asks for the software first, then shows the files it expects: result and parameter file names from ProteoBench's module documentation, packaged as `src/apb_export_ui/web/hints.json`, and whether the parameter file is required.

## Examples

`apb-export-web examples build` resolves Studio's `dataset,note` inventory through the Fixture Manager's `downloads.csv` and writes a staged manifest under `build/web-examples`. `apb-export-web serve` reads that bundle automatically; the optional positional directory overrides its location.

`examples build [DIRECTORY] [WORKSPACE]` accepts optional positional destination and workspace roots; the defaults are `build/web-examples` and `..`. The builder ships its supplementary example metadata and annotations with the Python package.

Examples can run three ways:

- Result file only
- With its parameter file
- With parameters and SDRF

The server uses the sample annotation beside the input, or the module annotation staged with the examples. It links the chosen files into the job instead of uploading them; the data stays where the corpus keeps it.

At startup it writes the first 20 lines of every example file to the store, and the page shows them when a file name is clicked.

## Jobs

- Each upload becomes a job folder
- One worker runs the installed conversion and report commands in its own process group
- The worker writes `status.json`, `qc.json` and the downloads; the server only serves them
- Finished jobs are deleted after `--ttl-hours`

The page is a Lit/Vite project in `web/`; `make web` rebuilds its bundle into `src/apb_export_ui/web/static`, which the wheel ships, so no Node runs in production.

## Deploy

Releasing the image, staging the examples and running the container: [Deployment](deploy.md).
