# Complete MetaMorpheus example

The web example uses the complete IonStar quantification table: 798,879 original rows, 26 columns, 20 runs and 255,817,791 uncompressed bytes. All five E. coli spike-in levels in a human background are retained, with four technical replicate runs each. There is no feature sampling or condition filtering.

## Source and acquisition

- Shared collection: [APB quantitative proteomics example datasets, version 1](https://doi.org/10.5281/zenodo.23691153), CC0
- Original archive: [PXD057758](https://www.ebi.ac.uk/pride/archive/projects/PXD057758), [Solivais et al., 2025](https://doi.org/10.1021/acs.jproteome.5c00065); original experiment [PXD003881](https://www.ebi.ac.uk/pride/archive/projects/PXD003881)
- Workflow: MetaMorpheus 1.0.7alpha identification followed by standalone FlashLFQ 1.3alpha quantification
- File: `IonStar_QuantResults-FlashLFQ_PIP_ECHO.zip` → `FlashLFQ_7772_Normed_Donor1_NoPip/QuantifiedPeaks.tsv`
- Original table SHA-256: `405d2ffdaa00cbfcaef7ecd4208fd9935837b5b655a7f5d3e89fcd62e874e35a`

APB Studio's Fixture Manager owns acquisition and verifies the pinned Zenodo files. Dataset key `zenodo/apb_examples/metamorpheus_ionstar` appears in both the shared `apb_examples` inventory and the 14-dataset `routine` inventory. It is not a ProteoBench scoring input and receives no benchmark FASTA. FlashLFQ settings are a companion file, not MetaMorpheus search parameters; no parameter upload is offered.

From APB Studio, run `uv run fixture download apb_examples` (or `routine`). Then run `apb-export-web examples build` from the UI repository.

Staging resolves corpus dataset keys through the managed `downloads.csv` manifest and copies complete files, unpacking gzip for web previews and conversion. The UI does not download or prepare scientific datasets itself; the former parser fixture and the 1,000-ion demonstration subset are not the active example.

## Scientific preservation

Zenodo stores the original table with gzip compression only, matching FlashLFQ settings, the unchanged public SDRF, a separately identified analysis SDRF, provenance and checksums. Decompressing the table must reproduce the original SHA-256. Neither publication nor web staging reorders rows, transforms intensities, fills missing values, or removes control records. Conversion applies the installed APB rules.

The analysis SDRF covers every run. It maps the original raw stem to the calibrated output run name and uses the public term's concentration/ratio (`CR`) as the spike-in factor. This minimal projection is an explicit workaround for the pMultiQC QPX reader interpreting every varying annotation column as a condition and semicolons as factor separators. Complete original metadata, including biological/technical replicate IDs and original filenames, remains in the original SDRF and provenance.

The archive directory's `NoPip` name must not be interpreted as disabling MBR: its preserved settings report normalization and match-between-runs enabled, with MBR FDR threshold 0.05. The source has RT columns. The locked APB2 MetaMorpheus rule (apb2 `45ffc2c`) reads them, and the locked apb-catalog (`f40edc0`) catalogues Peak RT Apex in minutes, so the QPX export carries RT, converted to seconds, into the report.

## Local migration

Keep the current store and pass the staged examples directory as the positional argument to `apb-export-web serve`. Stage the managed dataset under its new `zenodo/apb_examples/metamorpheus_ionstar` path and update only the active MetaMorpheus manifest row; preserve previous example directories because completed jobs link to their inputs. Restart only while the local worker is idle, then create a new report from the complete table. No production deployment is performed.
