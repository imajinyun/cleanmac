"""Behavior-level idempotency tests for AI-friendly cleanmac workflows."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from typing import Any, cast

from tests.helpers import cleanmac_test_env, make_sandbox, run_clean_json

VOLATILE_KEYS = {"generated_at", "expires_at", "timestamp", "started_at", "finished_at", "duration_ms"}


def _strip_volatile(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _strip_volatile(child) for key, child in value.items() if key not in VOLATILE_KEYS}
    if isinstance(value, list):
        return [_strip_volatile(child) for child in value]
    return value


class AIIdempotencyTests(unittest.TestCase):
    def test_repeated_inspect_produces_stable_output(self) -> None:
        with cleanmac_test_env():
            tmp, root, home = make_sandbox()
            with tmp:
                first = run_clean_json(root, home, "inspect", "--categories", "trash")
                second = run_clean_json(root, home, "inspect", "--categories", "trash")

        self.assertEqual(_strip_volatile(first), _strip_volatile(second))

    def test_repeated_generate_plan_produces_stable_plan_after_stripping_expiry(self) -> None:
        with cleanmac_test_env():
            tmp, root, home = make_sandbox()
            with tmp:
                first = run_clean_json(root, home, "plan", "--categories", "trash", "--ai-origin")
                second = run_clean_json(root, home, "plan", "--categories", "trash", "--ai-origin")

        self.assertEqual(first["schema"], "cleanmac.plan.v1")
        self.assertEqual(_strip_volatile(first), _strip_volatile(second))

    def test_replayed_dry_run_keeps_token_stable_within_same_plan(self) -> None:
        with cleanmac_test_env():
            tmp, root, home = make_sandbox()
            with tmp:
                plan_file = Path(tmp.name) / "plan.json"
                plan = run_clean_json(root, home, "plan", "--categories", "trash", "--ai-origin")
                plan_file.write_text(json.dumps(plan), encoding="utf-8")

                first = run_clean_json(root, home, "run", "--plan-file", str(plan_file), "--delete-mode", "trash")
                second = run_clean_json(root, home, "run", "--plan-file", str(plan_file), "--delete-mode", "trash")

        token1 = cast(dict[str, Any], first["ai_confirmation_summary"])["confirmation_token"]
        token2 = cast(dict[str, Any], second["ai_confirmation_summary"])["confirmation_token"]
        self.assertTrue(token1)
        self.assertEqual(token1, token2)


if __name__ == "__main__":
    unittest.main()
