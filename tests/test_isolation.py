"""The application lock, package resources and executable have one reproducible owner."""

from __future__ import annotations

import json
import re
import tomllib
from importlib import metadata
from importlib.resources import files
from pathlib import Path

ROOT = Path(__file__).parents[1]


APB = ("apb-export", "apb2", "apb-catalog", "apb-fasta", "protein-fasta", "prozor")


def _name(requirement: str) -> str:
    return re.split(r"[\[<>=!~ ;@]", requirement, maxsplit=1)[0]


def test_every_apb_runtime_is_a_locked_release_and_the_report_a_locked_commit() -> None:
    manifest = tomllib.loads((ROOT / "pyproject.toml").read_text())
    assert manifest["tool"]["uv"]["no-sources"] is True
    assert manifest["tool"]["uv"]["default-groups"] == ["dev", "report"]
    dependencies: list[str] = manifest["project"]["dependencies"]
    assert not [entry for entry in dependencies if " @ " in entry], "PyPI refuses direct URLs"
    assert set(APB) <= {_name(entry) for entry in dependencies}
    lock = tomllib.loads((ROOT / "uv.lock").read_text())
    packages = {package["name"]: package for package in lock["package"]}
    for name in APB:
        assert packages[name]["source"] == {"registry": "https://pypi.org/simple"}, name
        assert metadata.version(name) == packages[name]["version"], name
    (report,) = manifest["dependency-groups"]["report"]
    name, source = report.split(" @ ")
    assert name == "apb-pmultiqc"
    assert source.startswith("git+https://github.com/anndata-omics-bridge/")
    revision = source.rsplit("@", 1)[1]
    assert re.fullmatch(r"[0-9a-f]{40}", revision)
    assert packages[name]["source"]["git"].endswith("#" + revision)
    direct = json.loads(metadata.distribution(name).read_text("direct_url.json") or "{}")
    assert direct["vcs_info"]["commit_id"] == revision
    assert not direct.get("dir_info", {}).get("editable", False)


def test_only_the_ui_distribution_owns_the_web_executable() -> None:
    owners = [
        distribution.metadata["Name"]
        for distribution in metadata.distributions()
        if any(
            entry.name == "apb-export-web" and entry.group == "console_scripts"
            for entry in distribution.entry_points
        )
    ]
    assert owners == ["apb-export-ui"]


def test_the_package_contains_static_assets_and_descriptions() -> None:
    web = files("apb_export_ui.web")
    assert web.joinpath("static/index.html").is_file()
    assert json.loads(web.joinpath("hints.json").read_text())["software"]
    assert json.loads(web.joinpath("outputs.json").read_text())
