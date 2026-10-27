"""Cyclopts help never starts the server; serving is an explicit command."""

from __future__ import annotations

import csv
import socket
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from apb_export_ui.web.cli import app
from conftest import RUNS, write_diann


@pytest.mark.parametrize(
    "arguments,expected",
    [
        ([], "serve"),
        (["--help"], "examples"),
        (["serve", "--help"], "EXAMPLES"),
        (["examples"], "build"),
        (["examples", "--help"], "build"),
        (["examples", "build", "--help"], "DIRECTORY"),
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
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, use_default: bool, working_directory: str
) -> None:
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
    if not use_default:
        default = tmp_path / "build/web-examples"
        default.mkdir(parents=True)
        (default / "examples.csv").write_text(
            "input_file,vendor_parameter_file,module,software_name\n", encoding="utf-8"
        )

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
