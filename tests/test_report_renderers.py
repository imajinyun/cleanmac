from __future__ import annotations

import contextlib
import io
import json

import cleancli.core as cleancli
from cleancli.report_renderers import render_html_report, render_markdown_report
from tests.helpers import make_sandbox, run_cli


def test_ai_reports_render_directly_for_coverage_and_contracts() -> None:
    capabilities = cleancli.render_capabilities()
    assert capabilities["schema"] == "cleanmac.capabilities.v1"
    assert capabilities["ai_readiness"]["ready"] is True
    assert capabilities["ai_schema_registry"]["schema"] == "cleanmac.ai-schema-registry.v1"

    self_test = cleancli.render_ai_self_test()
    assert self_test["schema"] == "cleanmac.ai-self-test.v1"
    assert self_test["passed"] is True, self_test

    governance = cleancli.render_ai_governance_advice_report()
    assert governance["schema"] == "cleanmac.ai-governance-advice.v1"
    assert governance["ready_for_llm_calling"] is True

    host_policy = cleancli.render_ai_host_policy_report()
    assert host_policy["schema"] == "cleanmac.ai-host-policy.v1"
    assert host_policy["valid"] is True

    for shell in ("bash", "zsh", "fish"):
        script = cleancli.render_completion_shell(shell)
        assert "cleanmac" in script


def test_report_renderers_cover_review_selection_and_execution_summary() -> None:
    report = {
        "schema": "cleanmac.clean.v1",
        "destructive": True,
        "dry_run": False,
        "total_bytes": 1536,
        "candidate_count": 2,
        "deleted_count": 1,
        "skipped_count": 1,
        "risk_policy": "strict",
        "plan_file": "/tmp/cleanmac-plan.json",
        "review_selection": {
            "selection_file": "/tmp/cleanmac-selection.json",
            "selected_item_ids": ["cache-1"],
            "selected_paths": ["/tmp/cache-one"],
        },
        "ai_confirmation_summary": {
            "confirmation_token": "abc123",
            "confirmation_token_context": {"plan_file": "/tmp/cleanmac-plan.json"},
            "operation_log": "~/.cleanmac/operations.jsonl",
        },
        "skipped_summary": {"by_reason": {"protected": 1}},
        "pre_clean_report": {
            "category_preview": [
                {"key": "trash", "human": "1.5 KB", "risk": "low", "candidate_count": 2},
            ],
        },
        "items": [
            {
                "id": "cache-1",
                "path": "/tmp/cache-one",
                "category": "trash",
                "status": "deleted",
                "bytes": 1024,
                "reason": "selected by review",
                "reveal_command": ["open", "-R", "/tmp/cache-one"],
            },
            {
                "id": "cache-2",
                "path": "/tmp/cache two",
                "kind": "trash",
                "risk": "low",
                "size_bytes": 512,
                "default_selected": False,
                "finder_url": "file:///tmp/cache%20two",
            },
        ],
        "skipped": [{"path": "/tmp/protected", "reason": "protected"}],
    }

    markdown = render_markdown_report({"report": report})
    html_report = render_html_report({"report": report, "argv": ["cleanmac", "--json", "clean", "run"]})

    assert "# cleanmac.clean.v1" in markdown
    assert "[Open in Finder](file:///tmp/cache-one)" in markdown
    assert "Copyable execution command" in html_report
    assert "--confirmation-token abc123" in html_report
    assert "file:///tmp/cache%20two" in html_report
    assert "protected" in html_report


def test_report_file_can_emit_html_audit_report() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        report_file = root / "cleanmac-audit.html"
        result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "--report-file",
            str(report_file),
            "--report-format",
            "html",
            "inspect",
            "--categories",
            "trash",
        )
        report = json.loads(result.stdout)
        html_text = report_file.read_text(encoding="utf-8")
        first_item = report["items"][0]

        assert report["report_file"] == str(report_file)
        assert report["report_format"] == "html"
        assert "finder_url" in first_item
        assert first_item["finder_url"].startswith("file://")
        assert first_item["open_command"][0] == "open"
        assert first_item["reveal_command"][:2] == ["open", "-R"]
        assert "<!doctype html>" in html_text
        assert "<title>cleanmac.inspect.v1</title>" in html_text
        assert "cleanmac audit report" in html_text
        assert "<th>schema</th><td><code>cleanmac.inspect.v1</code></td>" in html_text
        assert "<th>dry_run</th><td><code>True</code></td>" in html_text
        assert "<th>destructive</th><td><code>False</code></td>" in html_text
        assert "Scan summary" in html_text
        assert "Top reclaimable" in html_text
        assert "Category cards" in html_text
        assert "Skipped reasons" in html_text
        assert "Selected-to-delete review" in html_text
        assert "Copyable execution command" in html_text
        assert "This command still uses the governed CLI plan / review-selection / delete_ops path." in html_text
        assert "<input type='checkbox' disabled" in html_text
        assert "Finder URL" in html_text
        assert "file://" in html_text
        assert "open -R" in html_text
        assert "old.tmp" in html_text


def test_report_file_html_productizes_plan_candidates_and_execution_command() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        report_file = root / "cleanmac-plan.html"
        result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "--report-file",
            str(report_file),
            "--report-format",
            "html",
            "clean",
            "plan",
            "--categories",
            "trash",
            "--max-items",
            "10",
            "--max-delete-mb",
            "1",
        )
        report = json.loads(result.stdout)
        html_text = report_file.read_text(encoding="utf-8")

        assert report["schema"] == "cleanmac.plan.v1"
        assert "old.tmp" in html_text
        assert "cleanmac-confirm" in html_text
        assert "python3 cleanmac.py --json clean run" in html_text
        assert "--review-selection-file" in html_text
        assert "--require-plan-context" in html_text
        assert "--delete-mode trash" in html_text
        assert "Trash" in html_text
        assert "open -R" in html_text


def test_report_file_html_escapes_audit_content() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        unsafe = root / "Users/tester/.Trash/<script>alert(1).tmp"
        unsafe.parent.mkdir(parents=True, exist_ok=True)
        unsafe.write_text("unsafe", encoding="utf-8")
        report_file = root / "cleanmac-audit.html"
        result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "--report-file",
            str(report_file),
            "--report-format",
            "html",
            "inspect",
            "--categories",
            "trash",
        )
        report = json.loads(result.stdout)
        html_text = report_file.read_text(encoding="utf-8")
        first_item = report["items"][0]

        assert "%3Cscript%3Ealert%281%29.tmp" in first_item["finder_url"]
        assert "<script>alert(1).tmp" in first_item["path"]
        assert "<script>alert(1).tmp" not in html_text
        assert "&lt;script&gt;alert(1).tmp" in html_text
        assert "%3Cscript%3Ealert%281%29.tmp" in html_text
        assert "&lt;script&gt;alert(1).tmp" in html_text
        assert "Raw JSON" in html_text


def test_report_file_defaults_to_json_audit_report() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        report_file = root / "cleanmac-audit.json"
        result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "--report-file",
            str(report_file),
            "inspect",
            "--categories",
            "trash",
        )
        report = json.loads(result.stdout)
        audit_record = json.loads(report_file.read_text(encoding="utf-8"))

        assert report["report_format"] == "json"
        assert audit_record["schema"] == "cleanmac.audit.v1"
        assert audit_record["report_format"] == "json"
        assert audit_record["report_file"] == str(report_file)
        assert "--json" in audit_record["argv"]
        assert "--report-file" in audit_record["argv"]
        assert "inspect" in audit_record["argv"]
        assert audit_record["report"]["schema"] == "cleanmac.inspect.v1"
        assert "report_file" not in audit_record["report"]
        assert "report_format" not in audit_record["report"]
        assert audit_record["report"]["items"]


def test_analyze_tree_writes_markdown_report_with_file_links() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        report_file = root / "tree-report.md"
        result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "--report-file",
            str(report_file),
            "--report-format",
            "markdown",
            "analyze",
            "tree",
            "--path",
            "/Users/tester",
            "--depth",
            "1",
            "--top",
            "5",
        )
        report = json.loads(result.stdout)
        markdown = report_file.read_text(encoding="utf-8")

        assert report["report_format"] == "markdown"
        assert "# cleanmac.analyze-tree.v1" in markdown
        assert "Open in Finder" in markdown


def test_core_print_report_human_branches_are_covered_in_process() -> None:
    reports: list[tuple[str, dict[str, object]]] = [
        ("analyze", {"total_human": "1 B", "categories": [{"key": "trash", "human": "1 B", "risk": "low"}]}),
        (
            "diagnose",
            {
                "total_human": "1 B",
                "recommended_clean_categories": ["trash"],
                "caution_clean_categories": ["systemLogs"],
            },
        ),
        (
            "capabilities",
            {
                "name": "cleanmac",
                "model": "safe-cli",
                "category_count": 1,
                "active_path_count": 1,
                "commands": ["list"],
            },
        ),
        ("doctor", {"platform": "darwin", "checks": {"dry_run": {"status": "enabled", "message": "safe"}}}),
        ("plan", {"categories": ["trash"], "risk_policy": "default", "replay_command": ["cleanmac"]}),
        ("validate-plan", {"valid": True, "replay_clean_command": ["cleanmac"]}),
        ("policy-simulate", {"allowed": False, "recommended_next_action": "dry_run"}),
        ("workflow", {"workflow_name": "safe", "dry_run_scope": "selected"}),
        (
            "inspect",
            {
                "shown_candidates": 1,
                "total_candidates": 1,
                "total_human": "1 B",
                "items": [{"category": "trash", "path": "/tmp/a", "human": "1 B"}],
            },
        ),
        (
            "scripts",
            {
                "groups": {"clean": {"destructive": False, "commands": ["cleanmac --json capabilities"]}},
                "categories": [
                    {
                        "key": "trash",
                        "title": "Trash",
                        "risk": "low",
                        "commands": {"analyze": ["inspect"], "delete": ["clean"]},
                    }
                ],
            },
        ),
        ("software", {"action": "list", "status": "ok"}),
        ("optimize", {"action": "list", "tasks": ["rotate"]}),
        ("analyze-tree", {"path": ".", "shown_entries": 1, "total_entries": 1}),
        ("status", {"disk": {"free_human": "1 GB"}}),
        ("links", {"dry_run": True, "mode": "preview", "kind": "all", "targets": []}),
        (
            "open",
            {
                "dry_run": True,
                "targets": [
                    {
                        "category": "trash",
                        "special_case": False,
                        "status": "preview",
                        "command": "open",
                        "exists": True,
                    }
                ],
            },
        ),
        (
            "clean",
            {
                "dry_run": True,
                "total_human": "1 B",
                "items": [{"category": "trash", "deleted": False, "path": "/tmp/a", "human": "1 B"}],
                "pre_clean_report": {
                    "summary": {
                        "selected_category_count": 1,
                        "candidate_count": 1,
                        "estimated_reclaimable_human": "1 B",
                        "high_risk_categories": [],
                        "delete_semantics": "dry-run",
                    }
                },
                "post_clean_report": {"summary": {"deleted_item_count": 0, "estimated_reclaimed_human": "0 B"}},
            },
        ),
    ]

    for command, report in reports:
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            cleancli.print_report(report, as_json=False, command=command)
        assert stdout.getvalue(), command


def test_core_print_report_execute_mode_human_branches_are_covered_in_process() -> None:
    reports: list[tuple[str, dict[str, object], list[str]]] = [
        ("links", {"dry_run": False, "mode": "refresh", "kind": "logs", "targets": []}, ["EXECUTE", "kind=logs"]),
        (
            "open",
            {
                "dry_run": False,
                "targets": [
                    {
                        "category": "trash",
                        "special_case": True,
                        "status": "opened",
                        "command": "open -R",
                        "exists": True,
                    }
                ],
            },
            ["EXECUTE: Finder targets", "[trash] special opened"],
        ),
        (
            "clean",
            {
                "dry_run": False,
                "total_human": "1 B",
                "items": [{"category": "trash", "deleted": True, "path": "/tmp/a", "human": "1 B"}],
            },
            ["EXECUTE: 1 B across 1 item(s)", "[trash] deleted: /tmp/a"],
        ),
    ]

    for command, report, expected_lines in reports:
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            cleancli.print_report(report, as_json=False, command=command)
        output = stdout.getvalue()

        for expected in expected_lines:
            assert expected in output
