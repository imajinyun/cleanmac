## Pytest Governance Round: AI Readiness Tests

Date: 2026-06-24

### Goal

Continue the incremental pytest migration by moving the AI readiness regression tests out of the
legacy `unittest` runner while preserving AI Host safety coverage and smoke-gate behavior.

### Scope

- `tests/test_ai_readiness.py`
- `Makefile`

### Out of Scope

- Do not migrate `test_cleanmac.py`.
- Do not migrate `tests/test_mcp_server.py`.
- Do not migrate the broad `tests/test_ai_eval.py` suite in this round.
- Do not change production AI readiness behavior.

### Tasks

1. Migrate `tests/test_ai_readiness.py` to pytest-native module-level tests.
   - Replace `unittest.TestCase` with plain test functions.
   - Replace `self.assert*` calls with pytest assertions.
   - Keep `unittest.mock.patch` where it is the simplest local patching mechanism.
   - Remove the `unittest.main()` entrypoint.

2. Wire migrated readiness tests into pytest governance.
   - Add `tests/test_ai_readiness.py` to `PYTEST_AI_ROBUSTNESS_TARGETS`.
   - Update `pytest-governance-smoke` expected robustness targets.
   - Move `tests.test_ai_readiness` from the `ai-host-smoke` unittest segment into the pytest segment.
   - Preserve remaining legacy unittest modules in `ai-host-smoke`.

3. Validate the migration.
   - `python3 -m compileall -q tests/test_ai_readiness.py`
   - `rg -n "import unittest|unittest\\.TestCase|unittest\\.main|self\\.assert" tests/test_ai_readiness.py`
   - `make pytest-governance-smoke`
   - `make pytest-test`
   - `make ai-host-smoke`

### Expected Outcome

AI readiness coverage becomes pytest-native, AI robustness governance tracks it explicitly, and
`ai-host-smoke` keeps full coverage without relying on `unittest` for this module.
