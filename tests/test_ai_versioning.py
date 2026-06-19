from __future__ import annotations

import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CLI = PROJECT_ROOT / "cleanmac.py"
CLEANCLI_DIR = PROJECT_ROOT / "cleancli"

SCHEMA_PATTERN = re.compile(r'"schema"\s*:\s*"(cleanmac\.[a-zA-Z0-9._-]+\.v\d+)"')


class AISchemaRegistryTests(unittest.TestCase):
    def test_registry_command_emits_schema_inventory(self) -> None:
        result = subprocess.run(
            [sys.executable, str(CLI), "--json", "ai-schema-registry"],
            text=True,
            capture_output=True,
            check=True,
        )
        report = json.loads(result.stdout)

        self.assertEqual(report["schema"], "cleanmac.ai-schema-registry.v1")
        self.assertGreaterEqual(report["entry_count"], 15)
        names = {entry["name"] for entry in report["entries"]}
        self.assertIn("cleanmac.ai-readiness.v1", names)
        self.assertIn("cleanmac.ai-runbook.v1", names)
        self.assertIn("cleanmac.ai-tool-decision-matrix.v1", names)
        self.assertIn("cleanmac.ai-eval-run.v1", names)
        for entry in report["entries"]:
            self.assertIn("name", entry)
            self.assertIn("version", entry)
            self.assertIn("module", entry)
            self.assertIn("stability", entry)

    def test_registry_covers_every_v1_schema_emitted_by_codebase(self) -> None:
        from cleancli import ai_versioning

        emitted: set[str] = set()
        for path in CLEANCLI_DIR.rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            emitted.update(SCHEMA_PATTERN.findall(text))
        for path in (PROJECT_ROOT / "scripts").rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            emitted.update(SCHEMA_PATTERN.findall(text))

        registered = {entry["name"] for entry in ai_versioning.render_ai_schema_registry()["entries"]}
        missing = sorted(emitted - registered)
        self.assertEqual(missing, [], f"Schemas missing from registry: {missing}")

    def test_registry_metadata_is_deterministic_and_documents_compatibility_policy(self) -> None:
        from cleancli import ai_versioning

        first = ai_versioning.render_ai_schema_registry()
        second = ai_versioning.render_ai_schema_registry()

        self.assertEqual(first, second)
        self.assertEqual(first["entry_count"], len(first["entries"]))
        self.assertEqual(first["supported_plan_schemas"][0], "cleanmac.plan.v1")
        self.assertIn("cleanmac.clean.v1", first["supported_plan_schemas"])
        self.assertIn("cleanmac.clean-plan.v1", first["supported_plan_schemas"])
        self.assertIn("Breaking changes require a new vN suffix", first["compatibility_policy"]["stable"])
        self.assertIn("subject to change", first["compatibility_policy"]["internal"])
        self.assertEqual({entry["version"] for entry in first["entries"]}, {1})

    def test_plan_schema_negotiation_accepts_only_supported_schema_versions(self) -> None:
        from cleancli.ai_versioning import negotiate_plan_schema

        self.assertEqual(
            negotiate_plan_schema({"schema": "cleanmac.plan.v1"}),
            {
                "accepted": True,
                "schema": "cleanmac.plan.v1",
                "reason": "supported",
                "latest_supported_schema": "cleanmac.plan.v1",
            },
        )
        self.assertEqual(
            negotiate_plan_schema({}),
            {"accepted": False, "schema": "", "reason": "missing-schema-field"},
        )
        self.assertEqual(
            negotiate_plan_schema({}, allow_legacy_missing=True),
            {
                "accepted": True,
                "schema": "",
                "reason": "legacy-missing-schema-field",
                "latest_supported_schema": "cleanmac.plan.v1",
            },
        )
        self.assertEqual(
            negotiate_plan_schema({"schema": "cleanmac.clean-plan.v2"}),
            {
                "accepted": False,
                "schema": "cleanmac.clean-plan.v2",
                "reason": "unsupported-schema-version",
                "latest_supported_schema": "cleanmac.plan.v1",
            },
        )


if __name__ == "__main__":
    unittest.main()
