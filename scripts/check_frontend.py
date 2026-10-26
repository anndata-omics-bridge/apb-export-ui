"""Compare a fresh frontend build with the static assets shipped in the Python wheel."""

from __future__ import annotations

import filecmp
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def contents(folder: Path) -> dict[str, Path]:
    """Index every asset by its relative path."""
    return {str(path.relative_to(folder)): path for path in folder.rglob("*") if path.is_file()}


def main() -> None:
    """Fail for missing, extra or stale packaged assets without rewriting tracked files."""
    with tempfile.TemporaryDirectory(prefix="apb-ui-assets-") as directory:
        fresh = Path(directory) / "static"
        subprocess.run(
            ["npm", "run", "build", "--", "--outDir", str(fresh)],
            cwd=ROOT / "web",
            check=True,
        )
        expected = contents(ROOT / "src/apb_export_ui/web/static")
        actual = contents(fresh)
        assert expected.keys() == actual.keys(), "asset inventory is stale; run make web"
        changed = [
            name
            for name in expected
            if not filecmp.cmp(expected[name], actual[name], shallow=False)
        ]
        assert not changed, f"packaged assets are stale: {changed}; run make web"
    print("Packaged frontend matches a fresh build")


if __name__ == "__main__":
    main()
