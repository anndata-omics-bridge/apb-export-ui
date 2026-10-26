# Dependency policy

The UI is an application: commit its uv and npm lockfiles. Rebuilding a UI revision must install the same APB source revisions even when exporter development continues.

## Initial baseline

[The source snapshot](source-baseline.json) records committed APB revisions before extraction. Uncommitted sibling edits are excluded. The application manifest uses standard Git dependency URLs to pin all six APB packages to full immutable SHAs; its exporter revision is the extraction commit after removal of the old web executable.

The six packages are explicit application runtime requirements. Besides directly imported APIs and invoked CLIs, the application deliberately pins apb-catalog, protein-fasta and prozor to own the full APB toolchain selection. Development checks explain those application-only pins to deptry rather than relying on accidental transitive resolution.

## Upgrade

1. Choose tested, remotely reachable commits for the packages being upgraded and update their manifest source revisions
2. Run `uv lock`, review the dependency diff, then `uv sync --locked --group dev`
3. Run `make check-full`, including synthetic conversion with the installed CLIs
4. Commit manifest and lock together; release a new UI image separately

`tool.uv.no-sources = true` disables dependency packages’ development-only sibling path overrides. Standard Git dependency URLs remain active, so the application never interprets a sibling path as a directory inside another Git repository.

CI and image builds use locked synchronization and refuse a stale lockfile. APB source declarations contain neither local paths nor editable installs nor moving branch references. uv is pinned to 0.12.17 for development, CI and image builds.

Local sibling checkouts are unnecessary. Production installs non-editable packages, and the clean-wheel/container acceptance checks verify installed Git commit metadata and sole ownership of the web executable.

## Report environment (0.2.0)

The QPX/report integration deliberately updates the exporter, APB2 and catalogue to the commits tested by the standalone report application, and adds an immutable `apb-pmultiqc` source pin. The initial extraction snapshot above remains historical. The manifest and committed lock are the current source of truth.

`apb-pmultiqc` also pins MultiQC 1.35 and a tested pMultiQC source revision with the pending null-RT fix and pyOpenMS 3.5 compatibility, preserving Linux ARM builds. Its provenance and upstream status are documented in [the report application](https://github.com/anndata-omics-bridge/apb-pmultiqc/blob/main/docs/dependencies.md). The newer idXML peptide container is used in both search and consensus readers; QPX serialization remains in APB Export.

All web tests and installed wheel/container checks use tiny synthetic uploads. No corpus run, real vendor download or large-dataset report is part of the UI gates. Report-generation failures remain failed jobs rather than exposing a partial report link.
