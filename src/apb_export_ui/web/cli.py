"""``apb-export-web``: serve the upload-and-convert page on one host and port."""

from __future__ import annotations

import errno
import os
import socket
from pathlib import Path
from typing import Annotated

import psutil
import uvicorn
from cyclopts import App, Parameter
from loguru import logger

from apb_export_ui.web.example_build import EXAMPLE_DATA, collect
from apb_export_ui.web.examples import load_examples, write_examples, write_previews
from apb_export_ui.web.exports import load_hints, rule_versions
from apb_export_ui.web.options import write_options
from apb_export_ui.web.server import Worker, create_app
from apb_export_ui.web.store import JobStore

app = App(
    name="apb-export-web",
    help="Serve a page that converts uploaded vendor results and shows their QC.",
)
examples_app = App(name="examples", help="Prepare example data for the web app.")
app.command(examples_app)
DEFAULT_EXAMPLES = Path("build/web-examples")


def _port_available(host: str, port: int) -> bool:
    for family, kind, protocol, _, address in socket.getaddrinfo(
        host, port, type=socket.SOCK_STREAM
    ):
        with socket.socket(family, kind, protocol) as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                probe.bind(address)
            except OSError as error:
                if error.errno == errno.EADDRINUSE:
                    return False
                raise
    return True


def _is_app(process: psutil.Process) -> bool:
    command = process.cmdline()
    if len(command) < 2 or Path(command[1]).name != "apb-export-web":
        return False
    try:
        script = Path(command[1]).read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return False
    return "from apb_export_ui.web.cli import main" in script


def _restart_existing(host: str, port: int) -> None:
    if _port_available(host, port):
        return
    addresses = {
        address[0]
        for _, _, _, _, address in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    }
    wildcard = {"0.0.0.0", "::"}
    username = psutil.Process().username()
    for process in psutil.process_iter():
        try:
            if process.pid == os.getpid() or process.username() != username or not _is_app(process):
                continue
            listeners = [
                connection
                for connection in process.net_connections(kind="tcp")
                if connection.status == psutil.CONN_LISTEN
                and connection.laddr
                and connection.laddr.port == port
                and (
                    connection.laddr.ip in addresses
                    or connection.laddr.ip in wildcard
                    or bool(addresses & wildcard)
                )
            ]
            if not listeners:
                continue
            logger.info(f"Restarting apb-export-web process {process.pid} on {host}:{port}")
            process.terminate()
            try:
                process.wait(timeout=10)
            except psutil.TimeoutExpired as error:
                raise SystemExit(
                    f"Existing app process {process.pid} did not stop within 10 seconds"
                ) from error
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
        if _port_available(host, port):
            return
    raise SystemExit(
        f"Port {host}:{port} is occupied by another or unverified application; left it running"
    )


@examples_app.command(name="build")
def build_examples(
    directory: Annotated[Path, Parameter(help="Destination examples directory")] = DEFAULT_EXAMPLES,
    workspace: Annotated[
        Path, Parameter(help="APB workspace containing Studio and fixtures")
    ] = Path(".."),
    /,
) -> None:
    """Build examples from Studio's routine inventory and packaged supplementary metadata."""
    studio = workspace / "apb_studio"
    collect(
        studio / "corpuses/routine.csv",
        studio / "test_data_download",
        workspace / "apb-proteobench/src/apb_proteobench/data/modules",
        directory,
        extra=EXAMPLE_DATA / "examples.csv",
        workspace=workspace,
        fastas=studio / "workflow_tables/workflow_proteobench.csv",
    )


@app.command
def serve(
    examples: Annotated[
        Path | None, Parameter(help="Examples directory; defaults to built examples when available")
    ] = None,
    /,
    *,
    store: Annotated[Path, Parameter(help="Directory for options and job folders")] = Path(
        "apb-export-web"
    ),
    host: Annotated[str, Parameter(help="Interface to listen on")] = "127.0.0.1",
    port: Annotated[int, Parameter(help="Port to listen on")] = 8770,
    max_upload_mb: Annotated[int, Parameter(help="Largest upload, all files together")] = 4096,
    ttl_hours: Annotated[float, Parameter(help="Delete finished jobs after this long")] = 24.0,
    timeout_minutes: Annotated[float, Parameter(help="Fail a job running longer")] = 60.0,
) -> None:
    """Start the web app, restarting an existing app on the same address."""
    if examples is None:
        working_directory = Path.cwd()
        examples = next(
            (
                root / DEFAULT_EXAMPLES
                for root in (working_directory, *working_directory.parents)
                if (root / DEFAULT_EXAMPLES / "examples.csv").is_file()
            ),
            None,
        )
    _restart_existing(host, port)
    jobs = JobStore(store, ttl_seconds=ttl_hours * 3600)
    jobs.interrupt_unfinished()
    jobs.expire()
    max_upload_bytes = max_upload_mb * 1024 * 1024
    software, outputs = write_options(jobs.options_path, max_upload_bytes)
    offered = (
        []
        if examples is None
        else load_examples(
            examples / "examples.csv",
            examples / "data",
            examples / "sdrf",
            software,
            load_hints()[1],
            rule_versions(),
        )
    )
    if examples is None:
        logger.warning("No built examples found; run `apb-export-web examples build`")
    else:
        logger.info(f"Loaded {len(offered)} examples from {examples.resolve()}")
    write_examples(jobs.examples_path, offered)
    write_previews(jobs.previews, offered)
    worker = Worker(jobs, timeout_seconds=timeout_minutes * 60)
    app = create_app(jobs, worker, outputs, software, max_upload_bytes, offered)
    uvicorn.run(app, host=host, port=port)


def main() -> None:
    """Run the command line and exit with its status."""
    app()
