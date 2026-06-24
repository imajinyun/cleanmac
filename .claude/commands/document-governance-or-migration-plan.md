---
name: document-governance-or-migration-plan
description: Workflow command scaffold for document-governance-or-migration-plan in cleanmac.
allowed_tools: ["Bash", "Read", "Write", "Grep", "Glob"]
---

# /document-governance-or-migration-plan

Use this workflow when working on **document-governance-or-migration-plan** in `cleanmac`.

## Goal

Creates or updates markdown documentation under docs/superpowers/plans/ to record the details and governance of test migrations or coverage expansions.

## Common Files

- `docs/superpowers/plans/2026-06-24-pytest-*.md`

## Suggested Sequence

1. Understand the current state and failure mode before editing.
2. Make the smallest coherent change that satisfies the workflow goal.
3. Run the most relevant verification for touched files.
4. Summarize what changed and what still needs review.

## Typical Commit Signals

- Write a markdown plan document summarizing the migration or governance change.
- Add the markdown file to docs/superpowers/plans/ with a date-stamped filename.
- Reference the plan in the relevant commit message and ensure it matches the migrated/updated test files.

## Notes

- Treat this as a scaffold, not a hard-coded script.
- Update the command if the workflow evolves materially.