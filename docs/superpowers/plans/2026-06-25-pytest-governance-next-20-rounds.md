# Cleanmac Pytest Governance Next 20 Rounds Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Continue migrating the large `test_cleanmac.py` unittest backlog into focused pytest-native governance tests without a big-bang rewrite.

**Architecture:** Each round extracts or mirrors one stable behavior slice into an existing or new `tests/test_*.py` file, validates it with targeted pytest, ruff, and `make pytest-test`, then commits independently. Production cleanup behavior, deletion primitives, AI Host contracts, MCP contracts, and release gates remain unchanged.

**Tech Stack:** Python 3.10+, pytest, native `assert`, `pytest.raises`, `tmp_path`, existing `tests.helpers`, Makefile temporary-venv targets, aiflow queue tasks.

---

## File Structure

- Modify: `tests/test_cli_basics.py` for capabilities, command grouping, unknown command/category, profiles, links, and report-file CLI basics.
- Modify: `tests/test_cli_workflows.py` for analyze/status/optimize/workflow grouped command behavior.
- Modify: `tests/test_clean_execution.py` for dry-run, execute, budget, report, and post-clean contracts still concentrated in `test_cleanmac.py`.
- Modify: `tests/test_delete_ops.py`, `tests/test_trash_mode.py`, and `tests/test_path_safety.py` for deletion and safety leftovers.
- Modify: `tests/test_software_governance.py`, `tests/test_startup_governance.py`, and `tests/test_privacy_governance.py` for governed execution leftovers.
- Modify: `tests/test_review_selection.py`, `tests/test_operation_log.py`, and `tests/test_report_renderers.py` for review/evidence/report leftovers.
- Modify: `tests/test_makefile_governance.py` for migration governance and backlog tracking.
- Create only when a slice has no clear home; prefer existing focused files.
- Do not modify production code unless a pytest reveals a real defect and the fix is narrowly scoped.

---

## Round 38: Capabilities Boundary Metadata

**Files:**
- Modify: `tests/test_cli_basics.py`

- [x] Add pytest coverage for `cleanmac --json capabilities` command groups, preferred grouped command style, AI eval pack summary, AI governance advice summary, and AI Host policy denial list.
- [x] Verify with `CLEANMAC_TEST_MODE=1 CLEANMAC_TEST_NO_AUTH=1 PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS="-p no:cacheprovider" .venv/bin/python -m pytest tests/test_cli_basics.py -q`.
- [x] Run ruff format/check for the touched file.
- [x] Run `make pytest-test`.
- [x] Commit with `test(pytest): cover capabilities boundary metadata`.

## Round 39: Runtime Lifecycle And Product Boundary

**Files:**
- Modify: `tests/test_cli_basics.py`

- [x] Add pytest coverage for zero-resident runtime lifecycle fields, forbidden GUI/TUI/daemon/login-item/background-scan surfaces, product positioning, and GEO discoverability policy.
- [x] Validate with targeted pytest, ruff, and `make pytest-test`.
- [x] Commit with `test(pytest): cover runtime lifecycle boundaries`.

## Round 40: Development Governance TODO Integrity

**Files:**
- Modify: `tests/test_cli_basics.py` or `tests/test_makefile_governance.py`

- [x] Add pytest coverage that `development_governance_todo` is ordered, 25/25 landed, release gated, mirrored under safety guardrails, and exposes the expected first/last IDs.
- [x] Validate with targeted pytest, ruff, and `make pytest-test`.
- [x] Commit with `test(pytest): cover development governance todo integrity`.

## Round 41: Open Source Gap Governance TODO

**Files:**
- Modify: `tests/test_cli_basics.py`

- [x] Add pytest coverage for `open_source_gap_governance_todo` ordering, P0 priorities, non-goals, and first software-leftover IDs.
- [x] Validate with targeted pytest, ruff, and `make pytest-test`.
- [x] Commit with `test(pytest): cover open source gap governance todo`.

## Round 42: Governance Integrity Contract

**Files:**
- Modify: `tests/test_cli_basics.py` or `tests/test_ai_governance.py`

- [x] Add pytest coverage for `governance_integrity` readiness, readiness score, governed contracts, required release gate commands, and remediation commands.
- [x] Validate with targeted pytest, ruff, and `make pytest-test`.
- [x] Commit with `test(pytest): cover governance integrity contract`.

## Round 43: Distribution Governance Metadata

**Files:**
- Modify: `tests/test_cli_basics.py` or `tests/test_release_artifacts.py`

- [x] Add pytest coverage for distribution governance artifact types, Homebrew tap policy, release manifest path, and privileged command ownership scan command.
- [x] Validate with targeted pytest, ruff, and `make pytest-test`.
- [x] Commit with `test(pytest): cover distribution governance metadata`.

## Round 44: AI Tool Contract From Capabilities

**Files:**
- Modify: `tests/test_ai_contract.py`

- [x] Add pytest coverage for `ai_tool_contract` default invocation, discoverability hints, one-shot interaction model, auto-call/confirmation rules, forbidden commands, and execution requirements.
- [x] Validate with targeted pytest, ruff, and `make pytest-test`.
- [x] Commit with `test(pytest): cover capabilities ai tool contract`.

## Round 45: AI Workflow And Intent Hints

**Files:**
- Modify: `tests/test_ai_runbook.py` or `tests/test_cli_workflows.py`

- [x] Add pytest coverage for `ai_recommended_workflow` discover/plan/dry-run/confirm/execute contracts and `ai_intent_hints` for developer, browser, and Xcode cleanup categories.
- [x] Validate with targeted pytest, ruff, and `make pytest-test`.
- [x] Commit with `test(pytest): cover ai workflow intent hints`.

## Round 46: Provider Export And MCP Catalog Parity

**Files:**
- Modify: `tests/test_ai_schema_exports.py`

- [ ] Add pytest coverage comparing `ai_function_schemas`, OpenAI function exports, Anthropic tool exports, MCP catalog names, argv-only invocation, and schema validation summary.
- [ ] Validate with targeted pytest, ruff, and `make pytest-test`.
- [ ] Commit with `test(pytest): cover provider export mcp parity`.

## Round 47: Confirmation Summary Contracts

**Files:**
- Modify: `tests/test_ai_idempotency.py` or `tests/test_clean_execution.py`

- [ ] Add pytest coverage for dry-run and execute confirmation summary fields, token context, Trash delete mode, budget fields, and execute result counts.
- [ ] Validate with targeted pytest, ruff, and `make pytest-test`.
- [ ] Commit with `test(pytest): cover confirmation summary contracts`.

## Round 48: Confirmation Token Boundary Conditions

**Files:**
- Modify: `tests/test_ai_idempotency.py`

- [ ] Add pytest coverage for token generation inputs and mismatches across categories, root/home, delete mode, max delete MB, and selected plan content.
- [ ] Validate with targeted pytest, ruff, and `make pytest-test`.
- [ ] Commit with `test(pytest): cover confirmation token boundaries`.

## Round 49: Grouped Command Compatibility

**Files:**
- Modify: `tests/test_cli_basics.py`

- [ ] Add pytest coverage that grouped clean commands match flat aliases, grouped clean run remains dry-run by default, grouped analyze tree reports largest entries, and non-CLI grouped analyze actions are rejected.
- [ ] Validate with targeted pytest, ruff, and `make pytest-test`.
- [ ] Commit with `test(pytest): cover grouped command compatibility`.

## Round 50: Analyze Tree Report Files

**Files:**
- Modify: `tests/test_cli_workflows.py` or `tests/test_report_renderers.py`

- [ ] Add pytest coverage for analyze tree Markdown report output, file links, sandbox root behavior, and JSON schema fields.
- [ ] Validate with targeted pytest, ruff, and `make pytest-test`.
- [ ] Commit with `test(pytest): cover analyze tree report files`.

## Round 51: Profiles And Links Commands

**Files:**
- Modify: `tests/test_cli_basics.py`

- [ ] Add pytest coverage for profile expansion defaults, safe budgets, links report mappings, link execute/create/remove behavior, and non-symlink skip handling.
- [ ] Validate with targeted pytest, ruff, and `make pytest-test`.
- [ ] Commit with `test(pytest): cover profiles and links commands`.

## Round 52: Clean Dry-Run And Pre/Post Reports

**Files:**
- Modify: `tests/test_clean_execution.py`

- [ ] Add pytest coverage for clean default dry-run, pre-clean report, symbolic-link refresh note, execute post-clean report, and human output pre/post summaries.
- [ ] Validate with targeted pytest, ruff, and `make pytest-test`.
- [ ] Commit with `test(pytest): cover clean dry-run reports`.

## Round 53: Clean Execute Sandbox And Audit Reports

**Files:**
- Modify: `tests/test_clean_execution.py`

- [ ] Add pytest coverage for execute removing only sandbox contents, JSON audit report file output, item failure continuation, and operation log visibility.
- [ ] Validate with targeted pytest, ruff, and `make pytest-test`.
- [ ] Commit with `test(pytest): cover clean execute audit reports`.

## Round 54: App And Group Container Cleanup Policies

**Files:**
- Modify: `tests/test_app_protection.py` or `tests/test_group_containers.py`

- [ ] Add pytest coverage for bundle blocklist, bundle allowlist, protected app container skip, group container Apple skip, developer tool cache rules, browser/collaboration/package cache rules, and credential preservation.
- [ ] Validate with targeted pytest, ruff, and `make pytest-test`.
- [ ] Commit with `test(pytest): cover app container cleanup policies`.

## Round 55: Software Uninstall Execution Evidence

**Files:**
- Modify: `tests/test_software_governance.py`

- [ ] Add pytest coverage for uninstall plan official uninstaller routing, orphan leftovers, protected system bundle skip, review-selection-required execute path, Trash routing, and operation-log evidence.
- [ ] Validate with targeted pytest, ruff, and `make pytest-test`.
- [ ] Commit with `test(pytest): cover software uninstall evidence`.

## Round 56: Startup And Privacy Execute Evidence

**Files:**
- Modify: `tests/test_startup_governance.py` and `tests/test_privacy_governance.py`

- [ ] Add pytest coverage for startup backup metadata, privacy sensitive-scope preservation, selected item/path matching, unsafe candidate blocking, Trash routing, and candidate review evidence.
- [ ] Validate with targeted pytest, ruff, and `make pytest-test`.
- [ ] Commit with `test(pytest): cover governed startup privacy evidence`.

## Round 57: Migration Backlog Ratchet

**Files:**
- Modify: `tests/test_makefile_governance.py`
- Modify: `docs/superpowers/plans/2026-06-25-pytest-governance-cycle-closeout.md`

- [ ] Add a pytest ratchet that records the allowed `test_cleanmac.py` unittest backlog and fails if new `unittest.TestCase`, `self.assert`, or `unittest.main` usage appears outside explicitly documented exceptions.
- [ ] Update the closeout document with the new Round 38-57 plan link and next backlog slices.
- [ ] Validate with targeted pytest, ruff, and `make pytest-test`.
- [ ] Commit with `test(pytest): ratchet unittest migration backlog`.

---

## Acceptance Criteria

- Twenty aiflow tasks are submitted with IDs `cleanmac-pytest-governance-round-38-*` through `cleanmac-pytest-governance-round-57-*`.
- Each completed round has one focused commit.
- Every round runs targeted pytest, ruff format/check, and `make pytest-test`.
- No production code is changed unless a pytest exposes a real defect.
- `.harness/store.json`, caches, temporary venvs, coverage files, and runtime state are not committed.
