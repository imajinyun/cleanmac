# Cleanmac Pytest AI Versioning Tests Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Continue the incremental pytest migration by converting the AI schema/versioning regression suite away from `unittest.TestCase` while preserving existing AI contract coverage.

**Architecture:** This is a test-only governance migration. `tests/test_ai_versioning.py` already participates in `PYTEST_AI_ROBUSTNESS_TARGETS`, so this round keeps the existing smoke wiring and changes only the test runner style unless validation exposes a Makefile drift. The migration preserves the current schema, contract validation, MCP resource, release evidence, and plan negotiation assertions.

**Tech Stack:** Python 3.10+, pytest, native `assert`, existing cleanmac AI versioning APIs, existing Makefile pytest smoke targets.

---

## File Structure

- Modify: `tests/test_ai_versioning.py`
  - Owns AI schema registry, core JSON schema fragment, AI Host critical schema validation, contract sample, and plan schema negotiation regressions.
- Verify: `Makefile`
  - Already lists `tests/test_ai_versioning.py` in `PYTEST_AI_ROBUSTNESS_TARGETS` and asserts that list in `pytest-governance-smoke`.

## Non-Goals

- Do not migrate `test_cleanmac.py`.
- Do not migrate `tests/test_mcp_server.py`.
- Do not migrate the broad `tests/test_ai_eval.py` suite in this round.
- Do not change production AI schema, AI Host, MCP, release, deletion, protection, or operation-log behavior.
- Do not commit `.harness/` runtime queue state.

## Task 1: Migrate AI Versioning Tests To Pytest Style

**Files:**
- Modify: `tests/test_ai_versioning.py`

- [ ] **Step 1: Remove unittest dependency**

Remove:

```python
import unittest
```

- [ ] **Step 2: Convert the test class to pytest collection**

Change:

```python
class AISchemaRegistryTests(unittest.TestCase):
```

to:

```python
class TestAISchemaRegistry:
```

This preserves the existing grouping without inheriting from `unittest.TestCase`.

- [ ] **Step 3: Replace assertion methods with native pytest assertions**

Use direct assertions such as:

```python
assert report["schema"] == "cleanmac.ai-schema-registry.v1"
assert report["entry_count"] >= 15
assert "cleanmac.ai-readiness.v1" in names
assert missing == [], f"Schemas missing from registry: {missing}"
assert validate_contract_payload("cleanmac.ai-host-policy.v1", host_policy)["valid"]
assert not missing_report["valid"]
```

- [ ] **Step 4: Remove the unittest main guard**

Remove:

```python
if __name__ == "__main__":
    unittest.main()
```

## Task 2: Verify Governance Wiring And Smoke Coverage

**Files:**
- Verify: `Makefile`
- Verify: `tests/test_ai_versioning.py`

- [ ] **Step 1: Confirm no unittest style remains in the migrated file**

Run:

```bash
python3 -m compileall -q tests/test_ai_versioning.py
rg -n "import unittest|unittest\\.TestCase|unittest\\.main|self\\.assert" tests/test_ai_versioning.py
```

Expected: compileall succeeds and `rg` returns no matches.

- [ ] **Step 2: Run the pytest governance smoke**

Run:

```bash
make pytest-governance-smoke
```

Expected: `pytest-governance-smoke passed`.

- [ ] **Step 3: Run the project pytest target through its managed temporary venv**

Run:

```bash
make pytest-test
```

Expected: pytest safe target slice passes.

- [ ] **Step 4: Run the AI robustness smoke**

Run:

```bash
make ai-robustness-smoke
```

Expected: pytest AI robustness target slice passes, including `tests/test_ai_versioning.py`.

## Expected Outcome

- `tests/test_ai_versioning.py` no longer imports or depends on `unittest`.
- The file is collected by pytest through `TestAISchemaRegistry`.
- Existing AI schema/versioning contract assertions remain behavior-equivalent.
- `PYTEST_AI_ROBUSTNESS_TARGETS` continues to expose `tests/test_ai_versioning.py`.
- `make pytest-governance-smoke`, `make pytest-test`, and `make ai-robustness-smoke` pass.
