# Cleanmac Pytest Governance Cycle Closeout

**Goal:** Close the current pytest governance cycle with a machine-checkable summary of migrated pytest surfaces, validation gates, and the remaining unittest migration backlog.

**Status:** Active pytest governance rounds have moved the release, deletion-safety, security, AI Host, AI robustness, Makefile, CI, macOS smoke, bundle audit, plan replay, confirmation-token, and AI eval surfaces behind pytest-native tests and explicit Makefile target groups.

---

## Landed Pytest Governance Surfaces

- `PYTEST_SAFE_TARGETS` covers release readiness, release orchestration, release artifacts, path safety, Trash mode, delete ops, and security scan pytest files.
- `PYTEST_AI_HOST_TARGETS` covers AI runbook, host policy, self-test, decision matrix, governance, host evidence, readiness, host scenarios, AI eval, and MCP server pytest files.
- `PYTEST_AI_ROBUSTNESS_TARGETS` covers AI versioning, MCP protocol, concurrency, policy, host integration, contracts, errors, idempotency, runbook, host policy, self-test, decision matrix, governance, host evidence, readiness, and trace persistence pytest files.
- `make pytest-test` remains the standard compatibility gate and must continue to create an isolated temporary venv before running pytest.
- `make pytest-governance-smoke` remains the policy gate for explicit pytest target lists and no broad `pytest tests -q` fallback.
- `make ai-host-smoke` and `make ai-robustness-smoke` remain the higher-level AI Host and AI robustness pytest gates.

---

## Remaining Unittest Migration Backlog

- `test_cleanmac.py` is the only intentional large unittest backlog. It still owns broad legacy CLI compatibility, grouped-command compatibility, safety guardrail contracts, governance metadata contracts, and release workflow regression checks.
- Do not migrate `test_cleanmac.py` as one large rewrite. Split it by stable ownership boundaries first, then move each extracted slice to pytest.
- Recommended next slices:
  - capabilities and governance metadata contracts
  - CLI plan / dry-run / execute orchestration contracts
  - delete safety and Trash execution compatibility cases not already covered in `tests/test_delete_ops.py` or `tests/test_trash_mode.py`
  - open-source, release workflow, and distribution governance checks
- `tests/test_makefile_governance.py` intentionally contains `import unittest`, `unittest.TestCase`, `unittest.main`, and `self.assert` as literal forbidden-token fixtures. It is not part of the unittest backlog.

---

## Required Validation

Run these before considering the cycle closed:

```bash
make pytest-test
make pytest-governance-smoke
make ai-robustness-smoke
```

When changing tooling or CI gates, also run:

```bash
make quality-check
```

All validation must use project-provided temporary venv targets or `.venv/bin/python`; do not rely on globally installed pytest, ruff, or mypy.

---

## Non-Goals

- Do not change production cleanup behavior as part of pytest migration.
- Do not expand cleanup execution privileges.
- Do not add GUI, TUI, daemon, login item, background scanner, or resident-process behavior.
- Do not commit `.harness/store.json`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `.coverage`, `.venv`, or temporary validation output.
