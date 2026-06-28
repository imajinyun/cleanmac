from __future__ import annotations

import json
from pathlib import Path

from cleancli.ai_schema import build_tool_argv
from cleancli.ai_versioning import validate_contract_payload
from tests.helpers import make_sandbox, run_cli


def _write_app(root: Path, name: str, bundle_id: str) -> None:
    app_contents = root / f"Applications/{name}.app/Contents"
    app_contents.mkdir(parents=True)
    app_contents.joinpath("Info.plist").write_bytes(
        b'<?xml version="1.0" encoding="UTF-8"?>'
        b'<plist version="1.0"><dict><key>CFBundleIdentifier</key><string>'
        + bundle_id.encode("utf-8")
        + b"</string></dict></plist>"
    )


def test_software_discovery_governance_contract_is_ready() -> None:
    report = json.loads(run_cli("--json", "software-discovery-governance").stdout)

    assert report["schema"] == "cleanmac.software-discovery-governance.v1"
    assert report["destructive"] is False
    assert report["dry_run"] is True
    assert report["ready"] is True
    assert report["failed_check_ids"] == []
    assert report["inspect_evidence_ready"] is True
    assert report["orphan_evidence_ready"] is True
    assert report["orphan_budget_ready"] is True
    assert report["review_selection_compatible"] is True
    assert report["destructive_paths_absent"] is True
    assert report["landed_backlog_item_ids"] == [
        "p0-software-leftover-discovery",
        "p0-software-orphan-scan",
    ]
    assert "cleanmac.software-discovery-evidence.v1" in report["evidence_refs"]
    assert ["make", "software-discovery-governance-smoke"] in report["release_gate_commands"]
    assert validate_contract_payload("cleanmac.software-discovery-governance.v1", report)["valid"] is True


def test_software_discovery_governance_fixture_closes_inspect_orphan_and_review_loop() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        _write_app(root, "Example", "com.example.app")
        cache = root / "Users/tester/Library/Caches/com.example.app/cache.bin"
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text("cache", encoding="utf-8")

        orphan_cache = root / "Users/tester/Library/Caches/com.example.oldapp"
        orphan_cache.mkdir(parents=True, exist_ok=True)
        orphan_cache.joinpath("data").write_text("orphan", encoding="utf-8")
        for index in range(12):
            extra_cache = root / f"Users/tester/Library/Caches/com.example.oldextra{index}"
            extra_cache.mkdir(parents=True, exist_ok=True)
            extra_cache.joinpath("data").write_text("orphan", encoding="utf-8")

        inspect = json.loads(
            run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "software",
                "inspect",
                "--app",
                "Example",
            ).stdout
        )
        orphans = json.loads(
            run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "software",
                "orphans",
                "--limit",
                "2",
                "--max-scan-entries",
                "10",
            ).stdout
        )
        orphan_report = root / "orphan-report.json"
        orphan_report.write_text(json.dumps(orphans), encoding="utf-8")
        review = json.loads(
            run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "review",
                "--input-file",
                str(orphan_report),
            ).stdout
        )

        inspect_candidates = inspect["candidates"]
        orphan_candidates = orphans["candidates"]
        assert any(candidate["discovery_evidence"]["installed_app_present"] is True for candidate in inspect_candidates)
        assert orphan_candidates
        assert all(candidate["discovery_evidence"]["installed_app_present"] is False for candidate in orphan_candidates)
        assert orphans["summary"]["schema"] == "cleanmac.software-orphan-summary.v1"
        assert orphans["shown_candidate_count"] == len(orphan_candidates)
        assert orphans["scan_truncated"] is True
        assert review["schema"] == "cleanmac.review.v1"
        assert review["source_schema"] == "cleanmac.software-orphans.v1"
        assert review["item_count"] == len(orphan_candidates)


def test_software_discovery_governance_marks_backlog_items_landed() -> None:
    capabilities = json.loads(run_cli("--json", "capabilities").stdout)
    gap_todo = capabilities["boundary_governance"]["open_source_gap_governance_todo"]
    by_id = {item["id"]: item for item in gap_todo["items"]}

    assert gap_todo["landed_count"] == 2
    assert gap_todo["in_progress_count"] == 0
    assert gap_todo["pending_count"] == 8
    for item_id in ("p0-software-leftover-discovery", "p0-software-orphan-scan"):
        item = by_id[item_id]
        assert item["status"] == "landed"
        assert item["landing_evidence"]["state"] == "landed"
        assert item["landing_evidence"]["release_gated"] is True
        assert "cleanmac.software-discovery-governance.v1" in item["landing_evidence"]["evidence_refs"]


def test_software_orphans_ai_tool_exposes_budget_parameters() -> None:
    argv = build_tool_argv(
        "cleanmac_software_orphans",
        {"limit": 5, "max_scan_entries": 50, "summary_only": True},
    )

    assert argv == [
        "cleanmac",
        "--json",
        "software",
        "orphans",
        "--limit",
        "5",
        "--max-scan-entries",
        "50",
        "--summary-only",
    ]
