"""A serve invocation replaces this app, never an unrelated listener."""

from __future__ import annotations

import json
import signal
import socket
import subprocess
import sys
import time
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

import pytest

from apb_export_ui.web.index import build_index

COMMAND = str(Path(sys.executable).with_name("apb-export-web"))


@pytest.fixture(scope="module")
def indexed(tmp_path_factory: pytest.TempPathFactory) -> str:
    """An indexed examples directory without examples; indexed once, as it asks each target."""
    folder = tmp_path_factory.mktemp("examples")
    build_index(folder)
    return str(folder)


def _port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


@contextmanager
def _process(command: list[str], folder: Path, log: Path) -> Generator[subprocess.Popen[bytes]]:
    with log.open("w") as output:
        process = subprocess.Popen(
            command,
            cwd=folder,
            stdin=subprocess.DEVNULL,
            stdout=output,
            stderr=subprocess.STDOUT,
        )
        try:
            yield process
        finally:
            if process.poll() is None:
                process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


def _ready(process: subprocess.Popen[bytes], url: str, log: Path) -> bytes:
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        assert process.poll() is None, log.read_text()
        try:
            with urlopen(url, timeout=1) as response:
                return response.read()
        except URLError:
            time.sleep(0.05)
    pytest.fail(f"Server did not become ready: {log.read_text()}")


def test_serve_restarts_the_existing_app_on_the_same_port(tmp_path: Path, indexed: str) -> None:
    port = _port()
    url = f"http://127.0.0.1:{port}/api/options.json"
    old_log, new_log = tmp_path / "old.log", tmp_path / "new.log"
    with _process(
        [COMMAND, "serve", indexed, "--port", str(port), "--store", str(tmp_path / "old")],
        tmp_path,
        old_log,
    ) as old:
        _ready(old, url, old_log)
        assert json.loads(_ready(old, f"http://127.0.0.1:{port}/api/examples.json", old_log)) == {
            "examples": []
        }
        with _process(
            [
                COMMAND,
                "serve",
                indexed,
                "--port",
                str(port),
                "--store",
                str(tmp_path / "new"),
                "--max-upload-mb",
                "2",
            ],
            tmp_path,
            new_log,
        ) as new:
            assert old.wait(timeout=30) in (0, -signal.SIGTERM)
            assert "Application shutdown complete" in old_log.read_text()
            options = json.loads(_ready(new, url, new_log))
            assert options["max_upload_bytes"] == 2 * 1024 * 1024
            assert new.poll() is None
            assert f"Restarting apb-export-web process {old.pid}" in new_log.read_text()


@pytest.mark.parametrize("same_name", [False, True])
def test_serve_leaves_an_unrelated_listener_and_the_store_untouched(
    tmp_path: Path, indexed: str, same_name: bool
) -> None:
    port = _port()
    url = f"http://127.0.0.1:{port}/"
    log = tmp_path / "unrelated.log"
    command = [sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1"]
    if same_name:
        script = tmp_path / "apb-export-web"
        script.write_text(
            "import sys\n"
            "from http.server import HTTPServer, SimpleHTTPRequestHandler\n"
            "HTTPServer(('127.0.0.1', int(sys.argv[1])), SimpleHTTPRequestHandler).serve_forever()\n",
            encoding="utf-8",
        )
        command = [sys.executable, str(script), str(port)]
    store = tmp_path / "unused-store"
    with _process(command, tmp_path, log) as unrelated:
        _ready(unrelated, url, log)

        result = subprocess.run(
            [COMMAND, "serve", indexed, "--port", str(port), "--store", str(store)],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 1
        assert "left it running" in result.stderr
        assert "Started server process" not in result.stdout + result.stderr
        assert not store.exists()
        assert unrelated.poll() is None
        _ready(unrelated, url, log)
