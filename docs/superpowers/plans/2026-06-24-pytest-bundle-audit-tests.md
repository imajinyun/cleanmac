## Pytest Governance Round: Bundle Audit Tests

Date: 2026-06-24

### Goal

Continue the incremental pytest migration by moving the small bundle drift audit
regression suite out of the legacy `unittest` runner while preserving the
existing bundle audit and macOS smoke gates.

### Scope

- `tests/test_bundle_audit.py`
- `Makefile`

### Out of Scope

- Do not migrate `test_cleanmac.py`.
- Do not migrate `tests/test_mcp_server.py`.
- Do not migrate `tests/test_ai_eval.py`.
- Do not change `scripts/audit_bundle_drift.py` behavior.

### Tasks

1. Migrate `tests/test_bundle_audit.py` to pytest-native module-level tests.
   - Replace `unittest.TestCase` with plain test functions.
   - Replace `TemporaryDirectory` with pytest `tmp_path`.
   - Replace `self.assert*` calls with pytest assertions.
   - Remove the `unittest.main()` entrypoint.

2. Wire bundle audit smoke coverage through pytest.
   - Update `bundle-audit-smoke` to run `tests/test_bundle_audit.py` with pytest.
   - Update `macos-smoke` to keep the existing focused `test_cleanmac` unittest
     selections while running `tests/test_bundle_audit.py` through pytest.
   - Preserve `tests.test_sudo_guard` in the unittest segment.

3. Validate the migration.
   - `python3 -m compileall -q tests/test_bundle_audit.py`
   - `rg -n "import unittest|unittest\\.TestCase|unittest\\.main|self\\.assert" tests/test_bundle_audit.py`
   - `make bundle-audit-smoke`
   - `make macos-smoke`
   - `make pytest-test`

### Expected Outcome

Bundle drift audit coverage becomes pytest-native and still participates in
both the dedicated bundle audit smoke and broader macOS smoke gates.
