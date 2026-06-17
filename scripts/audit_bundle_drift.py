#!/usr/bin/env python3
"""Audit macOS app bundle identifiers against cleanmac protection policy."""

from __future__ import annotations

import argparse
import fnmatch
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from cleancli.protection import bundle_id_for_app  # noqa: E402
from cleancli.protection_data import (  # noqa: E402
    DATA_PROTECTED_BUNDLE_PATTERNS,
    DEFAULT_PROTECTED_BUNDLE_IDS,
    PROTECTED_BUNDLE_PREFIXES,
    SYSTEM_CRITICAL_BUNDLE_PATTERNS,
)

SYSTEM_SCAN_ROOTS = (Path("/System/Applications"), Path("/System/Library/CoreServices"))
INFORMATIONAL_SCAN_ROOTS = (Path("/Applications"),)


def iter_app_bundles(root: Path) -> list[Path]:
    """Return app bundles under root, including root itself when it is an .app."""
    if not root.exists():
        return []
    if root.is_dir() and root.suffix == ".app":
        return [root]
    return sorted(path for path in root.rglob("*.app") if path.is_dir())


def coverage_reason(bundle_id: str | None) -> str | None:
    """Return the protection mechanism covering a bundle identifier, if any."""
    if not bundle_id:
        return None
    if bundle_id in DEFAULT_PROTECTED_BUNDLE_IDS:
        return "default-protected-bundle-id"
    if bundle_id.startswith(PROTECTED_BUNDLE_PREFIXES):
        return "protected-bundle-prefix"
    if any(fnmatch.fnmatchcase(bundle_id.lower(), pattern.lower()) for pattern in SYSTEM_CRITICAL_BUNDLE_PATTERNS):
        return "system-critical-bundle-pattern"
    if any(fnmatch.fnmatchcase(bundle_id.lower(), pattern.lower()) for pattern in DATA_PROTECTED_BUNDLE_PATTERNS):
        return "data-protected-bundle-pattern"
    return None


def scan_root(root: Path, *, source: str) -> list[dict[str, Any]]:
    rows = []
    for app_path in iter_app_bundles(root):
        bundle_id = bundle_id_for_app(app_path)
        reason = coverage_reason(bundle_id)
        rows.append(
            {
                "source": source,
                "path": str(app_path),
                "bundle_id": bundle_id,
                "coverage": reason or "uncovered",
                "covered": reason is not None,
            }
        )
    return rows


def audit_bundle_drift(
    *, system_roots: list[Path] | None = None, informational_roots: list[Path] | None = None
) -> dict[str, Any]:
    system_roots = list(SYSTEM_SCAN_ROOTS if system_roots is None else system_roots)
    informational_roots = list(INFORMATIONAL_SCAN_ROOTS if informational_roots is None else informational_roots)
    system_rows = [row for root in system_roots for row in scan_root(root, source="system")]
    informational_rows = [row for root in informational_roots for row in scan_root(root, source="applications")]
    uncovered_system = [row for row in system_rows if row["bundle_id"] and not row["covered"]]
    unreadable_system = [row for row in system_rows if not row["bundle_id"]]
    return {
        "schema": "cleanmac.bundle-drift-audit.v1",
        "destructive": False,
        "system_roots": [str(root) for root in system_roots],
        "informational_roots": [str(root) for root in informational_roots],
        "summary": {
            "system_bundle_count": len(system_rows),
            "informational_bundle_count": len(informational_rows),
            "uncovered_system_bundle_count": len(uncovered_system),
            "unreadable_system_bundle_count": len(unreadable_system),
            "drift_detected": bool(uncovered_system),
        },
        "uncovered_system_bundles": uncovered_system,
        "unreadable_system_bundles": unreadable_system,
        "system_bundles": system_rows,
        "informational_bundles": informational_rows,
        "policy_sources": {
            "default_protected_bundle_count": len(DEFAULT_PROTECTED_BUNDLE_IDS),
            "protected_bundle_prefixes": list(PROTECTED_BUNDLE_PREFIXES),
            "system_critical_bundle_pattern_count": len(SYSTEM_CRITICAL_BUNDLE_PATTERNS),
            "data_protected_bundle_pattern_count": len(DATA_PROTECTED_BUNDLE_PATTERNS),
        },
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit macOS bundle-id protection drift for cleanmac.")
    parser.add_argument("--system-root", action="append", type=Path, help="System app root to scan. Repeatable.")
    parser.add_argument(
        "--informational-root",
        action="append",
        type=Path,
        help="Non-system app root to scan for inventory only. Repeatable.",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    parser.add_argument(
        "--fail-on-drift", action="store_true", help="Exit non-zero when uncovered system bundles exist."
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = audit_bundle_drift(system_roots=args.system_root, informational_roots=args.informational_root)
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        summary = report["summary"]
        print("cleanmac bundle drift audit")
        print(f"  system bundles       : {summary['system_bundle_count']}")
        print(f"  informational bundles: {summary['informational_bundle_count']}")
        print(f"  uncovered system     : {summary['uncovered_system_bundle_count']}")
        for row in report["uncovered_system_bundles"]:
            print(f"  drift: {row['bundle_id']} at {row['path']}")
    return 1 if args.fail_on_drift and report["summary"]["drift_detected"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
