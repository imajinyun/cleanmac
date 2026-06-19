#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate cleanmac release manifest and SHA256SUMS.")
    parser.add_argument("--dist-dir", default="dist", help="Directory containing built wheel/sdist artifacts.")
    parser.add_argument("--assets-dir", default="release-assets", help="Directory containing SBOM.json and outputs.")
    return parser.parse_args()


def main() -> int:
    from cleancli.release_artifacts import write_release_artifact_outputs

    args = parse_args()
    manifest = write_release_artifact_outputs(
        dist_dir=Path(args.dist_dir).resolve(strict=False),
        assets_dir=Path(args.assets_dir).resolve(strict=False),
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
