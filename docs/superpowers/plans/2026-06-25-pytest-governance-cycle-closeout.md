# Cleanmac Pytest Governance Cycle Closeout

**Goal:** Close the current pytest governance cycle with a machine-checkable summary of migrated pytest surfaces, validation gates, and the remaining unittest migration backlog.

**Status:** Active pytest governance rounds have moved the release, deletion-safety, security, AI Host, AI robustness, Makefile, CI, macOS smoke, bundle audit, plan replay, confirmation-token, and AI eval surfaces behind pytest-native tests and explicit Makefile target groups.

---

## Round 38-57 Closeout

- Plan: `2026-06-25-pytest-governance-next-20-rounds.md`.
- Round 38-57 status: all planned pytest governance rounds are completed and each round has a focused commit.
- Newly ratcheted pytest surfaces include `tests/test_cli_basics.py`, `tests/test_ai_contract.py`, `tests/test_ai_schema_exports.py`, `tests/test_ai_idempotency.py`, `tests/test_cli_workflows.py`, `tests/test_clean_execution.py`, `tests/test_app_protection.py`, `tests/test_group_containers.py`, `tests/test_software_governance.py`, `tests/test_startup_governance.py`, `tests/test_privacy_governance.py`, and `tests/test_makefile_governance.py`.
- Round 57 adds the migration backlog ratchet: only `test_cleanmac.py` may remain as the intentional large unittest backlog, while `tests/test_makefile_governance.py` may contain unittest tokens only as literal forbidden-token fixtures.

## Round 58-77 Closeout

- Plan: `2026-06-25-pytest-governance-rounds-58-77.md`.
- Round 58-77 status: all planned pytest governance rounds are completed and each round has a focused commit.
- Newly ratcheted pytest surfaces include `tests/test_release_artifacts.py`, `tests/test_release_orchestration.py`, `tests/test_report_renderers.py`, `tests/test_public_imports.py`, `tests/test_core_dispatch.py`, `tests/test_open_source_governance.py`, plus expanded coverage in `tests/test_cli_basics.py`, `tests/test_cli_workflows.py`, `tests/test_clean_execution.py`, and `tests/test_ai_host_scenarios.py`.
- Release governance now has pytest coverage for supply-chain workflow contracts, release evidence commands, release manifest script reuse, and release readiness dispatch through `cleancli.core.main`.
- CLI governance now has pytest coverage for README audit command ordering, grouped command non-destructive smoke behavior, explain and diagnose routes, workflow selected dry-run scope, public module import boundaries, and removed product reference ratchets.
- AI Host governance now has pytest coverage for the one-shot AI workflow route contract, candidate evidence chain, review-selection evidence, dry-run token output, Trash execution gate, operation-log evidence requirements, and in-process AI/release dispatch schema coverage.
- Open-source governance now has pytest coverage for required governance files, pinned GitHub Actions references, security/dependency/scorecard workflow configuration, README/AGENTS AI-first zero-resident positioning, packaging metadata, and local developer path exclusion.

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

- `test_cleanmac.py` is the only intentional large unittest backlog. It still owns broad legacy CLI compatibility, safety guardrail contracts, governance metadata contracts, human-renderer branch coverage, and remaining edge-case compatibility checks.
- Do not migrate `test_cleanmac.py` as one large rewrite. Split it by stable ownership boundaries first, then move each extracted slice to pytest.
- Recommended next slices:
  - capabilities and governance metadata contracts
  - CLI plan / dry-run / execute orchestration contracts
  - delete safety and Trash execution compatibility cases not already covered in `tests/test_delete_ops.py` or `tests/test_trash_mode.py`
  - release workflow and distribution governance checks that are not already covered by release workflow and artifact pytest files
  - grouped command compatibility and legacy flat-command compatibility checks that are not already covered by grouped command pytest files
  - remaining distribution governance checks not covered by release workflow and artifact pytest files
  - legacy flat-command compatibility checks not already covered by grouped command pytest files
  - human report printer branches and remaining report renderer compatibility checks
  - in-process human output rendering branches in `cleancli.core.print_report`
- `tests/test_makefile_governance.py` intentionally contains `import unittest`, `unittest.TestCase`, `unittest.main`, and `self.assert` as literal forbidden-token fixtures. It is not part of the unittest backlog.

## Next backlog slices

1. Extract capabilities and governance metadata contracts from `test_cleanmac.py` into pytest coverage for runtime lifecycle, product positioning, boundary governance, development governance TODOs, and AI tool contract metadata.
2. Extract CLI plan / dry-run / execute orchestration edge cases into pytest coverage for plan context, review-selection constraints, confirmation-token propagation, and operation-log summaries.
3. Extract human report printer branches into pytest coverage for `cleancli.core.print_report` and plain-text fallbacks without relying on subprocess output.
4. Extract remaining distribution governance checks into pytest coverage for Homebrew formula metadata, package smoke invariants, and post-publish evidence contracts.
5. Extract legacy flat-command compatibility checks into pytest coverage for aliases that remain supported alongside grouped commands.
6. Keep `test_cleanmac.py` runnable until each extracted slice has equivalent pytest coverage and at least one targeted pytest plus `make pytest-test` evidence.

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
