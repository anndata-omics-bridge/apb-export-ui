"""The web examples, downloaded from their Zenodo record into an examples folder."""

from __future__ import annotations

import hashlib
import shutil
import zipfile
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory
from urllib.request import urlopen

from loguru import logger

# Zenodo record 24478242 (10.5281/zenodo.24478242), version 1: examples.csv, data/ and sdrf/
# under one top folder; every installation writes its own index beside them.
EXAMPLES_URL = "https://zenodo.org/api/records/24478242/files/apb_export_web_examples.zip/content"
EXAMPLES_MD5 = "b70d1f8495fbe01e5284c92cb6d7c35c"
_TOP = "apb_export_web_examples"
_CHUNK = 1 << 20


def _fetch(url: str, target: Path, md5: str) -> None:
    """Stream the archive to ``target``, reporting progress, and check its checksum.

    Raises:
        ValueError: The downloaded archive has another checksum.
    """
    digest = hashlib.md5()
    received = 0
    with urlopen(url, timeout=60) as response, target.open("wb") as handle:
        total = int(response.headers.get("Content-Length") or 0)
        reported = 0
        while chunk := response.read(_CHUNK):
            handle.write(chunk)
            digest.update(chunk)
            received += len(chunk)
            if received - reported >= 50 * _CHUNK or received == total:
                reported = received
                logger.info(f"Examples: {received >> 20} of {total >> 20} MB")
    if digest.hexdigest() != md5:
        raise ValueError(f"the examples archive from {url} has checksum {digest.hexdigest()}")


def _unpack(archive: Path, folder: Path) -> None:
    """Extract the archive's top folder into ``folder``.

    Raises:
        ValueError: A member lies outside the archive's top folder.
    """
    with zipfile.ZipFile(archive) as bundle:
        for member in bundle.infolist():
            parts = PurePosixPath(member.filename).parts
            if not parts or parts[0] != _TOP or ".." in parts:
                raise ValueError(f"unexpected member {member.filename} in the examples archive")
            if member.is_dir() or len(parts) == 1:
                continue
            target = folder.joinpath(*parts[1:])
            target.parent.mkdir(parents=True, exist_ok=True)
            with bundle.open(member) as source, target.open("wb") as copy:
                shutil.copyfileobj(source, copy)


def download_examples(folder: Path, url: str = EXAMPLES_URL, md5: str = EXAMPLES_MD5) -> None:
    """Download the web examples and unpack ``examples.csv``, ``data/`` and ``sdrf/`` into
    ``folder``; the archive itself is not kept. ``examples.csv`` arrives last, so a folder that
    holds it holds complete examples."""
    folder.mkdir(parents=True, exist_ok=True)
    logger.info(f"Downloading the examples from {url} into {folder}")
    with TemporaryDirectory(dir=folder.parent) as directory:
        archive = Path(directory) / "examples.zip"
        _fetch(url, archive, md5)
        unpacked = Path(directory) / "unpacked"
        _unpack(archive, unpacked)
        for entry in sorted(unpacked.iterdir(), key=lambda path: path.name == "examples.csv"):
            target = folder / entry.name
            if target.is_dir():
                shutil.rmtree(target)
            entry.replace(target)
