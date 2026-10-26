"""Check local Markdown links without following external URLs."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    """Fail for a broken local README or documentation link."""
    for source in [ROOT / "README.md", *sorted((ROOT / "docs").glob("*.md"))]:
        for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", source.read_text()):
            if "://" in target or target.startswith("#"):
                continue
            path = (source.parent / target.split("#")[0]).resolve()
            assert path.exists(), f"{source.relative_to(ROOT)}: missing {target}"
    print("Local documentation links passed")


if __name__ == "__main__":
    main()
