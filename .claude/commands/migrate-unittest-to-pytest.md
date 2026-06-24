---
name: migrate-unittest-to-pytest
description: Workflow command scaffold for migrate-unittest-to-pytest in cleanmac.
allowed_tools: ["Bash", "Read", "Write", "Grep", "Glob"]
---

# /migrate-unittest-to-pytest

Use this workflow when working on **migrate-unittest-to-pytest** in `cleanmac`.

## Goal

Migrates existing test suites from unittest.TestCase style to pytest-native functions, assertions, and fixtures, updating test files and wiring them into pytest targets and governance.

## Common Files

- `tests/test_*.py`
- `Makefile`
- `docs/superpowers/plans/2026-06-24-pytest-*.md`

## Suggested Sequence

1. Understand the current state and failure mode before editing.
2. Make the smallest coherent change that satisfies the workflow goal.
3. Run the most relevant verification for touched files.
4. Summarize what changed and what still needs review.

## Typical Commit Signals

- Identify target test modules using unittest.TestCase or similar wrappers.
- Refactor test files in tests/ to use pytest-native functions, assertions, and fixtures (e.g., tmp_path, pytest.raises, parametrize).
- Update Makefile to include migrated tests in relevant pytest targets (e.g., pytest-governance-smoke, ai-robustness-smoke, pytest-test).
- Add or update implementation/governance plan documents in docs/superpowers/plans/ to record the migration.
- Validate migration by running pytest targets and ensuring all tests pass.

## Notes

- Treat this as a scaffold, not a hard-coded script.
- Update the command if the workflow evolves materially.