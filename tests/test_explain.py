from __future__ import annotations

from cleancli import explain


def _human_size(size: int | None) -> str:
    return f"{size} B"


def test_payload_candidates_reads_pre_clean_report_candidates() -> None:
    payload = {
        "pre_clean_report": {
            "candidates": [
                {"category": "trash", "path": "/tmp/a", "bytes": 10},
                "invalid",
            ]
        }
    }

    assert explain.payload_candidates(payload) == [{"category": "trash", "path": "/tmp/a", "bytes": 10}]


def test_render_explain_payload_summarizes_categories_and_risk() -> None:
    report = explain.render_explain_payload(
        {
            "schema": "cleanmac.plan.v1",
            "destructive": False,
            "dry_run": True,
            "estimated_reclaimable_bytes": 30,
            "selected_categories": [
                {"key": "trash", "risk": "low"},
                {"key": "downloads", "risk": "high"},
            ],
            "pre_clean_report": {
                "candidates": [
                    {"category": "trash", "path": "/tmp/a", "bytes": 10},
                    {"category": "downloads", "path": "/tmp/b", "bytes": 20},
                ]
            },
        },
        human_size=_human_size,
    )

    assert report["schema"] == "cleanmac.explain.v1"
    assert report["source_schema"] == "cleanmac.plan.v1"
    assert report["summary"]["estimated_reclaimable_bytes"] == 30
    assert report["summary"]["candidate_count"] == 2
    assert report["risk_summary"] == {"high": 1, "low": 1}
    assert report["top_categories"][0]["category"] == "downloads"
    assert report["top_categories"][0]["reason"] == "high-risk category needs explicit review"
    assert report["ai_guidance"]["safe_to_execute"] is False
