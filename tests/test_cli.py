"""Cyclopts help never starts the server; serving is an explicit command."""

from __future__ import annotations

import csv
import json
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from apb_export_ui.web.cli import app
from apb_export_ui.web.index import build_index
from apb_export_ui.web.options import options_index
from conftest import RUNS, write_diann


@pytest.fixture(scope="module")
def index() -> dict[str, Any]:
    """What an index offers; built once, since it asks each target's --help."""
    return options_index()


@pytest.mark.parametrize(
    "arguments,expected",
    [
        ([], "serve"),
        (["--help"], "examples"),
        (["serve", "--help"], "EXAMPLES"),
        (["examples"], "build"),
        (["examples", "--help"], "build"),
        (["examples", "build", "--help"], "DIRECTORY"),
        (["examples", "index", "--help"], "DIRECTORY"),
        (["start", "--help"], "--no-browser"),
    ],
)
def test_help_exits_without_creating_a_store(
    tmp_path: Path, arguments: list[str], expected: str
) -> None:
    result = subprocess.run(
        [str(Path(sys.executable).with_name("apb-export-web")), *arguments],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=10,
        check=True,
    )

    assert "Usage:" in result.stdout
    assert expected in result.stdout
    assert "--examples" not in result.stdout
    if "serve" not in arguments:
        assert "--store" not in result.stdout
    assert "Started server process" not in result.stdout + result.stderr
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("use_default", [True, False])
@pytest.mark.parametrize("working_directory", ["", "build", "build/nested"])
def test_serve_offers_staged_inputs_from_the_default_or_explicit_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    index: dict[str, Any],
    use_default: bool,
    working_directory: str,
) -> None:
    monkeypatch.setattr("apb_export_ui.web.index.options_index", lambda: index)
    start = tmp_path / working_directory
    start.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(start)
    staged = tmp_path / ("build/web-examples" if use_default else "custom-examples")
    data = staged / "data"
    data.mkdir(parents=True)
    diann = write_diann(data)
    sdrf = staged / "sdrf"
    sdrf.mkdir()
    annotation = sdrf / "synthetic.sdrf.tsv"
    annotation.write_text(
        "comment[data file]\tfactor value[group]\n" + "".join(f"{run}\t{run[4]}\n" for run in RUNS),
        encoding="utf-8",
    )
    manifest = staged / "examples.csv"
    with manifest.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(("input_file", "vendor_parameter_file", "module", "software_name"))
        writer.writerow((diann.report.name, diann.log.name, "synthetic", "DIA-NN"))
    build_index(staged)
    if not use_default:
        build_index(tmp_path / "build/web-examples")

    served: list[FastAPI] = []
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = int(listener.getsockname()[1])

    def run(application: FastAPI, host: str, port: int) -> None:
        assert host == "127.0.0.1"
        with TestClient(application) as client:
            response = client.get("/api/examples.json")
            assert response.status_code == 200
            (example,) = response.json()["examples"]
            assert example["software"] == "DIA-NN"
            assert example["annotation"] == annotation.name
            for name, original in (
                (example["data"][0], diann.report),
                (annotation.name, annotation),
            ):
                download = client.get(f"/api/examples/{example['id']}/{name}")
                assert download.status_code == 200
                assert download.content == original.read_bytes()
        served.append(application)

    monkeypatch.setattr("apb_export_ui.web.cli.uvicorn.run", run)
    arguments = ["serve", "--store", str(tmp_path / "store"), "--port", str(port)]
    if not use_default:
        arguments.append(str(staged))
    with pytest.raises(SystemExit) as result:
        app(arguments)

    assert result.value.code == 0
    assert len(served) == 1


def test_serve_refuses_a_directory_without_an_index(tmp_path: Path) -> None:
    with pytest.raises(SystemExit, match="examples index"):
        app(["serve", str(tmp_path), "--store", str(tmp_path / "store")])
    assert not (tmp_path / "store").exists(), "refused before touching the store"


def _free_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, index: dict[str, Any]) -> Path:
    """A home directory for `start`, with the module's index standing in for a fresh one."""
    monkeypatch.setattr("apb_export_ui.web.index.options_index", lambda: index)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    return tmp_path / "APB-export"


def _start(monkeypatch: pytest.MonkeyPatch, arguments: list[str]) -> list[tuple[str, int]]:
    """Run `start` with uvicorn replaced; return the host and port it would serve on."""
    served: list[tuple[str, int]] = []

    def run(application: FastAPI, host: str, port: int) -> None:
        with TestClient(application) as client:
            assert client.get("/api/examples.json").json()["examples"] == []
        served.append((host, port))

    monkeypatch.setattr("apb_export_ui.web.cli.uvicorn.run", run)
    with pytest.raises(SystemExit) as result:
        app(["start", *arguments])
    assert result.value.code == 0
    return served


@pytest.mark.parametrize("existing", ["none", "stale"])
def test_start_indexes_a_missing_or_stale_index_and_serves_from_home(
    home: Path, monkeypatch: pytest.MonkeyPatch, index: dict[str, Any], existing: str
) -> None:
    if existing == "stale":
        build_index(home / "examples")
        options = home / "examples/options.json"
        stale = {**index, "installed": {**index["installed"], "apb-export": "0" * 40}}
        options.write_text(json.dumps(stale), encoding="utf-8")
    port = _free_port()

    served = _start(monkeypatch, ["--no-browser", "--port", str(port)])

    assert served == [("127.0.0.1", port)]
    written = json.loads((home / "examples/options.json").read_text(encoding="utf-8"))
    assert written["installed"] == index["installed"]
    assert (home / "options.json").is_file(), "the store is the home folder"
    assert (home / "jobs").is_dir()


def test_start_keeps_a_current_index(home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    build_index(home / "examples")
    indexed: list[Path] = []
    monkeypatch.setattr("apb_export_ui.web.cli.build_index", indexed.append)

    _start(monkeypatch, ["--no-browser", "--port", str(_free_port())])

    assert indexed == []


def test_start_opens_the_page_once_the_server_listens(
    home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    opened: list[str] = []
    monkeypatch.setattr("apb_export_ui.web.cli.webbrowser.open", opened.append)
    port = _free_port()

    def run(application: FastAPI, host: str, port: int) -> None:
        assert opened == [], "nothing opens before the server listens"
        with socket.socket() as listener:
            listener.bind((host, port))
            listener.listen()
            deadline = time.monotonic() + 10
            while not opened and time.monotonic() < deadline:
                time.sleep(0.05)

    monkeypatch.setattr("apb_export_ui.web.cli.uvicorn.run", run)
    with pytest.raises(SystemExit):
        app(["start", "--port", str(port)])

    assert opened == [f"http://127.0.0.1:{port}/"]
