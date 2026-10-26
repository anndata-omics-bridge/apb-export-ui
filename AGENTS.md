# APB Export UI — agent rules

The closest `AGENTS.md` wins. Explicit user instructions override this file.

## Verified commands

| Task | Command |
| --- | --- |
| Synchronize | `uv sync --locked --group dev` |
| Format | `make format` |
| Lint | `make lint` |
| Typecheck | `.venv/bin/pyright` |
| Dependencies | `.venv/bin/deptry .` |
| Tests | `.venv/bin/pytest --cov --cov-branch` |
| Build | `make build` |
| Full gate | `make check` |

## Code conventions

- Fully annotate every function and method in `src/` and `tests/`, including private functions, callbacks, generators, fixtures, and special methods.
- Standard Pyright strict and Ruff are mandatory. Do not create baselines, blanket exclusions, file-wide ignores, or unqualified `# type: ignore`.
- Ruff is the sole formatter and linter. Do not add Black, isort, Flake8, mypy, or another overlapping formatter/type checker.
- Keep `__init__.py` empty and import public objects from their defining modules.
- Use Google-style docstrings for public APIs and the configured 100-character line length.

## Dependency rules

### MUST

- Declare every imported runtime dependency directly in `[project.dependencies]`.
- Put tests, linting, typing, building, and documentation tools in dependency groups; optional user-facing capabilities belong in extras.
- Update `pyproject.toml` and run `make check`; the application commits `uv.lock` and uses immutable APB Git sources.

### SHOULD

- Prefer the standard library, then an existing direct dependency, then a small, maintained, typed dependency.
- Keep source independent of test, build, documentation, and CLI-only packages.

### MUST NOT

- Depend on unpinned branches or undeclared transitive dependencies.
- Add parallel manifests, lockfiles, formatters, type checkers, or test runners.
- Silence a dependency or typing defect instead of fixing its source.

## Workflow

1. Preserve unrelated worktree changes.
2. Add or update focused tests with each behavioral change.
3. Run the smallest relevant check while iterating.
4. Run `make check` before handoff and report its actual result.

## Application boundary

- This project owns the web frontend, HTTP server, job orchestration, QC presentation and deployment. Conversion remains in installed APB CLIs and sibling public APIs.
- Keep all frontend implementation in `apb_export_ui.web`; its internal imports stay inside that subsystem. Other APB packages are imported only through their `api` modules. No public library API is exposed here.
- Preserve `apb-export-web`, HTTP routes and persisted job formats during extraction.
- Commit both uv and npm lockfiles; never add sibling path sources or editable APB installations. Upgrade dependency revisions explicitly and run the full UI tests.
- `make check` includes frontend freshness and package checks; `make check-full` also checks a clean wheel installation and container execution.
- Real fixture data stays external. Tests and smoke checks synthesise their vendor input; no corpus run without the user's current request.
