#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def project_version() -> str:
    pyproject = PROJECT_ROOT / "pyproject.toml"
    for line in pyproject.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("version = "):
            return stripped.split("=", 1)[1].strip().strip('"')
    raise ValueError("Unable to find project version in pyproject.toml.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate the cleanmac Homebrew tap formula.")
    parser.add_argument("--version", help="Project version without a leading 'v'. Defaults to pyproject.toml.")
    parser.add_argument("--archive-url", help="Release source archive URL used by the Homebrew formula.")
    parser.add_argument("--sha256", required=True, help="SHA-256 digest for the Homebrew source archive.")
    parser.add_argument("--output", help="Write the generated formula to this path instead of stdout.")
    return parser.parse_args()


def main() -> int:
    from cleancli.release_artifacts import render_homebrew_formula

    args = parse_args()
    version = args.version or project_version()
    archive_url = args.archive_url or f"https://github.com/cleanmac/cleanmac/archive/refs/tags/v{version}.tar.gz"
    formula = render_homebrew_formula(version=version, archive_url=archive_url, sha256=args.sha256)
    if args.output:
        output = Path(args.output).resolve(strict=False)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(formula, encoding="utf-8")
    else:
        print(formula, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
