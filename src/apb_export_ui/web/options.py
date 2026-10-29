"""What the page offers: vendor software and outputs, indexed once with the examples, then the
server's own settings, the upload limit and viewer apps, added when it starts."""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import asdict
from importlib.metadata import distribution, version
from pathlib import Path
from typing import Any

from apb2.api import get_rules
from apb_export.api import Exporter

from apb_export_ui.web.exports import load_hints
from apb_export_ui.web.store import Output, write_json

EXPLOREDE_URL = "https://shiny-public.fgcz.uzh.ch/app/exploreDE/"
"""Peter Leary's exploreDE, which opens an exploreDE export given its URL as ``?data=``."""

# The toolchain an index describes; the server refuses an index built with another.
_PACKAGES = ("apb-export", "apb2", "apb-pmultiqc", "pmultiqc")

# apb2's --format values and what each writes.
_APB2_FORMATS = (
    ("hdf5", "APB2 result: h5ad or h5mu"),
    ("parquet", "APB2 result: Parquet folder (zip)"),
    ("duckdb", "APB2 result: DuckDB"),
)


def command(name: str) -> Path:
    """A console script installed beside this interpreter.

    Raises:
        FileNotFoundError: The script is not installed in this environment.
    """
    path = Path(sys.executable).with_name(name)
    if not path.is_file():
        raise FileNotFoundError(f"{name} is not installed beside {sys.executable}")
    return path


def software() -> list[str]:
    """Every software with a packaged quant-result rule, DDA and DIA together."""
    names = {rules.software_name for category in ("DDA", "DIA") for rules in get_rules(category)}
    return sorted(names, key=str.casefold)


def _help(target: str) -> str:
    """The target's subcommand help, which names the options it takes; asked once per target,
    since each call starts the exporter."""
    shown = subprocess.run(
        [command("apb-export"), target, "--help"],
        capture_output=True,
        text=True,
        check=True,
    )
    return shown.stdout


def outputs() -> list[Output]:
    """apb-export's targets ``outputs.json`` describes first, then APB2's own result formats.

    A target an installed plugin adds is not offered: the page describes only its own.
    """
    described = about()
    helps = {
        target: _help(target)
        for target in Exporter.targets()
        if f"apb-export:{target}" in described
    }
    targets = [
        Output(
            id=f"apb-export:{target}",
            label=f"{target} ({Exporter(target).extension})",
            command="apb-export",
            name=target,
            extension=Exporter(target).extension,
            annotation="--annotation" in shown,
            fasta="--fasta" in shown,
        )
        for target, shown in helps.items()
    ]
    formats = [
        Output(
            id=f"apb2:{name}",
            label=label,
            command="apb2",
            name=name,
            extension="",
            annotation=True,
            fasta=True,
        )
        for name, label in _APB2_FORMATS
    ]
    return targets + formats


ABOUT = Path(__file__).parent / "outputs.json"


def about() -> dict[str, dict[str, object]]:
    """What each output gives, which tool opens it and how, with links, by output id."""
    return json.loads(ABOUT.read_text(encoding="utf-8"))


def reads(output: Output) -> list[str]:
    """The levels an apb-export target reads, any of which it needs; none for an APB2 format,
    which writes whichever levels the result has."""
    return list(Exporter(output.name).levels) if output.command == "apb-export" else []


def installed() -> dict[str, str]:
    """Each toolchain package's installed Git commit, else its version."""
    found: dict[str, str] = {}
    for name in _PACKAGES:
        origin = distribution(name).read_text("direct_url.json")
        commit = json.loads(origin).get("vcs_info", {}).get("commit_id") if origin else None
        found[name] = commit or version(name)
    return found


def options_index() -> dict[str, Any]:
    """What the page offers with the installed toolchain: software, upload hints, outputs and
    their levels, and versions. Each target's help is read here, not when the server starts.

    Raises:
        ValueError: An offered output has no description in ``outputs.json``.
    """
    names, offered = software(), outputs()
    described = about()
    missing = [output.id for output in offered if output.id not in described]
    if missing:
        raise ValueError(f"{ABOUT} describes no output {missing}")
    return {
        "software": names,
        "hints": load_hints()[0],
        "outputs": [
            {**asdict(output), "about": described[output.id], "levels": reads(output)}
            for output in offered
        ],
        "versions": {name: version(name) for name in _PACKAGES},
        "installed": installed(),
    }


def read_outputs(index: dict[str, Any]) -> tuple[list[str], list[Output]]:
    """The software and outputs an index lists.

    Raises:
        ValueError: The index was built with another toolchain than the one installed.
    """
    if index["installed"] != installed():
        raise ValueError(
            f"the examples were indexed with {index['installed']}, not the installed "
            f"{installed()}; run `apb-export-web examples index` with this installation"
        )
    fields = ("id", "label", "command", "name", "extension", "annotation", "fasta")
    offered = [Output(**{field: entry[field] for field in fields}) for entry in index["outputs"]]
    return list(index["software"]), offered


def write_options(
    path: Path, index: dict[str, Any], max_upload_bytes: int, explorede_url: str = EXPLOREDE_URL
) -> None:
    """Write the page's ``options.json``: the index, the upload limit and the viewer apps.

    An output whose description names a ``viewer`` gets a link to that app, from ``viewers``.
    """
    write_json(
        path,
        {**index, "max_upload_bytes": max_upload_bytes, "viewers": {"exploreDE": explorede_url}},
    )
