---
name: update-pytest-governance-coverage
description: Workflow command scaffold for update-pytest-governance-coverage in cleanmac.
allowed_tools: ["Bash", "Read", "Write", "Grep", "Glob"]
---

# /update-pytest-governance-coverage

Use this workflow when working on **update-pytest-governance-coverage** in `cleanmac`.

## Goal

Expands or updates the set of tests covered by pytest governance by migrating additional test modules and updating Makefile targets and documentation.

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

- Migrate additional test modules from unittest to pytest-native style.
- Update Makefile pytest targets to include the new or migrated test files.
- Add corresponding governance or implementation plan markdown files under docs/superpowers/plans/.
- Validate by running updated pytest targets and confirming successful execution.

## Notes

- Treat this as a scaffold, not a hard-coded script.
- Update the command if the workflow evolves materially.