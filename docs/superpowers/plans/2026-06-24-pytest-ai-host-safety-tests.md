# Cleanmac Pytest AI Host Safety Tests Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve the next small unittest migration slice by converting AI Host integration and safety regression tests to pytest-native style while preserving existing unittest smoke gates.

**Architecture:** This is a test-only modernization. The selected files are not directly invoked by the active `ai-host-smoke` unittest module list, and the two safety tests are already standalone pytest-compatible functions with only residual `unittest` helpers. The migration keeps production cleanup, deletion, protection, AI Host, MCP, and release behavior unchanged, then expands Makefile pytest governance to cover this slice explicitly.

**Tech Stack:** Python 3.10+, pytest, native `assert`, `pytest.raises`, `pytest.mark.skipif`, temporary venv-backed Makefile pytest targets, existing cleanmac CLI and safety helpers.

---

## Workflow Checkpoints

- Step1: Test preparation completed with `BITS_TMP_ROOT=/var/folders/57/pqx08bk577x758hnslxkfhm40000gn/T/tmp.L5M1wEyYuv`.
- Step2: `LANG=python`; `EXEC_SOURCE=`; project convention requires `make pytest-test` for pytest parity validation.
- Step3: `scope_type=non_diff`; `TARGETS=[tests/test_ai_host_integration.py, tests/test_path_safety.py, tests/test_trash_mode.py]`.
- Step4: `BUG_MAP=[]`; this round migrates test style and governance targets, not defect-probing behavior.

## File Structure

- Modify: `tests/test_ai_host_integration.py`
  - Converts AI Host integration pack, evidence, preflight, CLI, and schema validation tests from `unittest.TestCase` to pytest functions.
- Modify: `tests/test_path_safety.py`
  - Replaces residual `unittest.skipIf` and `assertRaisesRegex` usage with pytest-native equivalents.
- Modify: `tests/test_trash_mode.py`
  - Replaces residual `unittest.skipIf` usage with pytest-native `pytest.mark.skipif`.
- Modify: `Makefile`
  - Adds `tests/test_ai_host_integration.py`, `tests/test_path_safety.py`, and `tests/test_trash_mode.py` to pytest target governance and updates `pytest-governance-smoke` expectations.

## Non-Goals

- Do not migrate broad legacy `test_cleanmac.py`.
- Do not migrate files or exact test methods that are still directly invoked through active `python -m unittest` smoke targets.
- Do not change production CLI, MCP, deletion, protection, AI Host, release, or governance behavior.
- Do not add GUI, TUI, daemon, login item, background scan, or resident-process behavior.
- Do not commit `.harness/` runtime queue state.

## Task 1: Migrate AI Host Integration Tests To Pytest Style

**Files:**
- Modify: `tests/test_ai_host_integration.py`

- [ ] **Step 1: Remove unittest import and class wrapper**

Remove:

```python
import unittest

class AIHostIntegrationPackTests(unittest.TestCase):
```

Convert each method into a module-level pytest function:

```python
def test_pack_aggregates_one_stop_host_discovery_metadata() -> None:
def test_pack_validates_against_registered_contract_schema() -> None:
def test_cli_emits_host_integration_pack() -> None:
def test_readiness_and_governance_recommend_integration_pack_entrypoint() -> None:
def test_evidence_reports_runtime_governance_audit_pack() -> None:
def test_preflight_reports_runtime_governance_gate() -> None:
def test_preflight_validates_against_registered_contract_schema() -> None:
def test_cli_emits_host_preflight() -> None:
```

- [ ] **Step 2: Replace unittest assertions with native asserts**

Use direct pytest assertion forms:

```python
assert pack["schema"] == "cleanmac.ai-host-integration-pack.v1"
assert pack["destructive"] is False
assert pack["dry_run"] is True
assert pack["ready"] is True, pack
assert "cleanmac://ai/host-integration-pack" in pack["mcp"]["resources"]
assert validation["valid"] is True, validation
assert validation["error_count"] == 0
```

- [ ] **Step 3: Remove unittest main guard**

Remove:

```python
if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 4: Run focused validation**

Run:

```bash
tmpdir=$(mktemp -d)
python3 -m venv "$tmpdir/venv"
"$tmpdir/venv/bin/python" -m pip install --upgrade pip
"$tmpdir/venv/bin/python" -m pip install -e '.[test]'
CLEANMAC_TEST_MODE=1 CLEANMAC_TEST_NO_AUTH=1 PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS="-p no:cacheprovider" "$tmpdir/venv/bin/python" -m pytest tests/test_ai_host_integration.py -q
rm -R "$tmpdir"
```

Expected: all AI Host integration tests pass.

## Task 2: Migrate Path Safety Test To Pytest Style

**Files:**
- Modify: `tests/test_path_safety.py`

- [ ] **Step 1: Replace unittest skip decorator**

Replace:

```python
import unittest

@unittest.skipIf(not hasattr(os, "symlink"), "symlink unsupported")
```

with:

```python
import pytest

@pytest.mark.skipif(not hasattr(os, "symlink"), reason="symlink unsupported")
```

- [ ] **Step 2: Replace exception assertion**

Replace:

```python
with unittest.TestCase().assertRaisesRegex(RuntimeError, "symlink pointing to protected path"):
    delete_ops.assert_safe_to_delete(link, policy=policy_for(root, home))
```

with:

```python
with pytest.raises(RuntimeError, match="symlink pointing to protected path"):
    delete_ops.assert_safe_to_delete(link, policy=policy_for(root, home))
```

- [ ] **Step 3: Run focused validation**

Run:

```bash
tmpdir=$(mktemp -d)
python3 -m venv "$tmpdir/venv"
"$tmpdir/venv/bin/python" -m pip install --upgrade pip
"$tmpdir/venv/bin/python" -m pip install -e '.[test]'
CLEANMAC_TEST_MODE=1 CLEANMAC_TEST_NO_AUTH=1 PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS="-p no:cacheprovider" "$tmpdir/venv/bin/python" -m pytest tests/test_path_safety.py -q
rm -R "$tmpdir"
```

Expected: the path safety symlink regression passes or is skipped on platforms without symlink support.

## Task 3: Migrate Trash Mode Test To Pytest Style

**Files:**
- Modify: `tests/test_trash_mode.py`

- [ ] **Step 1: Replace unittest skip decorator**

Replace:

```python
import unittest

@unittest.skipIf(not hasattr(os, "symlink"), "symlink unsupported")
```

with:

```python
import pytest

@pytest.mark.skipif(not hasattr(os, "symlink"), reason="symlink unsupported")
```

- [ ] **Step 2: Keep existing native assertions**

Keep the current pytest-native assertions:

```python
assert result.returncode != 0
assert (root / "Users/tester/Downloads/download.bin").exists()
assert list(routed.iterdir()) == []
```

- [ ] **Step 3: Run focused validation**

Run:

```bash
tmpdir=$(mktemp -d)
python3 -m venv "$tmpdir/venv"
"$tmpdir/venv/bin/python" -m pip install --upgrade pip
"$tmpdir/venv/bin/python" -m pip install -e '.[test]'
CLEANMAC_TEST_MODE=1 CLEANMAC_TEST_NO_AUTH=1 PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS="-p no:cacheprovider" "$tmpdir/venv/bin/python" -m pytest tests/test_trash_mode.py -q
rm -R "$tmpdir"
```

Expected: the Trash fail-closed regression passes or is skipped on platforms without symlink support.

## Task 4: Wire The New Pytest Slice Into Governance Targets

**Files:**
- Modify: `Makefile`

- [ ] **Step 1: Extend pytest safe targets**

Change:

```make
PYTEST_SAFE_TARGETS := tests/test_release_readiness.py tests/test_release_orchestration.py tests/test_release_artifacts.py
```

to:

```make
PYTEST_SAFE_TARGETS := tests/test_release_readiness.py tests/test_release_orchestration.py tests/test_release_artifacts.py tests/test_path_safety.py tests/test_trash_mode.py
```

- [ ] **Step 2: Extend pytest AI robustness targets**

Change:

```make
PYTEST_AI_ROBUSTNESS_TARGETS := tests/test_ai_versioning.py tests/test_mcp_protocol.py tests/test_ai_concurrency.py tests/test_ai_policy.py tests/test_ai_contract.py tests/test_ai_errors.py tests/test_ai_idempotency.py tests/test_ai_eval.py::AITracePersistenceTests
```

to:

```make
PYTEST_AI_ROBUSTNESS_TARGETS := tests/test_ai_versioning.py tests/test_mcp_protocol.py tests/test_ai_concurrency.py tests/test_ai_policy.py tests/test_ai_host_integration.py tests/test_ai_contract.py tests/test_ai_errors.py tests/test_ai_idempotency.py tests/test_ai_eval.py::AITracePersistenceTests
```

- [ ] **Step 3: Update pytest-governance-smoke expectations**

Update the inline `expected` list to:

```python
expected = [
    "tests/test_release_readiness.py",
    "tests/test_release_orchestration.py",
    "tests/test_release_artifacts.py",
    "tests/test_path_safety.py",
    "tests/test_trash_mode.py",
]
```

Update the inline `expected_robustness` list to:

```python
expected_robustness = [
    "tests/test_ai_versioning.py",
    "tests/test_mcp_protocol.py",
    "tests/test_ai_concurrency.py",
    "tests/test_ai_policy.py",
    "tests/test_ai_host_integration.py",
    "tests/test_ai_contract.py",
    "tests/test_ai_errors.py",
    "tests/test_ai_idempotency.py",
    "tests/test_ai_eval.py::AITracePersistenceTests",
]
```

- [ ] **Step 4: Run governance and full pytest validation**

Run:

```bash
make pytest-governance-smoke
make ai-robustness-smoke
make pytest-test
```

Expected:

```text
pytest-governance-smoke passed
ai-robustness-smoke passes with the expanded AI pytest target set
pytest-test passes with the expanded safe pytest target set
```

## Acceptance Criteria

- `tests/test_ai_host_integration.py` has no `unittest` import, no `unittest.TestCase`, no `self.assert*`, and no `unittest.main()`.
- `tests/test_path_safety.py` and `tests/test_trash_mode.py` use `pytest.mark.skipif`; path safety uses `pytest.raises`.
- `Makefile` pytest target governance includes the migrated files and `pytest-governance-smoke` enforces the updated lists.
- `make pytest-governance-smoke`, `make ai-robustness-smoke`, and `make pytest-test` pass.
- No production behavior changes are introduced.
