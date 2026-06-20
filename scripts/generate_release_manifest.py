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
    parser = argparse.ArgumentParser(
        description="Generate cleanmac release manifest, SHA256SUMS, and optional evidence bundle."
    )
    parser.add_argument("--dist-dir", default="dist", help="Directory containing built wheel/sdist artifacts.")
    parser.add_argument("--assets-dir", default="release-assets", help="Directory containing SBOM.json and outputs.")
    parser.add_argument(
        "--evidence",
        action="store_true",
        help="Also generate RELEASE-EVIDENCE.json using existing release readiness and artifact outputs.",
    )
    return parser.parse_args()


def main() -> int:
    from cleancli.release_artifacts import write_release_artifact_outputs, write_release_evidence_bundle_output

    args = parse_args()
    manifest = write_release_artifact_outputs(
        dist_dir=Path(args.dist_dir).resolve(strict=False),
        assets_dir=Path(args.assets_dir).resolve(strict=False),
    )
    if args.evidence:
        assets_dir = Path(args.assets_dir).resolve(strict=False)
        readiness_path = assets_dir / "RELEASE-READINESS.json"
        release_readiness = None
        if readiness_path.is_file():
            release_readiness = json.loads(readiness_path.read_text(encoding="utf-8"))
        manifest = write_release_evidence_bundle_output(
            dist_dir=Path(args.dist_dir).resolve(strict=False),
            assets_dir=assets_dir,
            release_readiness=release_readiness,
        )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
