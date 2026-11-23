from __future__ import annotations

import importlib
import re
import tomllib
from pathlib import Path


def test_package_is_importable() -> None:
    """The generated distribution exposes its configured import package."""
    assert importlib.import_module("apb_export_ui") is not None


def test_launchers_install_this_version() -> None:
    """Each launcher installs the version being released; the macOS one is the shell script."""
    root = Path(__file__).parents[1]
    version = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"][
        "version"
    ]
    launchers = root / "launchers"
    for name in ("install.sh", "install.command", "install.bat"):
        text = (launchers / name).read_text(encoding="utf-8")
        assert re.search(rf" apb-export-ui=={re.escape(version)}\s", text), name
    assert (launchers / "install.command").read_bytes() == (launchers / "install.sh").read_bytes()
    assert b"\r\n" in (launchers / "install.bat").read_bytes()
