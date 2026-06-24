from __future__ import annotations

import cleancli.core as cleancli
from cleancli.report_renderers import render_html_report, render_markdown_report


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
