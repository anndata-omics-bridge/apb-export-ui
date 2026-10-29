# Web app

`apb-export-web` without arguments shows Cyclopts help. `apb-export-web serve` starts the page that converts one vendor result and shows QC before download; `apb-export-web serve --help` lists server options.

## Inputs and outputs

- Inputs: a vendor result, an optional parameter file, an optional SDRF or prolfquapp sample table, an optional FASTA
- Outputs: any target on [APB Export targets](https://anndata-omics-bridge.github.io/apb-export/targets/), or an APB2 result as h5ad/h5mu, Parquet or DuckDB
- QC: intensity density per sample, CV per feature within each annotation group, detected and missing counts

## pMultiQC / QPX

Choose this output to convert the upload into an APB result and immediately run the locked `apb-pmultiqc` application. Optional sample annotation and FASTA verification run before the report; grouping, organism, FASTA and SDRF are not required. RT is resolved through APB Export's chromatography catalogue, never through web-specific vendor-column mappings.

After completion, **Open pMultiQC report** opens the self-contained HTML in a new tab. Downloads include `qpx.zip` (Parquet tables and exporter provenance), `pmultiqc_report.html`, and `pmultiqc.zip` (full report, data tables, logs and installed-source provenance). Only a completed job's listed report is served inline at `api/jobs/{id}/report`; deletion and expiry remove it with the job. Failures and timeouts remain failed jobs with a job log.

## exploreDE

Choose **exploreDE** to write one exploreDE file per level the result holds: protein, peptide and precursor. Each is its own download, `<input>_explorede_<level>.h5ad`, and **Open <level> in exploreDE** opens Peter Leary's [exploreDE](https://github.com/fgcz/exploreDE) in a new tab with the file's absolute URL as `?data=`. `serve --explorede-url` sets the app; the default is the public instance `https://shiny-public.fgcz.uzh.ch/app/exploreDE/`. exploreDE downloads the file itself, so the link works only from a server exploreDE can reach and accepts, such as `https://apps-dev.bfabric.org/apb-export/`.

```bash
uv sync --locked --group dev
uv run --locked apb-export-web examples build
uv run --locked apb-export-web serve
```

Staging requires the selected fixtures to be downloaded through APB Studio already. Start the server with `apb-export-web serve` and stop it with Ctrl-C.

`serve` searches the current directory and then its parents for `build/web-examples`, so starting from a checkout subdirectory loads the same bundle. An explicit positional directory selects another bundle. Startup logs the loaded count and directory, or a build reminder if no bundle is found.

If this app already owns the requested address, `serve` gracefully stops it and waits for the port before starting the replacement. The check verifies the listening socket, process owner and installed app entry point; an unrelated or unverifiable listener is left running, and startup exits before changing the job store.

The page asks for the software first, then shows the files it expects: result and parameter file names from ProteoBench's module documentation, packaged as `src/apb_export_ui/web/hints.json`, and whether the parameter file is required.

On desktop, Software and Files share the left column and Output fills the right. Convert opens a separate results view with a short summary, progress, downloads and full-width QC. Edit setup preserves the selected files and options; View conversion returns to the current job. Reloading a job URL reopens its results.

## Examples

`apb-export-web examples build` resolves the packaged [web selection](../src/apb_export_ui/web/example_data/datasets.csv) through the Fixture Manager's `downloads.csv` and writes a staged manifest under `build/web-examples`. MaxQuant offers two complete folders, FGCZ MaxQuant 2.0.1.0 searches of the ProteoBench Q Exactive and Astral DDA samples, each with evidence, modification-specific peptides, peptides, protein groups and `mqpar.xml`; peptide-entrapment datasets are excluded. `apb-export-web serve` reads that bundle automatically; the optional positional directory overrides its location.

`examples build [DIRECTORY] [WORKSPACE]` accepts optional positional destination and workspace roots; the defaults are `build/web-examples` and `..`. The builder ships its supplementary example metadata and annotations with the Python package.

Both MaxQuant folders use their ProteoBench module's SDRF, whose data files match the raw runs; each raw file is its own MaxQuant experiment, so the same annotation serves every level. Choose **+ sample annotation** to compute CV within conditions A and B. The selection's optional `sdrf` field names a CSV-relative annotation; staging puts it inside a folder input or beside a file input.

Examples can run three ways:

- Result file only
- With its parameter file
- With parameters and sample annotation

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
