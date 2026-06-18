from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CLI = PROJECT_ROOT / "cleanmac.py"


def run_cli(*args: str, root: Path, home: Path) -> dict:
    env = os.environ.copy()
    env["CLEANMAC_TEST_MODE"] = "1"
    env["CLEANMAC_TEST_NO_AUTH"] = "1"
    result = subprocess.run(
        [sys.executable, str(CLI), "--json", "--root", str(root), "--home", str(home), *args],
        text=True,
        capture_output=True,
        check=True,
        env=env,
    )
    return json.loads(result.stdout)


class AIHostScenarioTests(unittest.TestCase):
    def test_safe_ai_host_plan_to_dry_run_sequence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "root"
            home = root / "Users" / "tester"
            trash = home / ".Trash"
            downloads = home / "Downloads"
            downloads.mkdir(parents=True)
            trash.mkdir(parents=True)
            candidate = downloads / "old-cache.tmp"
            candidate.write_text("cache", encoding="utf-8")
            plan_file = Path(tmp) / "plan.json"

            capabilities = run_cli("capabilities", root=root, home=home)
            self.assertEqual(capabilities["schema"], "cleanmac.capabilities.v1")
            self.assertTrue(capabilities["ai_readiness"]["ready"])

            plan = run_cli("clean", "plan", "--categories", "downloads", "--ai-origin", root=root, home=home)
            plan_file.write_text(json.dumps(plan), encoding="utf-8")
            self.assertEqual(plan["schema"], "cleanmac.plan.v1")
            self.assertTrue(plan["ai_origin"])

            validation = run_cli("clean", "validate-plan", "--plan-file", str(plan_file), root=root, home=home)
            self.assertTrue(validation["valid"], validation)

            simulation = run_cli(
                "clean",
                "policy-simulate",
                "--plan-file",
                str(plan_file),
                "--execute",
                "--delete-mode",
                "trash",
                "--require-plan-context",
                "--require-confirmation-token",
                root=root,
                home=home,
            )
            self.assertFalse(simulation["allowed"])
            blocking_codes = {row["code"] for row in simulation["blocking_reasons"]}
            self.assertIn("AI_ORIGIN_REQUIRES_CONFIRMATION_TOKEN", blocking_codes)

            dry_run = run_cli(
                "clean", "run", "--plan-file", str(plan_file), "--delete-mode", "trash", root=root, home=home
            )
            self.assertTrue(dry_run["dry_run"])
            self.assertTrue(dry_run["ai_confirmation_summary"]["confirmation_token_embedded"])


if __name__ == "__main__":
    unittest.main()
