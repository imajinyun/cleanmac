# Pytest Governance Plan: AI Host Policy and Runbook Tests

Date: 2026-06-24

## Objective

Continue the incremental pytest migration by converting two AI Host contract test modules from `unittest.TestCase` to pytest-native function tests:

- `tests/test_ai_runbook.py`
- `tests/test_ai_host_policy.py`

This is a test-only governance round. It must preserve cleanmac's zero-resident product boundary, dry-run defaults, no-auth test defaults, and existing AI Host safety assertions.

## Scope Decisions

- `LANG=python`
- `scope_type=non_diff`
- `BUG_MAP=[]`
- Do not migrate broad legacy `test_cleanmac.py`.
- Do not migrate `tests/test_mcp_server.py` in this round.
- Do not change production AI Host, MCP, deletion, protection, or release behavior.
- Keep `.harness/` and `.harness/store.json` as ignored runtime queue state.

## Tasks

### Task 1: Migrate AI runbook tests to pytest

Convert `tests/test_ai_runbook.py` from a `unittest.TestCase` wrapper to a module-level pytest function.

Acceptance:

- No `import unittest`, `unittest.TestCase`, `unittest.main`, or `self.assert*` remains in the file.
- The test still invokes `cleanmac.py --json ai-runbook`.
- All existing assertions about dry-run-first workflow, zero-resident lifecycle, no GUI/TUI/daemon behavior, and destructive execution gates remain covered.

### Task 2: Migrate AI Host policy tests to pytest

Convert `tests/test_ai_host_policy.py` from `unittest.TestCase` to pytest-native tests.

Acceptance:

- No `import unittest`, `unittest.TestCase`, `unittest.main`, or `self.assert*` remains in the file.
- The shared `ai-host-policy` CLI payload is provided through a pytest fixture rather than `setUpClass`.
- Existing assertions for host policy schema, runtime lifecycle obligations, transport restrictions, auto-call deny rules, execution gate requirements, validation failures, and tool-call decisions remain covered.

### Task 3: Wire AI Host pytest governance

Update Makefile governance so the migrated files are exercised through pytest while preserving AI Host smoke coverage.

Acceptance:

- `PYTEST_AI_ROBUSTNESS_TARGETS` includes `tests/test_ai_runbook.py` and `tests/test_ai_host_policy.py`.
- `pytest-governance-smoke` expects those targets.
- `ai-host-smoke` uses pytest for the migrated modules and keeps the remaining legacy unittest modules on `python -m unittest`.
- `make pytest-governance-smoke` passes.
- `make pytest-test` passes.
- `make ai-host-smoke` passes.

## Validation

Run:

```bash
python3 -m compileall -q tests/test_ai_runbook.py tests/test_ai_host_policy.py
rg -n "import unittest|unittest\\.TestCase|unittest\\.main|self\\.assert" tests/test_ai_runbook.py tests/test_ai_host_policy.py
make pytest-governance-smoke
make pytest-test
make ai-host-smoke
```

## Rollback

If `ai-host-smoke` exposes an incompatibility with pytest invocation, keep the test function conversions but split the Makefile migration so only `pytest-test` owns these modules until the smoke runner can be safely updated.
