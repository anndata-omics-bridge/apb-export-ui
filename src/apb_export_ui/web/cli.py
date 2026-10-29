"""``apb-export-web``: serve the upload-and-convert page on one host and port."""

from __future__ import annotations

import errno
import os
import shutil
import socket
from pathlib import Path
from typing import Annotated

import psutil
import uvicorn
from cyclopts import App, Parameter
from loguru import logger

from apb_export_ui.web.example_build import EXAMPLE_DATA, collect
from apb_export_ui.web.index import EXAMPLES, OPTIONS, PREVIEWS, build_index, read_index
from apb_export_ui.web.options import EXPLOREDE_URL, write_options
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
    """Build the packaged web selection from Studio's managed fixtures, then index it."""
    studio = workspace / "apb_studio"
    collect(
        EXAMPLE_DATA / "datasets.csv",
        studio / "test_data_download",
        workspace / "apb-proteobench/src/apb_proteobench/data/modules",
        directory,
        extra=EXAMPLE_DATA / "examples.csv",
        workspace=workspace,
        fastas=studio / "workflow_tables/workflow_proteobench.csv",
    )
    index_examples(directory)


@examples_app.command(name="index")
def index_examples(
    directory: Annotated[Path, Parameter(help="Staged examples directory")] = DEFAULT_EXAMPLES,
    /,
) -> None:
    """Write what the page offers with this installation, the example list and the file
    previews into a staged examples directory; one without examples.csv offers no examples."""
    offered = build_index(directory)
    logger.info(f"Indexed {len(offered)} examples in {directory.resolve()}")


@app.command
def serve(
    examples: Annotated[
        Path | None,
        Parameter(help="Indexed examples directory; defaults to the nearest build/web-examples"),
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
    explorede_url: Annotated[
        str, Parameter(help="exploreDE app that Open in exploreDE passes a result's URL to")
    ] = EXPLOREDE_URL,
) -> None:
    """Start the web app on an indexed examples directory, restarting an existing app on the
    same address. Starting reads the index; it runs no exporter."""
    if examples is None:
        working_directory = Path.cwd()
        examples = next(
            (
                root / DEFAULT_EXAMPLES
                for root in (working_directory, *working_directory.parents)
                if (root / DEFAULT_EXAMPLES / OPTIONS).is_file()
            ),
            None,
        )
    if examples is None:
        raise SystemExit(
            "No indexed examples found; run `apb-export-web examples build` or `index`"
        )
    try:
        index, software, outputs, offered = read_index(examples)
    except (FileNotFoundError, ValueError) as error:
        raise SystemExit(str(error)) from error
    _restart_existing(host, port)
    jobs = JobStore(store, ttl_seconds=ttl_hours * 3600)
    jobs.interrupt_unfinished()
    jobs.expire()
    max_upload_bytes = max_upload_mb * 1024 * 1024
    write_options(jobs.options_path, index, max_upload_bytes, explorede_url)
    shutil.copyfile(examples / EXAMPLES, jobs.examples_path)
    shutil.rmtree(jobs.previews, ignore_errors=True)
    shutil.copytree(examples / PREVIEWS, jobs.previews)
    logger.info(f"Loaded {len(offered)} examples from {examples.resolve()}")
    worker = Worker(jobs, timeout_seconds=timeout_minutes * 60)
    app = create_app(jobs, worker, outputs, software, max_upload_bytes, offered)
    uvicorn.run(app, host=host, port=port)


def main() -> None:
    """Run the command line and exit with its status."""
    app()
