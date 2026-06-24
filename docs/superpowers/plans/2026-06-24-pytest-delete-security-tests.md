# Cleanmac Pytest Delete Security Tests Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve the next small unittest migration slice by converting delete boundary and security scan tests to pytest-native style and wiring them into the pytest governance target set.

**Architecture:** This is a test-only modernization. `tests/test_delete_ops.py` already uses module-level pytest functions but still depends on `unittest.TestCase()` assertion helpers; `tests/test_security_scan.py` still uses a `unittest.TestCase` wrapper and `TemporaryDirectory`. The migration preserves existing safety assertions, adds the files to the project-standard temporary-venv pytest target, and updates `AGENTS.md` guidance for this pytest-owned slice.

**Tech Stack:** Python 3.10+, pytest, native `assert`, `pytest.raises`, `tmp_path`, Makefile pytest targets, existing cleanmac delete and security-scan helpers.

---

## Workflow Checkpoints

- Step1: Test preparation completed with `BITS_TMP_ROOT=/var/folders/57/pqx08bk577x758hnslxkfhm40000gn/T/tmp.65HNooZx83`.
- Step2: `LANG=python`; `EXEC_SOURCE=`; project convention requires `make pytest-test` for pytest parity validation.
- Step3: `scope_type=non_diff`; `TARGETS=[tests/test_delete_ops.py, tests/test_security_scan.py, Makefile, AGENTS.md]`.
- Step4: `BUG_MAP=[]`; this round migrates test style and governance targets, not defect-probing behavior.

## File Structure

- Modify: `tests/test_delete_ops.py`
  - Replace residual `unittest.TestCase()` assertion helpers with `pytest.raises` and direct loop assertions.
- Modify: `tests/test_security_scan.py`
  - Convert `SecurityScanTests(unittest.TestCase)` methods into module-level pytest functions and replace `TemporaryDirectory` with `tmp_path`.
- Modify: `Makefile`
  - Add `tests/test_delete_ops.py` and `tests/test_security_scan.py` to `PYTEST_SAFE_TARGETS` and update `pytest-governance-smoke` expectations.
- Modify: `AGENTS.md`
  - Update the delete-ops module-specific validation command for the pytest-owned helper tests while preserving the existing high-risk `test_cleanmac.py` unittest commands.

## Non-Goals

- Do not migrate broad legacy `test_cleanmac.py`.
- Do not convert `tests/test_mcp_server.py`, `tests/test_ai_runbook.py`, `tests/test_ai_decision_matrix.py`, or other files still directly invoked by `ai-host-smoke`.
- Do not change production deletion behavior, security scan rules, MCP, AI Host, release, or governance logic.
- Do not add GUI, TUI, daemon, login item, background scan, or resident-process behavior.
- Do not commit `.harness/` runtime queue state.

## Task 1: Migrate Delete Ops Helper Tests To Pytest Assertions

**Files:**
- Modify: `tests/test_delete_ops.py`

- [ ] **Step 1: Replace imports**

Replace:

```python
import unittest
from pathlib import Path
from unittest import mock
```

with:

```python
from pathlib import Path
from unittest import mock

import pytest
```

- [ ] **Step 2: Replace exception assertions**

Replace forms such as:

```python
with unittest.TestCase().assertRaises(RuntimeError):
    delete_ops.validate_deletion_path(path, policy=policy)
```

with:

```python
with pytest.raises(RuntimeError):
    delete_ops.validate_deletion_path(path, policy=policy)
```

Replace regex assertions with:

```python
with pytest.raises(RuntimeError, match="control characters"):
    delete_ops.validate_deletion_path(target, policy=policy)
```

- [ ] **Step 3: Replace subTest loops**

Replace:

```python
for path in rejected_paths:
    with unittest.TestCase().subTest(path=str(path)):
        with unittest.TestCase().assertRaises(RuntimeError):
            delete_ops.validate_deletion_path(path, policy=policy)
```

with:

```python
for path in rejected_paths:
    with pytest.raises(RuntimeError):
        delete_ops.validate_deletion_path(path, policy=policy)
```

Keep allowed-path assertions direct:

```python
for path in allowed_paths:
    assert delete_ops.validate_deletion_path(path, policy=policy) == path
```

- [ ] **Step 4: Run focused validation**

Run:

```bash
tmpdir=$(mktemp -d)
python3 -m venv "$tmpdir/venv"
"$tmpdir/venv/bin/python" -m pip install --upgrade pip
"$tmpdir/venv/bin/python" -m pip install -e '.[test]'
CLEANMAC_TEST_MODE=1 CLEANMAC_TEST_NO_AUTH=1 PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS="-p no:cacheprovider" "$tmpdir/venv/bin/python" -m pytest tests/test_delete_ops.py -q
rm -R "$tmpdir"
```

Expected: all delete ops helper tests pass.

## Task 2: Migrate Security Scan Tests To Pytest Style

**Files:**
- Modify: `tests/test_security_scan.py`

- [ ] **Step 1: Replace imports and class wrapper**

Remove:

```python
import unittest
from tempfile import TemporaryDirectory

class SecurityScanTests(unittest.TestCase):
```

Keep helper loading and convert each method into a module-level pytest function:

```python
def test_security_scan_flags_raw_delete_and_privileged_business_calls(tmp_path: Path) -> None:
def test_security_scan_flags_python_shell_strings_and_absolute_commands(tmp_path: Path) -> None:
def test_security_scan_ignores_local_virtualenvs(tmp_path: Path) -> None:
def test_security_scan_flags_shell_privileged_commands(tmp_path: Path) -> None:
def test_security_scan_flags_workflow_privileged_run_blocks(tmp_path: Path) -> None:
def test_security_scan_allows_test_runner_privileged_stubs(tmp_path: Path) -> None:
def test_security_scan_allows_delete_ops_boundary(tmp_path: Path) -> None:
def test_security_scan_flags_gui_tui_and_resident_product_surfaces(tmp_path: Path) -> None:
```

- [ ] **Step 2: Replace temporary directories**

Replace:

```python
with TemporaryDirectory() as tmp:
    root = Path(tmp)
```

with:

```python
root = tmp_path
```

Use `tmp_path` once per test function to preserve isolation.

- [ ] **Step 3: Replace unittest assertions**

Use direct pytest assertions:

```python
assert any("privileged command 'sudo'" in violation for violation in violations), violations
assert violations == []
assert any("forbidden TUI framework import 'curses'" in violation for violation in violations), violations
```

- [ ] **Step 4: Remove unittest main guard**

Remove:

```python
if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 5: Run focused validation**

Run:

```bash
tmpdir=$(mktemp -d)
python3 -m venv "$tmpdir/venv"
"$tmpdir/venv/bin/python" -m pip install --upgrade pip
"$tmpdir/venv/bin/python" -m pip install -e '.[test]'
CLEANMAC_TEST_MODE=1 CLEANMAC_TEST_NO_AUTH=1 PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS="-p no:cacheprovider" "$tmpdir/venv/bin/python" -m pytest tests/test_security_scan.py -q
rm -R "$tmpdir"
```

Expected: all security scan tests pass.

## Task 3: Wire Delete And Security Tests Into Pytest Governance

**Files:**
- Modify: `Makefile`
- Modify: `AGENTS.md`

- [ ] **Step 1: Extend pytest safe targets**

Change:

```make
PYTEST_SAFE_TARGETS := tests/test_release_readiness.py tests/test_release_orchestration.py tests/test_release_artifacts.py tests/test_path_safety.py tests/test_trash_mode.py
```

to:

```make
PYTEST_SAFE_TARGETS := tests/test_release_readiness.py tests/test_release_orchestration.py tests/test_release_artifacts.py tests/test_path_safety.py tests/test_trash_mode.py tests/test_delete_ops.py tests/test_security_scan.py
```

- [ ] **Step 2: Update pytest-governance-smoke expectations**

Update the inline `expected` list to:

```python
expected = [
    "tests/test_release_readiness.py",
    "tests/test_release_orchestration.py",
    "tests/test_release_artifacts.py",
    "tests/test_path_safety.py",
    "tests/test_trash_mode.py",
    "tests/test_delete_ops.py",
    "tests/test_security_scan.py",
]
```

- [ ] **Step 3: Update AGENTS delete-ops validation guidance**

Replace the helper module line in the `cleancli/delete_ops.py` section:

```bash
python3 -m unittest tests.test_delete_ops tests.test_path_safety tests.test_trash_mode -v
```

with:

```bash
make pytest-test
```

Keep the targeted `test_cleanmac.CleanMacCLITests...` unittest commands and `make docker-test` unchanged.

- [ ] **Step 4: Run governance and full pytest validation**

Run:

```bash
make pytest-governance-smoke
make pytest-test
```

Expected:

```text
pytest-governance-smoke passed
pytest-test passes with the expanded safe pytest target set
```

## Acceptance Criteria

- `tests/test_delete_ops.py` has no `unittest` import and no `unittest.TestCase()` helper usage.
- `tests/test_security_scan.py` has no `unittest` import, no `unittest.TestCase`, no `self.assert*`, no `TemporaryDirectory`, and no `unittest.main()`.
- `Makefile` pytest safe target governance includes `tests/test_delete_ops.py` and `tests/test_security_scan.py`.
- `AGENTS.md` points this pytest-owned helper slice at `make pytest-test`.
- `make pytest-governance-smoke` and `make pytest-test` pass.
- No production behavior changes are introduced.
