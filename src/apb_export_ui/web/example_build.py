"""Stage managed fixtures, annotations and FASTAs as one web examples directory.

Corpus keys resolve through the Fixture Manager's manifest. Supplementary input sources
are workspace-relative; their annotation paths are relative to the supplementary CSV.
Gzip files are unpacked without changing their contents.
"""

from __future__ import annotations

import csv
import gzip
import shutil
from pathlib import Path

EXAMPLE_DATA = Path(__file__).with_name("example_data")

COLUMNS: tuple[str, ...] = (
    "input_file",
    "vendor_parameter_file",
    "module",
    "software_name",
    "fasta",
)


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _copy(source: Path, target: Path) -> None:
    """Copy one file, unpacking a ``.gz`` source whose target is not one."""
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.suffix == ".gz" and target.suffix != ".gz":
        with gzip.open(source, "rb") as packed, target.open("wb") as plain:
            shutil.copyfileobj(packed, plain)
    else:
        shutil.copy2(source, target)


def _corpus_rows(corpus: Path, manifest: Path) -> list[dict[str, str]]:
    """Resolve a curated inventory through the Fixture Manager's stored paths."""
    downloaded = {row["dataset"]: row for row in _rows(manifest)}
    rows: list[dict[str, str]] = []
    for selected in _rows(corpus):
        key = selected["dataset"]
        if key not in downloaded:
            raise ValueError(f"Unknown fixture dataset: {key}")
        held = downloaded[key]
        if not held["input_file_path"]:
            raise ValueError(f"Dataset not downloaded: {key}; run fixture download {corpus.stem}")
        rows.append(
            {
                "input_file": held["input_file_path"],
                "vendor_parameter_file": held["vendor_parameter_file_path"],
                "module": held["module"],
                "software_name": held["software_name"],
            }
        )
    return rows


def _copy_input_folders(rows: list[dict[str, str]], root: Path, out: Path) -> None:
    """Stage the input directories named by the existing manifest rows."""
    folders: set[Path] = set()
    for row in rows:
        for column in ("input_file", "vendor_parameter_file"):
            if row[column]:
                path = root / row[column]
                if not path.exists() and not path.with_name(path.name + ".gz").is_file():
                    raise FileNotFoundError(path)
                folders.add(path if path.is_dir() else path.parent)
    for folder in sorted(folders):
        for source in sorted(folder.rglob("*")):
            if source.is_file():
                target = out / "data" / source.relative_to(root)
                _copy(source, target.with_suffix("") if source.suffix == ".gz" else target)


def collect(
    corpus: Path,
    root: Path,
    sdrf: Path,
    out: Path,
    extra: Path | None = None,
    workspace: Path = Path(".."),
    fastas: Path | None = None,
    manifest: Path = Path("downloads.csv"),
) -> None:
    """Copy the corpus rows' folders, the extra rows' sources and the SDRFs into ``out``."""
    rows = _corpus_rows(corpus, root / manifest)
    added = [] if extra is None else _rows(extra)
    _copy_input_folders([*rows, *(row for row in added if not row["source"])], root, out)
    if extra is not None:
        for row in added:
            if row["source"]:
                _copy(workspace / row["source"], out / "data" / row["input_file"])
            if row["sdrf"]:
                _copy(
                    extra.parent / row["sdrf"],
                    (out / "data" / row["input_file"]).parent / "sdrf.tsv",
                )
    modules = {} if fastas is None else {row["module"]: row["fasta"] for row in _rows(fastas)}
    for row in [*rows, *added]:
        for column in ("input_file", "vendor_parameter_file"):
            row[column] = row[column].removesuffix(".gz")
        fasta = modules.get(row["module"], "")
        row["fasta"] = fasta
        if fasta and not (out / "data" / fasta).exists():
            _copy(root / fasta, out / "data" / fasta)
    out.mkdir(parents=True, exist_ok=True)
    with (out / "examples.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows([*rows, *added])
    (out / "sdrf").mkdir(exist_ok=True)
    for path in sorted(sdrf.glob("*.sdrf.tsv")):
        shutil.copy2(path, out / "sdrf" / path.name)
    print(f"{len(rows)} corpus and {len(added)} extra examples -> {out}")
