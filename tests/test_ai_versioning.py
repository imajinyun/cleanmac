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
        self.assertIn("cleanmac.release-readiness.v1", names)
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
        for schema_name in ai_versioning.AI_HOST_CRITICAL_SCHEMAS:
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
        self.assertIn("cleanmac.release-artifact-manifest.v1", entries)
        self.assertIn("json_schema", entries["cleanmac.release-artifact-manifest.v1"])
        self.assertIn("cleanmac.release-readiness.v1", entries)
        self.assertIn("json_schema", entries["cleanmac.release-readiness.v1"])
        self.assertIn("cleanmac.release-diagnostics.v1", entries)
        self.assertIn("cleanmac.release-evidence.v1", entries)
        self.assertIn("cleanmac.release-operator-summary.v1", entries)
        self.assertTrue(entries["cleanmac.release-evidence.v1"]["release_critical"])
        self.assertEqual(entries["cleanmac.release-evidence.v1"]["owner_area"], "release")

    def test_contract_validator_covers_ai_host_critical_schema_shapes(self) -> None:
        from cleancli.ai_versioning import (
            AI_HOST_CRITICAL_SCHEMAS,
            CORE_CONTRACT_SCHEMAS,
            render_ai_contract_samples,
            validate_contract_payload,
        )

        self.assertLessEqual(set(AI_HOST_CRITICAL_SCHEMAS), set(CORE_CONTRACT_SCHEMAS))
        host_policy = {
            "schema": "cleanmac.ai-host-policy.v1",
            "valid": True,
            "default_decision": "deny",
            "auto_call": {
                "allow": [],
                "deny": ["cleanmac_execute_plan", "cleanmac_startup_disable", "cleanmac_privacy_execute"],
            },
            "execution_gate": {"auto_call_allowed": False},
        }
        self.assertTrue(validate_contract_payload("cleanmac.ai-host-policy.v1", host_policy)["valid"])

        missing_auto_call = dict(host_policy)
        del missing_auto_call["auto_call"]
        missing_report = validate_contract_payload("cleanmac.ai-host-policy.v1", missing_auto_call)
        self.assertFalse(missing_report["valid"])
        self.assertEqual(missing_report["errors"][0]["code"], "MISSING_REQUIRED_FIELD")

        wrong_schema = dict(host_policy)
        wrong_schema["schema"] = "cleanmac.ai-host-policy.v2"
        const_report = validate_contract_payload("cleanmac.ai-host-policy.v1", wrong_schema)
        self.assertFalse(const_report["valid"])
        self.assertEqual(const_report["errors"][0]["code"], "CONST_MISMATCH")

        governance_advice = {
            "schema": "cleanmac.ai-governance-advice.v1",
            "ready_for_llm_calling": True,
            "governance_score": {"level": "strong"},
            "default_policy": {"shell_allowed": False},
            "required_host_controls": ["Load host policy before execution."],
            "recommended_call_sequence": ["cleanmac_capabilities"],
            "anti_patterns": ["Calling execute directly."],
            "governance_route": [{"id": "entrypoint-governance", "status": "satisfied"}],
            "release_gate_commands": [["make", "ai-governance-smoke"]],
            "recommendations": [{"id": "preflight-first"}],
        }
        self.assertTrue(validate_contract_payload("cleanmac.ai-governance-advice.v1", governance_advice)["valid"])

        eval_pack = {
            "schema": "cleanmac.ai-eval-pack.v1",
            "scenario_count": 1,
            "scenarios": [{"id": "discover_readiness"}],
            "allows_destructive_execution": False,
            "recommended_runner_command": ["cleanmac", "--json", "ai-eval-run", "--scenario", "smoke"],
        }
        self.assertTrue(validate_contract_payload("cleanmac.ai-eval-pack.v1", eval_pack)["valid"])

        eval_run = {
            "schema": "cleanmac.ai-eval-run.v1",
            "scenario": "smoke",
            "passed": True,
            "passed_count": 1,
            "failed_count": 0,
            "results": [{"id": "discover_readiness", "passed": True}],
        }
        self.assertTrue(validate_contract_payload("cleanmac.ai-eval-run.v1", eval_run)["valid"])

        release_readiness = {
            "schema": "cleanmac.release-readiness.v1",
            "destructive": False,
            "dry_run": True,
            "ready": True,
            "manual_review_required": False,
            "readiness_score": {"passed": 7, "total": 7, "level": "release-ready"},
            "failed_gate_ids": [],
            "gates": [
                {
                    "id": "ai-host-preflight-ready",
                    "passed": True,
                    "evidence_schema": "cleanmac.ai-host-preflight.v1",
                    "severity": "none",
                    "next_actions": [["make", "ai-host-smoke"]],
                }
            ],
            "release_gate_commands": [["make", "ai-host-smoke"]],
            "review_questions": ["Did ai-host-preflight pass before tool orchestration?"],
        }
        self.assertTrue(validate_contract_payload("cleanmac.release-readiness.v1", release_readiness)["valid"])
        invalid_release_readiness = dict(release_readiness)
        invalid_release_readiness["gates"] = [{"id": "ai-host-preflight-ready", "passed": True}]
        invalid_gate_report = validate_contract_payload("cleanmac.release-readiness.v1", invalid_release_readiness)
        self.assertFalse(invalid_gate_report["valid"])
        self.assertEqual(invalid_gate_report["errors"][0]["code"], "MISSING_REQUIRED_FIELD")

        release_diagnostics = {
            "schema": "cleanmac.release-diagnostics.v1",
            "destructive": False,
            "dry_run": True,
            "ready": False,
            "failed_gate_ids": ["release-artifact-manifest-valid"],
            "environment": {"platform": "darwin"},
            "artifacts": {"error_code": "RELEASE_ARTIFACT_MANIFEST_MISSING"},
            "recommended_commands": [["make", "release-artifacts-smoke"]],
        }
        self.assertTrue(validate_contract_payload("cleanmac.release-diagnostics.v1", release_diagnostics)["valid"])

        release_evidence = {
            "schema": "cleanmac.release-evidence.v1",
            "destructive": False,
            "dry_run": True,
            "ready": True,
            "artifact_manifest": {"schema": "cleanmac.release-artifact-manifest.v1", "valid": True},
            "release_readiness": {"schema": "cleanmac.release-readiness.v1", "ready": True},
            "assets": {"required": ["SBOM.json"], "missing": []},
        }
        self.assertTrue(validate_contract_payload("cleanmac.release-evidence.v1", release_evidence)["valid"])

        samples = render_ai_contract_samples()
        self.assertEqual(samples["schema"], "cleanmac.ai-contract-samples.v1")
        self.assertEqual(samples["sample_count"], len(samples["samples"]))
        self.assertEqual({sample["target_schema"] for sample in samples["samples"]}, set(AI_HOST_CRITICAL_SCHEMAS))
        for sample in samples["samples"]:
            self.assertTrue(sample["valid"], sample)
            validation = validate_contract_payload(sample["target_schema"], sample["payload"])
            self.assertTrue(validation["valid"], validation)

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
        coverage = summary["contract_schema_coverage"]
        self.assertEqual(coverage["missing_stable_ai_schema_fragments"], [])
        self.assertGreaterEqual(coverage["json_schema_fragment_count"], len(coverage["critical_schemas"]))

    def test_operational_plan_samples_expose_current_execute_gate_name(self) -> None:
        from cleancli.ai_versioning import render_ai_contract_samples, validate_contract_payload

        payloads = {sample["target_schema"]: sample["payload"] for sample in render_ai_contract_samples()["samples"]}
        startup = payloads["cleanmac.startup-plan.v1"]
        privacy = payloads["cleanmac.privacy-plan.v1"]
        self.assertTrue(startup["disable_plan"]["requires_explicit_execute"])
        self.assertTrue(privacy["privacy_plan"]["requires_explicit_execute"])
        self.assertTrue(startup["disable_plan"]["requires_explicit_future_execute"])
        self.assertTrue(privacy["privacy_plan"]["requires_explicit_future_execute"])
        self.assertTrue(validate_contract_payload("cleanmac.startup-plan.v1", startup)["valid"])
        self.assertTrue(validate_contract_payload("cleanmac.privacy-plan.v1", privacy)["valid"])

    def test_contract_validator_reports_nested_array_item_type_mismatch(self) -> None:
        from cleancli.ai_versioning import validate_contract_payload

        payload = {
            "schema": "cleanmac.ai-contract-samples.v1",
            "destructive": False,
            "dry_run": True,
            "sample_count": 1,
            "samples": ["not-an-object"],
        }

        report = validate_contract_payload("cleanmac.ai-contract-samples.v1", payload)

        self.assertFalse(report["valid"])
        self.assertEqual(report["error_count"], 1)
        self.assertEqual(report["errors"][0]["code"], "TYPE_MISMATCH")
        self.assertEqual(report["errors"][0]["path"], "$.samples[0]")

    def test_contract_validator_rejects_boolean_for_integer(self) -> None:
        from cleancli.ai_versioning import validate_contract_payload

        payload = {
            "schema": "cleanmac.ai-contract-samples.v1",
            "destructive": False,
            "dry_run": True,
            "sample_count": True,
            "samples": [],
        }

        report = validate_contract_payload("cleanmac.ai-contract-samples.v1", payload)

        self.assertFalse(report["valid"])
        self.assertEqual(report["error_count"], 1)
        self.assertEqual(report["errors"][0]["code"], "TYPE_MISMATCH")
        self.assertEqual(report["errors"][0]["path"], "$.sample_count")

    def test_contract_validator_reports_const_mismatch_before_type_walk(self) -> None:
        from cleancli.ai_versioning import validate_contract_payload

        payload = {
            "schema": "cleanmac.ai-contract-samples.v2",
            "destructive": False,
            "dry_run": True,
            "sample_count": 0,
            "samples": [],
        }

        report = validate_contract_payload("cleanmac.ai-contract-samples.v1", payload)

        self.assertFalse(report["valid"])
        self.assertEqual(report["error_count"], 1)
        self.assertEqual(report["errors"][0]["code"], "CONST_MISMATCH")
        self.assertEqual(report["errors"][0]["path"], "$.schema")

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
