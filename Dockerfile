FROM node:22-bookworm-slim AS frontend
WORKDIR /frontend
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm test && npm run build

FROM ghcr.io/astral-sh/uv:0.12.17-python3.13-trixie-slim AS runtime
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH=/app/.venv/bin:$PATH
ARG UI_REVISION=unknown
ARG EXPORTER_REVISION=unknown
ARG REPORT_REVISION=unknown
LABEL org.opencontainers.image.source="https://github.com/anndata-omics-bridge/apb-export-ui" \
    org.opencontainers.image.revision=$UI_REVISION \
    org.anndata-omics-bridge.apb-export.revision=$EXPORTER_REVISION \
    org.anndata-omics-bridge.apb-pmultiqc.revision=$REPORT_REVISION
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src/ ./src/
COPY --from=frontend /src/apb_export_ui/web/static/ ./src/apb_export_ui/web/static/
RUN --mount=type=cache,target=/root/.cache/uv uv sync --locked --no-dev --no-editable
ENTRYPOINT ["apb-export-web", "--host", "0.0.0.0", "--port", "8000", "--store", "/data/store"]
EXPOSE 8000
