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
