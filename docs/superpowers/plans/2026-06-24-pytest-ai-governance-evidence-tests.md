# Pytest Governance Plan: AI Governance and Host Evidence Tests

Date: 2026-06-24

## Objective

Continue the incremental pytest migration by converting two AI Host governance test modules from `unittest.TestCase` to pytest-native tests:

- `tests/test_ai_governance.py`
- `tests/test_ai_host_evidence.py`

This is a test-only governance round. It must preserve cleanmac's zero-resident product boundary, dry-run defaults, no-auth test defaults, and existing AI Host evidence-chain smoke coverage.

## Scope Decisions

- `LANG=python`
- `scope_type=non_diff`
- `BUG_MAP=[]`
- Do not migrate broad legacy `test_cleanmac.py`.
- Do not migrate `tests/test_mcp_server.py` in this round.
- Do not migrate `tests/test_ai_host_scenarios.py` in this round because it has broader sandboxed CLI workflow coverage.
- Do not change production AI Host, MCP, deletion, protection, or release behavior.
- Keep `.harness/` and `.harness/store.json` as ignored runtime queue state.

## Tasks

### Task 1: Migrate AI governance tests to pytest

Convert `tests/test_ai_governance.py` from `unittest.TestCase` to pytest-native tests.

Acceptance:

- No `import unittest`, `unittest.TestCase`, `unittest.main`, or `self.assert*` remains in the file.
- The shared `ai-governance-advice` CLI payload is provided through a pytest fixture rather than `setUpClass`.
- Existing assertions for governance schema, ready status, default policy, release gates, recommendations, route coverage, and validation failures remain covered.

### Task 2: Migrate AI Host evidence tests to pytest

Convert `tests/test_ai_host_evidence.py` from `unittest.TestCase` to pytest-native tests.

Acceptance:

- No `import unittest`, `unittest.TestCase`, `unittest.main`, or `self.assert*` remains in the file.
- Existing assertions for AI Host evidence readiness, non-destructive/dry-run contract, candidate evidence chain, MCP resource/prompt/tool evidence, runtime denial samples, contract validation, and CLI release gate commands remain covered.

### Task 3: Wire AI Host smoke and pytest governance

Update Makefile governance so the migrated files are exercised through pytest while preserving AI Host smoke coverage.

Acceptance:

- `PYTEST_AI_ROBUSTNESS_TARGETS` includes `tests/test_ai_governance.py` and `tests/test_ai_host_evidence.py`.
- `pytest-governance-smoke` expects those targets.
- `ai-host-smoke` runs the migrated files in the existing temporary-venv pytest segment.
- Remaining legacy AI/MCP modules continue to run under `python -m unittest`.
- `make pytest-governance-smoke` passes.
- `make pytest-test` passes.
- `make ai-host-smoke` passes.

## Validation

Run:

```bash
python3 -m compileall -q tests/test_ai_governance.py tests/test_ai_host_evidence.py
rg -n "import unittest|unittest\\.TestCase|unittest\\.main|self\\.assert" tests/test_ai_governance.py tests/test_ai_host_evidence.py
make pytest-governance-smoke
make pytest-test
make ai-host-smoke
```

## Rollback

If the AI Host smoke runner exposes pytest incompatibility, keep the test conversions but temporarily limit the Makefile wiring to `PYTEST_AI_ROBUSTNESS_TARGETS` until the smoke runner can be updated safely.
