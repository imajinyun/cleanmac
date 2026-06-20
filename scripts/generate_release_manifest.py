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
    from cleancli.core import render_release_diagnostics_report
    from cleancli.release_artifacts import write_release_artifact_outputs, write_release_evidence_bundle_output
    from cleancli.release_orchestration import (
        render_release_promotion_decision,
        render_release_rehearsal,
        render_release_rollback_plan,
    )

    args = parse_args()
    manifest = write_release_artifact_outputs(
        dist_dir=Path(args.dist_dir).resolve(strict=False),
        assets_dir=Path(args.assets_dir).resolve(strict=False),
    )
    if args.evidence:
        assets_dir = Path(args.assets_dir).resolve(strict=False)
        resolved_dist_dir = Path(args.dist_dir).resolve(strict=False)
        readiness_path = assets_dir / "RELEASE-READINESS.json"
        release_readiness = None
        if readiness_path.is_file():
            release_readiness = json.loads(readiness_path.read_text(encoding="utf-8"))
        diagnostics = render_release_diagnostics_report(dist_dir=resolved_dist_dir, assets_dir=assets_dir)
        (assets_dir / "RELEASE-DIAGNOSTICS.json").write_text(
            json.dumps(diagnostics, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        rollback_plan = render_release_rollback_plan(
            dist_dir=resolved_dist_dir,
            assets_dir=assets_dir,
        )
        (assets_dir / "RELEASE-ROLLBACK-PLAN.json").write_text(
            json.dumps(rollback_plan, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        (assets_dir / "RELEASE-REHEARSAL.json").write_text("{}\n", encoding="utf-8")
        release_rehearsal = render_release_rehearsal(
            dist_dir=resolved_dist_dir,
            assets_dir=assets_dir,
        )
        (assets_dir / "RELEASE-REHEARSAL.json").write_text(
            json.dumps(release_rehearsal, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        promotion_decision = render_release_promotion_decision(
            dist_dir=resolved_dist_dir,
            assets_dir=assets_dir,
        )
        (assets_dir / "RELEASE-PROMOTION-DECISION.json").write_text(
            json.dumps(promotion_decision, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        manifest = write_release_evidence_bundle_output(
            dist_dir=resolved_dist_dir,
            assets_dir=assets_dir,
            release_readiness=release_readiness,
            release_rehearsal=release_rehearsal,
            promotion_decision=promotion_decision,
            rollback_plan=rollback_plan,
        )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
