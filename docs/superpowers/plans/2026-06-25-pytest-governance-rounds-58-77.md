# Cleanmac Pytest Governance Rounds 58-77 Implementation Plan

> **For agentic workers:** Continue the pytest migration in small, committed rounds. Keep `test_cleanmac.py` runnable until each migrated slice has equivalent pytest-native coverage.

**Goal:** Move the next 20 stable governance and compatibility slices out of the large legacy unittest backlog into focused pytest tests, without changing production cleanup behavior.

**Architecture:** Each round adds or extends one `tests/test_*.py` file with pytest-native assertions, validates the touched slice with targeted pytest, ruff format/check, and `make pytest-test`, then commits independently. Use temporary-venv validation targets only.

**Non-goals:** Do not rewrite `test_cleanmac.py` wholesale. Do not add GUI, TUI, daemons, login items, background scanners, or resident processes. Do not change deletion primitives or execution policy unless a real defect is proven by tests.

---

## Step Status

- Step1 test preparation: completed with `BITS_TMP_ROOT=/var/folders/57/pqx08bk577x758hnslxkfhm40000gn/T/tmp.8481TDp3YT`.
- Step2 context: `LANG=python`; pytest-native function tests with project helpers and temporary-venv validation.
- Step3 scope: `non_diff`; migrate remaining `test_cleanmac.py` release, report, workflow, filter, import-boundary, and open-source governance slices.
- Step4 defect analysis: `BUG_MAP=[]`; this batch is equivalence and governance coverage unless a pytest exposes a real defect.
- Step5 execution: complete one round at a time with validation and commit.
- Step6 report: update this plan as rounds complete and keep the closeout backlog current.

---

## Round 58: Release Workflow Supply Chain Contract

**Files:**
- Modify: `tests/test_release_artifacts.py`

- [ ] Add pytest coverage for `.github/workflows/release.yml` permissions, SHA256/SBOM/readiness artifacts, release asset names, pinned upload/download/attestation/publish actions, and venv-backed release steps.
- [ ] Validate with targeted pytest, ruff format/check, and `make pytest-test`.
- [ ] Commit with `test(pytest): cover release workflow supply chain`.

## Round 59: Release Workflow Evidence Commands

**Files:**
- Modify: `tests/test_release_orchestration.py`

- [ ] Add pytest coverage that the release workflow invokes readiness, diagnostics, evidence, rehearsal, promotion decision, rollback, post-publish verification, post-publish result, post-publish evidence template, and release manifest generation commands.
- [ ] Validate with targeted pytest, ruff format/check, and `make pytest-test`.
- [ ] Commit with `test(pytest): cover release workflow evidence commands`.

## Round 60: Release Manifest Script Reuse

**Files:**
- Modify: `tests/test_release_artifacts.py`

- [ ] Add pytest coverage that `.github/workflows/release.yml` and `Makefile` reuse `scripts/generate_release_manifest.py` instead of duplicating manifest construction inline.
- [ ] Validate with targeted pytest, ruff format/check, and `make pytest-test`.
- [ ] Commit with `test(pytest): cover release manifest script reuse`.

## Round 61: README Audit Command Ordering

**Files:**
- Modify: `tests/test_cli_basics.py`

- [ ] Add pytest coverage that README audit examples keep global flags before grouped clean commands and still parse to the expected report-file contract.
- [ ] Validate with targeted pytest, ruff format/check, and `make pytest-test`.
- [ ] Commit with `test(pytest): cover readme audit command ordering`.

## Round 62: Report Renderer HTML Audit Files

**Files:**
- Modify: `tests/test_report_renderers.py`

- [ ] Add pytest coverage for HTML audit report emission, Finder links, selected-to-delete review sections, execution command copy, and report metadata.
- [ ] Validate with targeted pytest, ruff format/check, and `make pytest-test`.
- [ ] Commit with `test(pytest): cover html audit report files`.

## Round 63: Report Renderer Escaping And JSON Defaults

**Files:**
- Modify: `tests/test_report_renderers.py`

- [ ] Add pytest coverage for HTML escaping of unsafe audit content and default JSON audit report wrapper schema.
- [ ] Validate with targeted pytest, ruff format/check, and `make pytest-test`.
- [ ] Commit with `test(pytest): cover report escaping json defaults`.

## Round 64: Plan File Filter Replay

**Files:**
- Modify: `tests/test_clean_execution.py`

- [ ] Add pytest coverage that `--plan-file` reuses exclude patterns and age filters during execute without deleting filtered candidates.
- [ ] Validate with targeted pytest, ruff format/check, and `make pytest-test`.
- [ ] Commit with `test(pytest): cover plan file filter replay`.

## Round 65: Inspect Sorting And Budget Preview

**Files:**
- Modify: `tests/test_cli_basics.py`

- [ ] Add pytest coverage for inspect direct-child sorting, AI summary fields, recursive min-size filtering, path sort, and non-destructive budget previews.
- [ ] Validate with targeted pytest, ruff format/check, and `make pytest-test`.
- [ ] Commit with `test(pytest): cover inspect sorting budget preview`.

## Round 66: Filter And Active File Policies

**Files:**
- Modify: `tests/test_path_safety.py` or `tests/test_cli_basics.py`

- [ ] Add pytest coverage for invalid name-regex rejection, active incomplete download skips, mail download age/size defaults, GPU cache stale allowlist, and browser code-sign cache shard behavior.
- [ ] Validate with targeted pytest, ruff format/check, and `make pytest-test`.
- [ ] Commit with `test(pytest): cover filter active file policies`.

## Round 67: Inspect And Clean Filter Consistency

**Files:**
- Modify: `tests/test_clean_execution.py`

- [ ] Add pytest coverage that name regex and exclude filters behave consistently across inspect and clean, including skipped reason summaries.
- [ ] Validate with targeted pytest, ruff format/check, and `make pytest-test`.
- [ ] Commit with `test(pytest): cover inspect clean filter consistency`.

## Round 68: Risk Policy Execution Gates

**Files:**
- Modify: `tests/test_clean_execution.py`

- [ ] Add pytest coverage for high-risk `--yes` requirements, strict medium-risk blocking, permissive high-risk execution, live-root refusal, and pre-delete budget fail-closed checks.
- [ ] Validate with targeted pytest, ruff format/check, and `make pytest-test`.
- [ ] Commit with `test(pytest): cover risk policy execution gates`.

## Round 69: Public Module Import Boundary

**Files:**
- Modify: `tests/test_makefile_governance.py` or create `tests/test_public_imports.py`

- [x] Add pytest coverage that public `cleancli` modules import after package splitting and `cleanmac.main` still delegates to `cleancli.cli.main`.
- [x] Validate with targeted pytest, ruff format/check, and `make pytest-test`.
- [x] Commit with `test(pytest): cover public module import boundary`.

## Round 70: Grouped Command Matrix Smoke

**Files:**
- Modify: `tests/test_cli_workflows.py`

- [x] Add pytest coverage for the grouped command matrix smoke remaining non-destructive across clean, analyze, software, privacy, startup, status, optimize, links, and workflow routes.
- [x] Validate with targeted pytest, ruff format/check, and `make pytest-test`.
- [x] Commit with `test(pytest): cover grouped command matrix smoke`.

## Round 71: Explain And Diagnose Routes

**Files:**
- Modify: `tests/test_cli_workflows.py`

- [x] Add pytest coverage for `explain` summarizing plans without execution and `diagnose` recommending safe categories while flagging logs.
- [x] Validate with targeted pytest, ruff format/check, and `make pytest-test`.
- [x] Commit with `test(pytest): cover explain diagnose routes`.

## Round 72: AI Workflow Route Contract

**Files:**
- Modify: `tests/test_ai_runbook.py` or `tests/test_cli_workflows.py`

- [x] Add pytest coverage for `ai-workflow` one-shot governed cleanup route, validation schema, review-selection gate, trash execution, and single-shot workflow lifecycle fields.
- [x] Validate with targeted pytest, ruff format/check, and `make pytest-test`.
- [x] Commit with `test(pytest): cover ai workflow route contract`.

## Round 73: Workflow Selected Dry-Run Scope

**Files:**
- Modify: `tests/test_cli_workflows.py`

- [ ] Add pytest coverage that selected dry-run workflows can include high-risk categories without execute behavior.
- [ ] Validate with targeted pytest, ruff format/check, and `make pytest-test`.
- [ ] Commit with `test(pytest): cover workflow selected dry-run scope`.

## Round 74: Core AI Dispatches In Process

**Files:**
- Modify: `tests/test_ai_contract.py` or `tests/test_cli_workflows.py`

- [ ] Add pytest coverage for in-process `cleancli.core.main` AI/release dispatches and schema outputs without spawning external processes.
- [ ] Validate with targeted pytest, ruff format/check, and `make pytest-test`.
- [ ] Commit with `test(pytest): cover core ai dispatches`.

## Round 75: Contract Validation Failure Reporting

**Files:**
- Modify: `tests/test_ai_contract.py` or `tests/test_cli_workflows.py`

- [ ] Add pytest coverage that core contract validation reports file failures in-process with structured errors.
- [ ] Validate with targeted pytest, ruff format/check, and `make pytest-test`.
- [ ] Commit with `test(pytest): cover contract validation failures`.

## Round 76: Open Source Governance Files

**Files:**
- Modify: `tests/test_open_source_governance.py` or `tests/test_makefile_governance.py`

- [ ] Add pytest coverage for required governance files, pinned GitHub Actions, security/dependency/scorecard workflows, README/AGENTS AI-first zero-resident positioning, and packaging metadata.
- [ ] Validate with targeted pytest, ruff format/check, and `make pytest-test`.
- [ ] Commit with `test(pytest): cover open source governance files`.

## Round 77: Removed Product Reference Ratchet

**Files:**
- Modify: `tests/test_open_source_governance.py` or `tests/test_makefile_governance.py`
- Modify: `docs/superpowers/plans/2026-06-25-pytest-governance-cycle-closeout.md`

- [ ] Add pytest coverage that scanned project files do not contain removed product references or local developer paths.
- [ ] Update the closeout document with Round 58-77 status and the next backlog slices.
- [ ] Validate with targeted pytest, ruff format/check, and `make pytest-test`.
- [ ] Commit with `test(pytest): ratchet removed product references`.

---

## Acceptance Criteria

- Twenty aiflow tasks are submitted with IDs `cleanmac-pytest-governance-round-58-*` through `cleanmac-pytest-governance-round-77-*`.
- Each completed round has one focused commit.
- Every round runs targeted pytest, ruff format/check, and `make pytest-test`.
- No production code is changed unless a pytest exposes a real defect.
- `.harness/store.json`, caches, temporary venvs, coverage files, and runtime state are not committed.
