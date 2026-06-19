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
            self.assertIn("kind", entry)
            self.assertIn("producer", entry)
            self.assertIn("consumers", entry)
            self.assertIn("latest", entry)
            self.assertIn("deprecated", entry)
            self.assertIn("replaced_by", entry)
            self.assertIn("compatibility", entry)
            self.assertIn("breaking_change_policy", entry["compatibility"])

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
        self.assertGreaterEqual(first["stable_schema_count"], 20)
        self.assertEqual(first["deprecated_schema_count"], 0)
        self.assertEqual(first["latest_plan_schema"], "cleanmac.plan.v1")
        self.assertEqual(first["supported_plan_schemas"][0], "cleanmac.plan.v1")
        self.assertIn("cleanmac.clean.v1", first["supported_plan_schemas"])
        self.assertIn("cleanmac.clean-plan.v1", first["supported_plan_schemas"])
        self.assertIn("Breaking changes require a new vN suffix", first["compatibility_policy"]["stable"])
        self.assertIn("subject to change", first["compatibility_policy"]["internal"])
        self.assertEqual({entry["version"] for entry in first["entries"]}, {1})
        entries = {entry["name"]: entry for entry in first["entries"]}
        self.assertTrue(entries["cleanmac.plan.v1"]["latest"])
        self.assertFalse(entries["cleanmac.clean.v1"]["latest"])
        self.assertFalse(entries["cleanmac.clean-plan.v1"]["latest"])
        self.assertEqual(entries["cleanmac.plan.v1"]["producer"], "clean plan")
        self.assertIn("validate-plan", entries["cleanmac.plan.v1"]["consumers"])

    def test_registry_exposes_core_json_schema_fragments(self) -> None:
        from cleancli import ai_versioning

        entries = {entry["name"]: entry for entry in ai_versioning.render_ai_schema_registry()["entries"]}
        for schema_name in (
            "cleanmac.plan.v1",
            "cleanmac.validate-plan.v1",
            "cleanmac.ai-policy-simulation.v1",
            "cleanmac.ai-schema-registry.v1",
            "cleanmac.ai-readiness.v1",
        ):
            self.assertIn("json_schema", entries[schema_name], schema_name)
            json_schema = entries[schema_name]["json_schema"]
            self.assertEqual(json_schema["type"], "object")
            self.assertIn("schema", json_schema["required"])
            self.assertEqual(json_schema["properties"]["schema"]["const"], schema_name)
            self.assertTrue(json_schema["additionalProperties"])

        plan_schema = entries["cleanmac.plan.v1"]["json_schema"]
        self.assertIn("destructive", plan_schema["required"])
        self.assertIn("dry_run", plan_schema["required"])
        self.assertEqual(plan_schema["properties"]["destructive"]["const"], False)
        self.assertEqual(plan_schema["properties"]["dry_run"]["const"], True)

    def test_contract_validator_reports_valid_missing_and_unsupported_payloads(self) -> None:
        from cleancli.ai_versioning import render_ai_contract_validation_summary, validate_contract_payload

        valid_plan = {
            "schema": "cleanmac.plan.v1",
            "destructive": False,
            "dry_run": True,
            "generated_at": "2026-06-19T00:00:00+00:00",
            "expires_at": "2026-06-19T00:30:00+00:00",
            "selected_category_keys": ["trash"],
            "candidate_fingerprints": [{"path": "/tmp/old.tmp", "exists": True}],
        }
        self.assertTrue(validate_contract_payload("cleanmac.plan.v1", valid_plan)["valid"])

        missing_required = dict(valid_plan)
        del missing_required["candidate_fingerprints"]
        missing_report = validate_contract_payload("cleanmac.plan.v1", missing_required)
        self.assertFalse(missing_report["valid"])
        self.assertEqual(missing_report["errors"][0]["code"], "MISSING_REQUIRED_FIELD")

        unsupported_report = validate_contract_payload("cleanmac.plan." + "v99", valid_plan)
        self.assertFalse(unsupported_report["valid"])
        self.assertEqual(unsupported_report["errors"][0]["code"], "UNSUPPORTED_SCHEMA")

        summary = render_ai_contract_validation_summary()
        self.assertEqual(summary["schema"], "cleanmac.ai-contract-validation-summary.v1")
        self.assertTrue(summary["valid"], summary)
        self.assertEqual(summary["failure_count"], 0)

    def test_plan_schema_negotiation_accepts_only_supported_schema_versions(self) -> None:
        from cleancli.ai_versioning import negotiate_plan_schema

        self.assertEqual(
            negotiate_plan_schema({"schema": "cleanmac.plan.v1"}),
            {
                "accepted": True,
                "schema": "cleanmac.plan.v1",
                "reason": "supported",
                "latest_supported_schema": "cleanmac.plan.v1",
                "legacy": False,
            },
        )
        self.assertEqual(
            negotiate_plan_schema({}),
            {
                "accepted": False,
                "schema": "",
                "reason": "missing-schema-field",
                "latest_supported_schema": "cleanmac.plan.v1",
                "legacy": False,
            },
        )
        self.assertEqual(
            negotiate_plan_schema({}, allow_legacy_missing=True),
            {
                "accepted": True,
                "schema": "",
                "reason": "legacy-missing-schema-field",
                "latest_supported_schema": "cleanmac.plan.v1",
                "legacy": True,
            },
        )
        self.assertEqual(
            negotiate_plan_schema({"schema": "cleanmac.clean-plan.v1"}),
            {
                "accepted": True,
                "schema": "cleanmac.clean-plan.v1",
                "reason": "supported",
                "latest_supported_schema": "cleanmac.plan.v1",
                "legacy": True,
            },
        )
        self.assertEqual(
            negotiate_plan_schema({"schema": "cleanmac.clean-plan.v2"}),
            {
                "accepted": False,
                "schema": "cleanmac.clean-plan.v2",
                "reason": "unsupported-schema-version",
                "latest_supported_schema": "cleanmac.plan.v1",
                "legacy": False,
            },
        )


if __name__ == "__main__":
    unittest.main()
