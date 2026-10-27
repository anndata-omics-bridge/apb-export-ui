"""Staging resolves managed fixtures and preserves complete source files."""

from __future__ import annotations

import csv
import gzip
import subprocess
import sys
from pathlib import Path

import pytest

from apb_export_ui.web.example_build import EXAMPLE_DATA, collect


def _table(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _read(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def test_build_subcommand_uses_packaged_metadata_from_another_working_directory(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    studio = workspace / "apb_studio"
    root = studio / "test_data_download"
    dataset = "submissions/synthetic"
    original = b"Run\tIntensity\nrun_A\t123.4567890123456789\n"
    source = root / dataset / "input.tsv.gz"
    source.parent.mkdir(parents=True)
    source.write_bytes(gzip.compress(original))
    _table(
        root / "downloads.csv",
        [
            {
                "dataset": dataset,
                "input_file_path": f"{dataset}/input.tsv.gz",
                "vendor_parameter_file_path": "",
                "module": "synthetic",
                "software_name": "DIA-NN",
            }
        ],
    )
    _table(studio / "corpuses/routine.csv", [{"dataset": dataset, "note": "test fixture"}])
    _table(
        studio / "workflow_tables/workflow_proteobench.csv",
        [{"module": "synthetic", "fasta": "fasta/test.fasta"}],
    )
    fasta = root / "fasta/test.fasta"
    fasta.parent.mkdir()
    fasta.write_text(">P1\nPEPTIDEK\n", encoding="utf-8")
    modules = workspace / "apb-proteobench/src/apb_proteobench/data/modules"
    modules.mkdir(parents=True)
    (modules / "synthetic.sdrf.tsv").write_text("sample annotation\n", encoding="utf-8")
    extra_rows = _read(EXAMPLE_DATA / "examples.csv")
    for row in extra_rows:
        sources = (
            [workspace / row["source"]]
            if row["source"]
            else [
                root / row[column]
                for column in ("input_file", "vendor_parameter_file")
                if row[column]
            ]
        )
        for path in sources:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"complete supplementary input\n")
    output = tmp_path / "staged"

    result = subprocess.run(
        [
            str(Path(sys.executable).with_name("apb-export-web")),
            "examples",
            "build",
            str(output),
            str(workspace),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )

    assert "1 corpus" in result.stdout
    assert len(_read(output / "examples.csv")) == 1 + len(extra_rows)
    assert (output / "data" / dataset / "input.tsv").read_bytes() == original
    assert (output / "data/fasta/test.fasta").read_bytes() == fasta.read_bytes()
    assert (output / "sdrf/synthetic.sdrf.tsv").read_text() == "sample annotation\n"
    for row in extra_rows:
        if row["sdrf"]:
            annotation = (output / "data" / row["input_file"]).parent / "sdrf.tsv"
            assert annotation.read_bytes() == (EXAMPLE_DATA / row["sdrf"]).read_bytes()


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
