"""An examples folder's index, written once when the examples are staged: what the page offers
with the installed toolchain, the example list and each example file's preview. The server only
reads it, so starting it runs no exporter.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from apb_export_ui.web.examples import (
    Example,
    load_examples,
    read_examples,
    write_examples,
    write_previews,
)
from apb_export_ui.web.exports import load_hints, rule_versions
from apb_export_ui.web.options import options_index, read_outputs
from apb_export_ui.web.store import Output, write_json

OPTIONS = "options.json"
EXAMPLES = "examples.json"
PREVIEWS = "previews"


def build_index(folder: Path) -> list[Example]:
    """Write the index into a staged examples folder; one without ``examples.csv`` offers none.

    Returns:
        The examples it lists.
    """
    folder = folder.absolute()
    folder.mkdir(parents=True, exist_ok=True)
    index = options_index()
    write_json(folder / OPTIONS, index)
    corpus = folder / "examples.csv"
    offered = (
        load_examples(
            corpus,
            folder / "data",
            folder / "sdrf",
            index["software"],
            load_hints()[1],
            rule_versions(),
        )
        if corpus.is_file()
        else []
    )
    write_examples(folder / EXAMPLES, offered, folder)
    write_previews(folder / PREVIEWS, offered)
    return offered


def read_index(folder: Path) -> tuple[dict[str, Any], list[str], list[Output], list[Example]]:
    """The index, the software and outputs it offers, and its examples.

    Raises:
        FileNotFoundError: The folder holds no index.
        ValueError: The index was built with another toolchain than the one installed.
    """
    folder = folder.absolute()
    if not (folder / OPTIONS).is_file():
        raise FileNotFoundError(
            f"{folder} holds no {OPTIONS}; run `apb-export-web examples index {folder}`"
        )
    index = json.loads((folder / OPTIONS).read_text(encoding="utf-8"))
    software, outputs = read_outputs(index)
    return index, software, outputs, read_examples(folder / EXAMPLES, folder)
