# Cleanmac Pytest AI Policy Protocol Tests Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve the remaining small AI governance unittest files by migrating policy, MCP protocol, and AI concurrency tests to pytest-native style without weakening existing smoke gates.

**Architecture:** This is a test-only modernization. The selected files are already part of, or safe to add to, the pytest AI robustness target set and are not directly invoked by the legacy `ai-host-smoke` unittest module list. The migration preserves current CLI/MCP subprocess coverage, removes `unittest.TestCase` wrappers, and keeps Makefile pytest governance synchronized.

**Tech Stack:** Python 3.10+, pytest, native `assert`, temporary venv-backed Makefile pytest targets, existing cleanmac CLI/MCP helpers.

---

## File Structure

- Modify: `tests/test_ai_policy.py`
  - Owns plan policy, prompt-injection policy, and LLM invocation guide re-export tests.
- Modify: `tests/test_mcp_protocol.py`
  - Owns MCP JSON-RPC protocol hardening tests for invalid requests, timeout behavior, and resource payload treatment.
- Modify: `tests/test_ai_concurrency.py`
  - Owns concurrent CLI and MCP call regression tests.
- Modify: `Makefile`
  - Adds `tests/test_ai_policy.py` to `PYTEST_AI_ROBUSTNESS_TARGETS` and updates `pytest-governance-smoke` expectations.

## Non-Goals

- Do not migrate broad legacy `test_cleanmac.py`.
- Do not migrate tests that are still directly invoked through `python -m unittest` smoke lists in this phase.
- Do not change production CLI, MCP, deletion, protection, AI Host, or release behavior.
- Do not add GUI, TUI, daemon, login item, background scan, or resident-process behavior.
- Do not commit `.harness/` runtime queue state.

## Task 1: Migrate AI Policy Tests To Pytest Style

**Files:**
- Modify: `tests/test_ai_policy.py`

- [ ] **Step 1: Remove unittest import and class wrapper**

Replace:

```python
import unittest

class AIPolicyTests(unittest.TestCase):
    def test_plan_policy_is_owned_outside_core_and_reexported(self) -> None:
```

with:

```python
def test_plan_policy_is_owned_outside_core_and_reexported() -> None:
```

Repeat for:

```python
def test_prompt_injection_policy_treats_paths_as_untrusted_data() -> None:
def test_llm_invocation_guide_preserves_execute_gates_and_runtime_policy() -> None:
```

- [ ] **Step 2: Replace unittest assertions with native asserts**

Use direct forms:

```python
assert policy == render_core_plan_policy()
assert policy["schema"] == "cleanmac.plan-policy.v1"
assert policy["max_age_seconds"] == 30 * 60
assert "cleanmac_policy_simulate" in policy["required_before_execute"]
assert execute_conditions["operation_log_explicit"] is True
```

- [ ] **Step 3: Run focused validation**

Run:

```bash
tmpdir=$(mktemp -d)
python3 -m venv "$tmpdir/venv"
"$tmpdir/venv/bin/python" -m pip install --upgrade pip
"$tmpdir/venv/bin/python" -m pip install -e '.[test]'
CLEANMAC_TEST_MODE=1 CLEANMAC_TEST_NO_AUTH=1 PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS="-p no:cacheprovider" "$tmpdir/venv/bin/python" -m pytest tests/test_ai_policy.py -q
rm -R "$tmpdir"
```

Expected: all `tests/test_ai_policy.py` tests pass.

## Task 2: Migrate MCP Protocol Tests To Pytest Style

**Files:**
- Modify: `tests/test_mcp_protocol.py`

- [ ] **Step 1: Remove unittest import and class wrapper**

Remove:

```python
import unittest
```

Convert the class methods into module-level pytest functions:

```python
def test_request_without_jsonrpc_field_returns_invalid_request() -> None:
def test_request_with_wrong_jsonrpc_version_returns_invalid_request() -> None:
def test_tool_call_respects_injected_timeout(tmp_path: Path) -> None:
def test_resource_payload_is_returned_as_data_not_instruction() -> None:
```

- [ ] **Step 2: Replace `tempfile.TemporaryDirectory()` with `tmp_path`**

For the timeout test, replace:

```python
with tempfile.TemporaryDirectory() as tmp:
    sleeper = Path(tmp) / "sleepy_cleanmac.py"
```

with:

```python
sleeper = tmp_path / "sleepy_cleanmac.py"
```

- [ ] **Step 3: Replace assertions**

Use direct forms:

```python
assert response["error"]["code"] == -32600
assert "jsonrpc" in response["error"]["message"].lower()
assert result["isError"] is True
assert result["structuredContent"]["schema"] == "cleanmac.mcp-tool-error.v1"
assert payload["execution_gate"]["auto_call_allowed"] is False
```

- [ ] **Step 4: Run focused validation**

Run:

```bash
tmpdir=$(mktemp -d)
python3 -m venv "$tmpdir/venv"
"$tmpdir/venv/bin/python" -m pip install --upgrade pip
"$tmpdir/venv/bin/python" -m pip install -e '.[test]'
CLEANMAC_TEST_MODE=1 CLEANMAC_TEST_NO_AUTH=1 PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS="-p no:cacheprovider" "$tmpdir/venv/bin/python" -m pytest tests/test_mcp_protocol.py -q
rm -R "$tmpdir"
```

Expected: all MCP protocol tests pass.

## Task 3: Migrate AI Concurrency Tests To Pytest Style

**Files:**
- Modify: `tests/test_ai_concurrency.py`

- [ ] **Step 1: Remove unittest import and class wrapper**

Remove:

```python
import unittest
```

Convert the class methods into module-level pytest functions:

```python
def test_concurrent_capabilities_calls_are_deterministic() -> None:
def test_concurrent_mcp_tool_calls_do_not_cross_pollute() -> None:
```

- [ ] **Step 2: Replace assertion methods**

Use direct forms:

```python
assert errors == []
assert len(results) == 8
assert {result["schema"] for result in results} == {"cleanmac.capabilities.v1"}
assert response["result"]["isError"] is False, response
assert "structuredContent" in response["result"]
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
make ai-robustness-smoke
```

Expected: the AI robustness pytest target set passes, including `tests/test_ai_concurrency.py`.

## Task 4: Update Pytest AI Robustness Governance

**Files:**
- Modify: `Makefile`

- [ ] **Step 1: Add AI policy tests to pytest AI robustness targets**

Change:

```make
PYTEST_AI_ROBUSTNESS_TARGETS := tests/test_ai_versioning.py tests/test_mcp_protocol.py tests/test_ai_concurrency.py tests/test_ai_contract.py tests/test_ai_errors.py tests/test_ai_idempotency.py tests/test_ai_eval.py::AITracePersistenceTests
```

to:

```make
PYTEST_AI_ROBUSTNESS_TARGETS := tests/test_ai_versioning.py tests/test_mcp_protocol.py tests/test_ai_concurrency.py tests/test_ai_policy.py tests/test_ai_contract.py tests/test_ai_errors.py tests/test_ai_idempotency.py tests/test_ai_eval.py::AITracePersistenceTests
```

- [ ] **Step 2: Update `pytest-governance-smoke` target list assertion**

Update `expected_robustness` to the same ordered list:

```python
[
    "tests/test_ai_versioning.py",
    "tests/test_mcp_protocol.py",
    "tests/test_ai_concurrency.py",
    "tests/test_ai_policy.py",
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

Expected: both targets pass.

## Task 5: Final Validation And Queue Hygiene

**Files:**
- Verify: `tests/test_ai_policy.py`
- Verify: `tests/test_mcp_protocol.py`
- Verify: `tests/test_ai_concurrency.py`
- Verify: `Makefile`
- Verify: `docs/superpowers/plans/2026-06-24-pytest-ai-policy-protocol-tests.md`

- [ ] **Step 1: Confirm migrated files no longer use unittest**

Run:

```bash
rg -n "unittest|self\\.assert|unittest\\.main" tests/test_ai_policy.py tests/test_mcp_protocol.py tests/test_ai_concurrency.py
```

Expected: no matches.

- [ ] **Step 2: Confirm the old release pytest gate still passes**

Run:

```bash
make pytest-test
```

Expected: release pytest parity tests pass unchanged.

- [ ] **Step 3: Check git and ignored runtime safety**

Run:

```bash
git status --short --ignored
```

Expected: source/test/plan changes are visible, `.harness/` remains ignored, and no cache or venv artifacts are staged.

## Acceptance Criteria

- `tests/test_ai_policy.py`, `tests/test_mcp_protocol.py`, and `tests/test_ai_concurrency.py` no longer import `unittest`.
- Migrated tests use pytest-native function tests and `assert`.
- `tests/test_mcp_protocol.py` uses `tmp_path` instead of `tempfile.TemporaryDirectory()`.
- `PYTEST_AI_ROBUSTNESS_TARGETS` includes `tests/test_ai_policy.py`.
- `make pytest-governance-smoke` passes.
- `make ai-robustness-smoke` passes.
- `make pytest-test` passes.
- `.harness/` runtime queue state is not committed.
