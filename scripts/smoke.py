"""Exercise a clean installed wheel or a container, without source mounts or real fixtures."""

from __future__ import annotations

import argparse
import json
import os
import re
import socket
import subprocess
import tarfile
import tempfile
import threading
import time
import tomllib
from collections.abc import Generator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, override
from urllib.error import URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


def request(url: str, data: bytes | None = None, content_type: str = "") -> bytes:
    """Read one successful HTTP response."""
    headers = {"Content-Type": content_type} if content_type else {}
    with urlopen(Request(url, data=data, headers=headers), timeout=15) as response:
        return response.read()


@contextmanager
def prefixed(base: str) -> Generator[str]:
    """Emulate the deployed portal, stripping its prefix before forwarding requests."""

    class Proxy(BaseHTTPRequestHandler):
        def forward(self) -> None:
            assert self.path.startswith("/apb-export/")
            target = urljoin(base, self.path.removeprefix("/apb-export/"))
            length = int(self.headers.get("Content-Length", "0"))
            data = self.rfile.read(length) if length else None
            upstream = Request(
                target,
                data=data,
                headers={"Content-Type": self.headers.get("Content-Type", "")},
                method=self.command,
            )
            with urlopen(upstream, timeout=15) as response:
                self.send_response(response.status)
                self.send_header("Content-Type", response.headers.get("Content-Type", ""))
                self.end_headers()
                self.wfile.write(response.read())

        do_GET = forward
        do_POST = forward

        @override
        def log_message(self, format: str, *args: object) -> None:
            pass

    with ThreadingHTTPServer(("127.0.0.1", 0), Proxy) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield f"http://127.0.0.1:{server.server_port}/apb-export/"
        finally:
            server.shutdown()
            thread.join()


def multipart(output: str = "apb-export:proteopy") -> tuple[bytes, str]:
    """Build a small DIA-NN upload using only the standard library."""
    columns = (
        "Run",
        "Modified.Sequence",
        "Stripped.Sequence",
        "Precursor.Charge",
        "Precursor.Id",
        "Protein.Group",
        "Protein.Ids",
        "Protein.Names",
        "Genes",
        "Precursor.Quantity",
        "Precursor.Normalised",
        "Q.Value",
        "Global.Q.Value",
        "Lib.Q.Value",
        "PEP",
        "RT",
        "PG.MaxLFQ",
        "PG.Q.Value",
        "Lib.PG.Q.Value",
        "Global.PG.Q.Value",
    )
    rows = ["\t".join(columns)]
    for run in ("sample_1", "sample_2"):
        for index, sequence in enumerate(("PEPTIDEK", "SECONDK", "THIRDPEPK"), 1):
            values = (
                run,
                sequence,
                sequence,
                2,
                sequence + "2",
                f"P{index}",
                f"P{index}",
                f"P{index}",
                f"G{index}",
                1000 * index,
                900 * index,
                0.001,
                0.002,
                0,
                0.01,
                10,
                500 * index,
                0.001,
                0,
                0.002,
            )
            rows.append("\t".join(map(str, values)))
    boundary = "apb-ui-smoke-boundary"
    parts = []
    for name, filename, value in (
        ("output", None, output),
        ("software", None, "DIA-NN"),
        ("data", "report.tsv", "\n".join(rows) + "\n"),
        (
            "params",
            "report.log.txt",
            "DIA-NN 1.8.1 (Data-Independent Acquisition by Neural Networks)\n",
        ),
    ):
        disposition = f'Content-Disposition: form-data; name="{name}"'
        if filename:
            disposition += f'; filename="{filename}"'
        parts.append(f"--{boundary}\r\n{disposition}\r\n\r\n{value}\r\n")
    return ("".join(parts) + f"--{boundary}--\r\n").encode(), boundary


def wait_ready(base: str) -> None:
    """Wait for startup, failing after one minute."""
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        try:
            request(urljoin(base, "api/options.json"))
            return
        except (URLError, ConnectionError, TimeoutError):
            time.sleep(0.2)
    raise TimeoutError(f"UI did not start: {base}")


def exercise(base: str) -> None:
    """Check assets, options, conversion, QC and a downloaded HDF5 result through the prefix."""
    wait_ready(base)
    with prefixed(base) as public:
        page = request(public).decode()
        assets = [name for name in re.findall(r'(?:src|href)="([^"]+)"', page) if "assets/" in name]
        assert assets, "the wheel contains no frontend asset references"
        for asset in assets:
            assert request(urljoin(public, asset)), f"empty asset: {asset}"
        options = json.loads(request(urljoin(public, "api/options.json")))
        assert "apb-export:proteopy" in {output["id"] for output in options["outputs"]}
        data, boundary = multipart()
        job = json.loads(
            request(urljoin(public, "api/jobs"), data, f"multipart/form-data; boundary={boundary}")
        )["id"]
        deadline = time.monotonic() + 60
        status: dict[str, Any] = {}
        while time.monotonic() < deadline:
            status = json.loads(request(urljoin(public, f"api/jobs/{job}/status.json")))
            if status["state"] in ("done", "failed"):
                break
            time.sleep(0.2)
        assert status.get("state") == "done", status
        qc = json.loads(request(urljoin(public, f"api/jobs/{job}/qc.json")))
        assert qc["matrices"]
        assert all(matrix["features"] == 3 for matrix in qc["matrices"]), qc
        output = next(item["name"] for item in status["files"] if item["name"].endswith(".h5ad"))
        downloaded = request(urljoin(public, f"api/jobs/{job}/files/{output}"))
        assert downloaded.startswith(b"\x89HDF\r\n\x1a\n"), "download is not an HDF5 result"
        print("Assets, prefixed routes, synthetic conversion, QC and HDF5 download passed")
        data, boundary = multipart("apb-export:qpx")
        job = json.loads(
            request(urljoin(public, "api/jobs"), data, f"multipart/form-data; boundary={boundary}")
        )["id"]
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            status = json.loads(request(urljoin(public, f"api/jobs/{job}/status.json")))
            if status["state"] in ("done", "failed"):
                break
            time.sleep(0.2)
        assert status.get("state") == "done", status
        assert {item["name"] for item in status["files"]} == {
            "pmultiqc.zip",
            "pmultiqc_report.html",
            "qpx.zip",
        }
        with urlopen(urljoin(public, f"api/jobs/{job}/report"), timeout=15) as report:
            assert report.headers["Content-Type"].startswith("text/html")
            assert report.read() == request(
                urljoin(public, f"api/jobs/{job}/files/pmultiqc_report.html")
            )
        archive = request(urljoin(public, f"api/jobs/{job}/files/qpx.zip"))
        assert archive.startswith(b"PK"), "QPX tables are not a ZIP archive"
        print("Prefixed pMultiQC report, HTML download and QPX ZIP passed")


def installed_check() -> str:
    """Return a standard-library-only assertion script for the installed dependency graph."""
    dependencies = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["dependencies"]
    expected = {
        entry.split(" @ ")[0]: entry.rsplit("@", 1)[1]
        for entry in dependencies
        if " @ git+" in entry
    }
    return f"""
import importlib.metadata as metadata
import json
expected = {expected!r}
for name, revision in expected.items():
    distribution = metadata.distribution(name)
    direct = json.loads(distribution.read_text("direct_url.json"))
    assert not direct.get("dir_info", {{}}).get("editable", False), (name, direct)
    assert direct["vcs_info"]["commit_id"] == revision, (name, direct)
owners = [d.metadata["Name"] for d in metadata.distributions() if any(e.name == "apb-export-web" and e.group == "console_scripts" for e in d.entry_points)]
assert owners == ["apb-export-ui"], owners
import apb_export_ui
assert {str(ROOT)!r} not in apb_export_ui.__file__, apb_export_ui.__file__
print("Isolated installation owns the web executable and matches all declared Git pins")
"""


def wheel_smoke() -> None:
    """Install the lock and wheel into a fresh environment outside the checkout."""
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    stem = f"{project['name'].replace('-', '_')}-{project['version']}"
    wheel = ROOT / "dist" / f"{stem}-py3-none-any.whl"
    with tarfile.open(ROOT / "dist" / f"{stem}.tar.gz") as archive:
        names = archive.getnames()
        assert not any("node_modules" in name or "__pycache__" in name for name in names)
        for required in ("web/package.json", "web/package-lock.json", "web/src/app.ts", "uv.lock"):
            assert any(name.endswith("/" + required) for name in names), required
    with tempfile.TemporaryDirectory(prefix="apb-ui-wheel-") as directory:
        folder = Path(directory)
        environment = folder / "venv"
        subprocess.run(["uv", "venv", "--python", "3.13", str(environment)], check=True)
        exported = subprocess.check_output(
            ["uv", "export", "--locked", "--no-dev", "--no-emit-project", "--no-hashes"], cwd=ROOT
        )
        requirements = folder / "requirements.txt"
        requirements.write_bytes(exported)
        python = environment / "bin/python"
        subprocess.run(
            [
                "uv",
                "pip",
                "install",
                "--python",
                str(python),
                "--no-deps",
                "-r",
                str(requirements),
                str(wheel),
            ],
            check=True,
        )
        subprocess.run([str(python), "-c", installed_check()], cwd=folder, check=True)
        examples = folder / "examples"
        subprocess.run(
            [str(environment / "bin/apb-export-web"), "examples", "index", str(examples)],
            cwd=folder,
            check=True,
        )
        with socket.socket() as available:
            available.bind(("127.0.0.1", 0))
            port = available.getsockname()[1]
        with (folder / "server.log").open("w+") as log:
            process = subprocess.Popen(
                [
                    str(environment / "bin/apb-export-web"),
                    "serve",
                    str(examples),
                    "--port",
                    str(port),
                    "--store",
                    str(folder / "store"),
                ],
                cwd=folder,
                stdout=log,
                stderr=subprocess.STDOUT,
            )
            try:
                exercise(f"http://127.0.0.1:{port}/")
            finally:
                process.terminate()
                process.wait(timeout=10)
                log.seek(0)
                print(log.read())


def container_smoke(image: str) -> None:
    """Index an empty examples directory with the image, then run the image on it read-only,
    without source mounts, and exercise the same HTTP contract."""
    examples = Path(tempfile.mkdtemp(prefix="apb-ui-examples-"))
    owner = f"{os.getuid()}:{os.getgid()}"
    subprocess.run(
        [
            *("docker", "run", "--rm", "--user", owner, "--env", "HOME=/tmp"),
            *("--volume", f"{examples}:/examples", "--entrypoint", "apb-export-web"),
            *(image, "examples", "index", "/examples"),
        ],
        check=True,
    )
    container = subprocess.check_output(
        [
            *("docker", "run", "--detach", "--rm", "--publish", "127.0.0.1::8000"),
            *("--volume", f"{examples}:/examples:ro", image, "/examples"),
        ],
        text=True,
    ).strip()
    try:
        subprocess.run(["docker", "exec", container, "python", "-c", installed_check()], check=True)
        address = subprocess.check_output(
            ["docker", "port", container, "8000/tcp"], text=True
        ).strip()
        exercise(f"http://{address}/")
    finally:
        subprocess.run(["docker", "logs", container], check=True)
        subprocess.run(["docker", "stop", container], check=True)


def main() -> None:
    """Choose the wheel or container acceptance check."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("wheel", "container"))
    parser.add_argument("--image", default="ghcr.io/anndata-omics-bridge/apb-export-ui:local")
    args = parser.parse_args()
    if args.mode == "wheel":
        wheel_smoke()
    else:
        container_smoke(args.image)


if __name__ == "__main__":
    main()
