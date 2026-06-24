# Cleanmac Pytest AI Contract Tests Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve the existing AI contract, AI error, and AI idempotency unittest files by migrating them to pytest-native style and keeping them visible through cleanmac's pytest governance targets.

**Architecture:** This is a test-only migration. The selected files already validate stable AI-facing contracts, error taxonomy behavior, and idempotent AI workflow output; the change removes `unittest.TestCase` wrappers, keeps the same assertions, and updates Makefile pytest target governance so these pytest-native tests remain discoverable. No production cleanup, deletion, protection, AI Host, MCP, or release behavior changes.

**Tech Stack:** Python 3.10+, pytest, native `assert`, existing cleanmac AI helper APIs, existing `tests.helpers` sandbox/CLI helpers, Makefile pytest smoke targets.

---

## File Structure

- Modify: `tests/test_ai_contract.py`
  - Owns AI contract payload, core re-export, safety-chain, and version validation tests.
- Modify: `tests/test_ai_errors.py`
  - Owns AI error taxonomy, error report, and classifier tests.
- Modify: `tests/test_ai_idempotency.py`
  - Owns repeated AI workflow output stability and dry-run token stability tests.
- Modify: `Makefile`
  - Keeps the pytest AI robustness target list and governance smoke expectations synchronized with migrated pytest files.

## Non-Goals

- Do not migrate broad legacy tests such as `test_cleanmac.py`.
- Do not change production behavior or contract payload contents.
- Do not add GUI, TUI, daemon, login item, background scan, or resident-process behavior.
- Do not weaken dry-run defaults, confirmation-token gates, Trash routing, or operation-log evidence expectations.
- Do not commit `.harness/` runtime queue state.

## Task 1: Migrate AI Contract Tests To Pytest Style

**Files:**
- Modify: `tests/test_ai_contract.py`

- [ ] **Step 1: Remove unittest dependency**

Replace:

```python
import unittest
```

with no import, because the file only needs direct pytest collection.

- [ ] **Step 2: Convert the class wrapper to pytest functions**

Replace:

```python
class AIContractTests(unittest.TestCase):
    def test_ai_tool_contract_is_owned_outside_core_and_reexported(self) -> None:
```

with:

```python
def test_ai_tool_contract_is_owned_outside_core_and_reexported() -> None:
```

Repeat this for every test in the file:

```python
def test_ai_recommended_workflow_preserves_governed_execute_chain() -> None:
def test_ai_intent_hints_remain_readonly_for_analysis_and_uninstall_planning() -> None:
def test_ai_entrypoint_contract_covers_canonical_cli_surfaces() -> None:
def test_ai_safety_chain_contract_covers_non_bypassable_execute_path() -> None:
```

- [ ] **Step 3: Replace assertion methods with native asserts**

Use direct forms such as:

```python
assert contract == render_core_ai_tool_contract()
assert contract["schema"] == "cleanmac.ai-tool-contract.v1"
assert "clean run --execute" in contract["confirmation_required"]
assert execute["auto_call_allowed"] is False
assert execute["requires_user_confirmation"] is True
assert validation["valid"], validation
```

- [ ] **Step 4: Run focused validation**

Run:

```bash
tmpdir=$(mktemp -d)
python3 -m venv "$tmpdir/venv"
"$tmpdir/venv/bin/python" -m pip install --upgrade pip
"$tmpdir/venv/bin/python" -m pip install -e '.[test]'
CLEANMAC_TEST_MODE=1 CLEANMAC_TEST_NO_AUTH=1 PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS="-p no:cacheprovider" "$tmpdir/venv/bin/python" -m pytest tests/test_ai_contract.py -q
rm -R "$tmpdir"
```

Expected: pytest reports all `tests/test_ai_contract.py` tests passed.

## Task 2: Migrate AI Error Tests To Pytest Style

**Files:**
- Modify: `tests/test_ai_errors.py`

- [ ] **Step 1: Remove unittest dependency**

Replace:

```python
import unittest
```

with no import.

- [ ] **Step 2: Convert the class wrapper to pytest functions**

Use these exact test function names:

```python
def test_ai_error_taxonomy_is_owned_outside_core_and_reexported() -> None:
def test_ai_error_report_classifies_review_selection_failures() -> None:
def test_ai_error_classifier_keeps_argument_errors_machine_readable() -> None:
```

- [ ] **Step 3: Replace assertion methods with native asserts**

Use direct forms such as:

```python
assert taxonomy == render_core_ai_error_taxonomy()
assert {entry["code"] for entry in taxonomy} >= {
    "CLI_ARGUMENT_ERROR",
    "SELECTION_VALIDATION_FAILED",
    "OPERATION_LOG_UNAVAILABLE",
    "EXECUTION_REFUSED",
}
assert report["schema"] == "cleanmac.ai-error.v1"
assert report["safe_to_auto_retry"] is True
assert "cleanmac_review" in report["error"]["next_allowed_tools"]
```

- [ ] **Step 4: Run focused validation**

Run:

```bash
tmpdir=$(mktemp -d)
python3 -m venv "$tmpdir/venv"
"$tmpdir/venv/bin/python" -m pip install --upgrade pip
"$tmpdir/venv/bin/python" -m pip install -e '.[test]'
CLEANMAC_TEST_MODE=1 CLEANMAC_TEST_NO_AUTH=1 PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS="-p no:cacheprovider" "$tmpdir/venv/bin/python" -m pytest tests/test_ai_errors.py -q
rm -R "$tmpdir"
```

Expected: pytest reports all `tests/test_ai_errors.py` tests passed.

## Task 3: Migrate AI Idempotency Tests To Pytest Style

**Files:**
- Modify: `tests/test_ai_idempotency.py`

- [ ] **Step 1: Remove unittest dependency and main guard**

Remove:

```python
import unittest
```

and remove the bottom guard:

```python
if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Convert the class wrapper to pytest functions**

Use these exact test function names:

```python
def test_repeated_inspect_produces_stable_output() -> None:
def test_repeated_generate_plan_produces_stable_plan_after_stripping_expiry() -> None:
def test_replayed_dry_run_keeps_token_stable_within_same_plan() -> None:
```

- [ ] **Step 3: Replace assertion methods with native asserts**

Use direct forms such as:

```python
assert _strip_volatile(first) == _strip_volatile(second)
assert first["schema"] == "cleanmac.plan.v1"
assert token1
assert token1 == token2
```

- [ ] **Step 4: Run focused validation**

Run:

```bash
make ai-robustness-smoke
```

Expected: pytest reports the AI robustness target slice passed, including `tests/test_ai_idempotency.py`.

## Task 4: Update Pytest Governance Targets

**Files:**
- Modify: `Makefile`

- [ ] **Step 1: Add migrated contract/error files to AI robustness pytest targets**

Change:

```make
PYTEST_AI_ROBUSTNESS_TARGETS := tests/test_ai_versioning.py tests/test_mcp_protocol.py tests/test_ai_concurrency.py tests/test_ai_idempotency.py tests/test_ai_eval.py::AITracePersistenceTests
```

to:

```make
PYTEST_AI_ROBUSTNESS_TARGETS := tests/test_ai_versioning.py tests/test_mcp_protocol.py tests/test_ai_concurrency.py tests/test_ai_contract.py tests/test_ai_errors.py tests/test_ai_idempotency.py tests/test_ai_eval.py::AITracePersistenceTests
```

- [ ] **Step 2: Keep pytest-governance-smoke synchronized**

Update the inline `robustness_targets == [...]` assertion in `pytest-governance-smoke` to the same ordered list:

```python
[
    "tests/test_ai_versioning.py",
    "tests/test_mcp_protocol.py",
    "tests/test_ai_concurrency.py",
    "tests/test_ai_contract.py",
    "tests/test_ai_errors.py",
    "tests/test_ai_idempotency.py",
    "tests/test_ai_eval.py::AITracePersistenceTests",
]
```

- [ ] **Step 3: Run governance validation**

Run:

```bash
make pytest-governance-smoke
make ai-robustness-smoke
```

Expected: both Makefile targets pass.

## Task 5: Final Validation And Queue Hygiene

**Files:**
- Verify: `tests/test_ai_contract.py`
- Verify: `tests/test_ai_errors.py`
- Verify: `tests/test_ai_idempotency.py`
- Verify: `Makefile`
- Verify: `docs/superpowers/plans/2026-06-24-pytest-ai-contract-tests.md`

- [ ] **Step 1: Run focused combined pytest validation**

Run:

```bash
tmpdir=$(mktemp -d)
python3 -m venv "$tmpdir/venv"
"$tmpdir/venv/bin/python" -m pip install --upgrade pip
"$tmpdir/venv/bin/python" -m pip install -e '.[test]'
CLEANMAC_TEST_MODE=1 CLEANMAC_TEST_NO_AUTH=1 PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS="-p no:cacheprovider" "$tmpdir/venv/bin/python" -m pytest tests/test_ai_contract.py tests/test_ai_errors.py tests/test_ai_idempotency.py -q
rm -R "$tmpdir"
```

Expected: all selected migrated tests pass.

- [ ] **Step 2: Check git staging safety**

Run:

```bash
git status --short
```

Expected: source/test/plan changes are visible, `.harness/` remains ignored unless explicitly added by the user.

## Acceptance Criteria

- `tests/test_ai_contract.py`, `tests/test_ai_errors.py`, and `tests/test_ai_idempotency.py` no longer import `unittest`.
- The migrated tests are pytest-native function tests using `assert`.
- AI contract, error, and idempotency assertions remain behavior-equivalent to the previous unittest coverage.
- `PYTEST_AI_ROBUSTNESS_TARGETS` includes the migrated AI contract and AI error pytest files.
- `make pytest-governance-smoke` passes.
- `make ai-robustness-smoke` passes.
- `.harness/` runtime queue state is not committed.
