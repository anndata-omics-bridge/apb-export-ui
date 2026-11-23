#!/bin/sh
# Install the APB Export web app with uv from PyPI, then start it; run it again to start the app.
# Arguments go to `apb-export-web start`, such as --port 8771 or --no-browser.
set -eu
export PATH="$HOME/.local/bin:$PATH"
if ! command -v uv >/dev/null 2>&1; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
fi
uv tool install --python 3.13 --with-executables-from apb2,apb-export,apb-fasta apb-export-ui==0.3.1
exec "$(uv tool dir --bin)/apb-export-web" start "$@"
