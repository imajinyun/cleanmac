# Pytest Governance Plan: AI Self-Test and Decision Matrix Tests

Date: 2026-06-24

## Objective

Continue the incremental pytest migration by converting two small AI Host governance test modules from `unittest.TestCase` to pytest-native tests:

- `tests/test_ai_self_test.py`
- `tests/test_ai_decision_matrix.py`

This is a test-only governance round. It must preserve cleanmac's zero-resident product boundary, dry-run defaults, no-auth test defaults, and existing AI Host smoke coverage.

## Scope Decisions

- `LANG=python`
- `scope_type=non_diff`
- `BUG_MAP=[]`
- Do not migrate broad legacy `test_cleanmac.py`.
- Do not migrate `tests/test_mcp_server.py` in this round.
- Do not change production AI Host, MCP, deletion, protection, or release behavior.
- Keep `.harness/` and `.harness/store.json` as ignored runtime queue state.

## Tasks

### Task 1: Migrate AI self-test tests to pytest

Convert `tests/test_ai_self_test.py` from a `unittest.TestCase` wrapper to pytest-native module-level tests.

Acceptance:

- No `import unittest`, `unittest.TestCase`, `unittest.main`, or `self.assert*` remains in the file.
- The test still covers the `cleancli.ai_self_test` owner module and `cleancli.core` re-export parity.
- The CLI test still invokes `cleanmac.py --json ai-self-test`.
- Existing assertions for schema, passed checks, runtime lifecycle, decision matrix, eval pack, governance advice, host policy, contract validation, and MCP transport remain covered.

### Task 2: Migrate AI decision matrix tests to pytest

Convert `tests/test_ai_decision_matrix.py` from `unittest.TestCase` to pytest-native module-level tests.

Acceptance:

- No `import unittest`, `unittest.TestCase`, `unittest.main`, or `self.assert*` remains in the file.
- Existing assertions for tool boundaries, dry-run-first policy, no-shell policy, destructive execute gates, MCP annotations, and runbook phase tool coverage remain covered.

### Task 3: Wire AI Host smoke and pytest governance

Update Makefile governance so the migrated files are exercised through pytest while preserving AI Host smoke coverage.

Acceptance:

- `PYTEST_AI_ROBUSTNESS_TARGETS` includes `tests/test_ai_self_test.py` and `tests/test_ai_decision_matrix.py`.
- `pytest-governance-smoke` expects those targets.
- `ai-host-smoke` runs the migrated files in the existing temporary-venv pytest segment.
- Remaining legacy AI/MCP modules continue to run under `python -m unittest`.
- `make pytest-governance-smoke` passes.
- `make pytest-test` passes.
- `make ai-host-smoke` passes.

## Validation

Run:

```bash
python3 -m compileall -q tests/test_ai_self_test.py tests/test_ai_decision_matrix.py
rg -n "import unittest|unittest\\.TestCase|unittest\\.main|self\\.assert" tests/test_ai_self_test.py tests/test_ai_decision_matrix.py
make pytest-governance-smoke
make pytest-test
make ai-host-smoke
```

## Rollback

If the AI Host smoke runner exposes pytest incompatibility, keep the test conversions but temporarily limit the Makefile wiring to `PYTEST_AI_ROBUSTNESS_TARGETS` until the smoke runner can be updated safely.
