"""Other anndata_bridge packages, and this package's CLI, import only through an api module."""

from __future__ import annotations

import ast
import tomllib
from pathlib import Path

ROOT = Path(__file__).parents[1]
PACKAGE = "apb_export_ui"
FOLDERS = ("src", "tests", "scripts")
# Application pins use Git sources, so boundary coverage must not depend on path sources.
PYPROJECT = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
SIBLINGS = frozenset(
    dependency.split(" @ ")[0].replace("-", "_")
    for dependency in PYPROJECT["project"]["dependencies"]
    if " @ git+" in dependency
)


def _sibling_modules(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None and node.level == 0:
            modules.extend(
                f"{node.module}.{alias.name}" if node.module in SIBLINGS else node.module
                for alias in node.names
            )
    return [module for module in modules if module.split(".")[0] in SIBLINGS]


def test_siblings_are_imported_only_through_their_api() -> None:
    sources = sorted(path for folder in FOLDERS for path in (ROOT / folder).rglob("*.py"))
    offenders = [
        f"{path.relative_to(ROOT)}: {module}"
        for path in sources
        for module in _sibling_modules(path)
        if module != f"{module.split('.')[0]}.api"
    ]
    assert SIBLINGS
    assert offenders == []


def _package_modules(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None and node.level == 0:
            modules.append(node.module)
    return [module for module in modules if module.split(".")[0] == PACKAGE]


def test_the_web_front_end_imports_only_its_own_subsystem_or_public_sibling_apis() -> None:
    sources = sorted((ROOT / "src" / PACKAGE / "web").rglob("*.py"))
    assert sources
    offenders = [
        f"{path.relative_to(ROOT)}: {module}"
        for path in sources
        for module in _package_modules(path)
        if module.split(".")[:2] != [PACKAGE, "web"]
    ]
    assert offenders == []
