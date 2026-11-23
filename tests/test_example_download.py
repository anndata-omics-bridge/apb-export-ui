"""The web examples download: a synthetic archive served from a file URL."""

from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path

import pytest

from apb_export_ui.web.example_download import download_examples


def _archive(path: Path, members: dict[str, bytes]) -> str:
    with zipfile.ZipFile(path, "w") as bundle:
        for name, content in members.items():
            bundle.writestr(name, content)
    return hashlib.md5(path.read_bytes()).hexdigest()


def test_download_unpacks_the_examples_without_their_top_folder(tmp_path: Path) -> None:
    archive = tmp_path / "examples.zip"
    md5 = _archive(
        archive,
        {
            "apb_export_web_examples/examples.csv": b"input_file\n",
            "apb_export_web_examples/data/a/report.tsv": b"x\n",
            "apb_export_web_examples/sdrf/m.sdrf.tsv": b"s\n",
        },
    )
    folder = tmp_path / "home" / "examples"

    download_examples(folder, archive.as_uri(), md5)

    assert (folder / "examples.csv").read_bytes() == b"input_file\n"
    assert (folder / "data/a/report.tsv").read_bytes() == b"x\n"
    assert (folder / "sdrf/m.sdrf.tsv").read_bytes() == b"s\n"
    assert sorted(path.name for path in folder.parent.iterdir()) == ["examples"]


def test_a_wrong_checksum_leaves_no_examples(tmp_path: Path) -> None:
    archive = tmp_path / "examples.zip"
    _archive(archive, {"apb_export_web_examples/examples.csv": b"input_file\n"})
    folder = tmp_path / "examples"

    with pytest.raises(ValueError, match="checksum"):
        download_examples(folder, archive.as_uri(), "0" * 32)

    assert not (folder / "examples.csv").exists()


@pytest.mark.parametrize("member", ["other/examples.csv", "apb_export_web_examples/../x"])
def test_members_outside_the_top_folder_are_refused(tmp_path: Path, member: str) -> None:
    archive = tmp_path / "examples.zip"
    md5 = _archive(archive, {member: b"x\n"})
    folder = tmp_path / "examples"

    with pytest.raises(ValueError, match="unexpected member"):
        download_examples(folder, archive.as_uri(), md5)

    assert not (folder / "examples.csv").exists()
