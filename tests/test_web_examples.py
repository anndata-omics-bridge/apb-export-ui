"""Staging resolves managed fixtures and preserves complete source files."""

from __future__ import annotations

import csv
import gzip
import runpy
from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

SCRIPT = runpy.run_path(str(Path(__file__).parents[1] / "scripts" / "web_examples.py"))
collect = cast(Callable[..., None], SCRIPT["collect"])


def _table(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _read(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def test_complete_gzipped_fixture_and_annotation_are_staged_without_a_benchmark_fasta(
    tmp_path: Path,
) -> None:
    root = tmp_path / "fixtures"
    dataset = "zenodo/apb_examples/metamorpheus_ionstar"
    folder = root / dataset
    folder.mkdir(parents=True)
    original = b"Run\tIon\tIntensity\n" + b"".join(
        f"run_{index % 20}\tion_{index}\t1.234567890123456789\n".encode() for index in range(2001)
    )
    (folder / "QuantifiedPeaks.tsv.gz").write_bytes(gzip.compress(original))
    annotation = b"comment[data file]\tfactor value[group]\nrun_0\tC\n"
    (folder / "sdrf.tsv.gz").write_bytes(gzip.compress(annotation))
    (folder / "FlashLfqSettings.toml").write_text("Normalize = true\n")
    _table(
        root / "downloads.csv",
        [
            {
                "dataset": dataset,
                "input_file_path": f"{dataset}/QuantifiedPeaks.tsv.gz",
                "vendor_parameter_file_path": "",
                "module": "PXD003881",
                "software_name": "MetaMorpheus",
            }
        ],
    )
    corpus = tmp_path / "routine.csv"
    _table(corpus, [{"dataset": dataset, "note": "complete original"}])
    modules = tmp_path / "modules"
    modules.mkdir()
    fastas = tmp_path / "fastas.csv"
    _table(fastas, [{"module": "dda_qexactive", "fasta": "benchmark.fasta"}])
    out = tmp_path / "staged"

    collect(corpus, root, modules, out, fastas=fastas)

    staged = out / "data" / dataset
    assert (staged / "QuantifiedPeaks.tsv").read_bytes() == original
    assert (staged / "sdrf.tsv").read_bytes() == annotation
    assert (staged / "FlashLfqSettings.toml").read_text() == "Normalize = true\n"
    assert not (staged / "QuantifiedPeaks.tsv.gz").exists()
    assert _read(out / "examples.csv") == [
        {
            "input_file": f"{dataset}/QuantifiedPeaks.tsv",
            "vendor_parameter_file": "",
            "module": "PXD003881",
            "software_name": "MetaMorpheus",
            "fasta": "",
        }
    ]


def test_multifile_fixture_and_external_extra_keep_their_companions(tmp_path: Path) -> None:
    root = tmp_path / "fixtures"
    folder = root / "zenodo/mq/related"
    folder.mkdir(parents=True)
    for name in ("evidence.txt", "peptides.txt", "proteinGroups.txt"):
        (folder / f"{name}.gz").write_bytes(gzip.compress(name.encode()))
    (folder / "mqpar.xml").write_text("<MaxQuantParams/>")
    _table(
        root / "downloads.csv",
        [
            {
                "dataset": "zenodo/mq/related",
                "input_file_path": "zenodo/mq/related",
                "vendor_parameter_file_path": "zenodo/mq/related/mqpar.xml",
                "module": "test_module",
                "software_name": "MaxQuant",
            }
        ],
    )
    corpus = tmp_path / "routine.csv"
    _table(corpus, [{"dataset": "zenodo/mq/related", "note": "all tables"}])
    modules = tmp_path / "modules"
    modules.mkdir()
    (modules / "test_module.sdrf.tsv").write_text("annotation")
    (tmp_path / "source.tsv.gz").write_bytes(gzip.compress(b"entire extra table\n"))
    (tmp_path / "override.tsv").write_text("own annotation\n")
    extra = tmp_path / "extras.csv"
    _table(
        extra,
        [
            {
                "input_file": "custom/source.tsv",
                "vendor_parameter_file": "",
                "module": "test_module",
                "software_name": "pb_custom",
                "source": "source.tsv.gz",
                "sdrf": "override.tsv",
            }
        ],
    )
    out = tmp_path / "staged"

    collect(corpus, root, modules, out, extra=extra, workspace=tmp_path)

    for name in ("evidence.txt", "peptides.txt", "proteinGroups.txt"):
        assert (out / "data/zenodo/mq/related" / name).read_bytes() == name.encode()
    assert (out / "data/zenodo/mq/related/mqpar.xml").is_file()
    assert _read(out / "examples.csv")[0]["input_file"] == "zenodo/mq/related"
    assert (out / "data/custom/source.tsv").read_bytes() == b"entire extra table\n"
    assert (out / "data/custom/sdrf.tsv").read_text() == "own annotation\n"
    assert (out / "sdrf/test_module.sdrf.tsv").read_text() == "annotation"


@pytest.mark.parametrize(
    "key,source,message",
    [
        ("unknown", "present.tsv", "Unknown fixture dataset"),
        ("known", "", "Dataset not downloaded"),
        ("known", "absent.tsv", "absent.tsv"),
    ],
)
def test_unresolvable_corpus_inputs_fail_before_writing_a_manifest(
    tmp_path: Path,
    key: str,
    source: str,
    message: str,
) -> None:
    root = tmp_path / "fixtures"
    _table(
        root / "downloads.csv",
        [
            {
                "dataset": "known",
                "input_file_path": source,
                "vendor_parameter_file_path": "",
                "module": "m",
                "software_name": "s",
            }
        ],
    )
    corpus = tmp_path / "routine.csv"
    _table(corpus, [{"dataset": key, "note": "test"}])
    with pytest.raises((ValueError, FileNotFoundError), match=message):
        collect(corpus, root, tmp_path, tmp_path / "staged")
    assert not (tmp_path / "staged/examples.csv").exists()
