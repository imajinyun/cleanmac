# Cleanmac Pytest Governance Rounds 98-117 Implementation Plan

> Continue migrating stable legacy `unittest` slices into focused pytest-native coverage. Keep `test_cleanmac.py` runnable until each extracted slice has equivalent pytest coverage.

**Goal:** Move the next 20 review, startup/privacy, plan, inspect, filter, risk-gate, and report-renderer governance slices out of the legacy unittest backlog into pytest tests.

**Architecture:** Each round extends one existing `tests/test_*.py` surface where possible. Validate each slice with targeted pytest, ruff format/check for touched Python files, and `make pytest-test`, then commit independently.

**Non-goals:** Do not rewrite `test_cleanmac.py` wholesale. Do not change production cleanup behavior. Do not add GUI, TUI, daemon, login item, background scanner, resident process, or new destructive pathway.

---

## Step Status

- Step1 test preparation: completed with `BITS_TMP_ROOT=/var/folders/57/pqx08bk577x758hnslxkfhm40000gn/T/tmp.m0VSg0FlcN`.
- Step2 context: `LANG=python`; pytest-native function tests, project helpers, temporary-venv validation, and cleanmac AGENTS.md safety rules.
- Step3 scope: `non_diff`; migrate remaining stable slices from `test_cleanmac.py` into pytest files under `tests/`.
- Step4 defect analysis: `BUG_MAP=[]`; this batch is equivalence and governance coverage unless a pytest exposes a real defect.
- Step5 execution: complete one round at a time with validation and commit.
- Step6 report: update this plan and cycle closeout as rounds complete.

---

## TARGETS

```json
[
  {
    "file_path": "test_cleanmac.py",
    "target_type": "method",
    "symbol": "CleanMacCLITests.test_review_html_includes_selection_summary_and_selected_state",
    "locator": "test_cleanmac.py:2801",
    "source": "test_entry",
    "reason": "Extract review HTML selection summary and selected/excluded display-state coverage.",
    "hunks": []
  },
  {
    "file_path": "test_cleanmac.py",
    "target_type": "method",
    "symbol": "CleanMacCLITests.test_review_supports_startup_and_privacy_plans",
    "locator": "test_cleanmac.py:2846",
    "source": "test_entry",
    "reason": "Ratchet review normalization and candidate evidence for startup/privacy plans.",
    "hunks": []
  },
  {
    "file_path": "test_cleanmac.py",
    "target_type": "method",
    "symbol": "CleanMacCLITests.test_review_synthesizes_candidate_evidence_for_clean_reports",
    "locator": "test_cleanmac.py:2909",
    "source": "test_entry",
    "reason": "Extract clean report review evidence synthesis into pytest coverage.",
    "hunks": []
  },
  {
    "file_path": "test_cleanmac.py",
    "target_type": "method",
    "symbol": "CleanMacCLITests.test_startup_and_privacy_plans_expose_current_execution_gate_names",
    "locator": "test_cleanmac.py:2940",
    "source": "test_entry",
    "reason": "Ratchet startup/privacy execution-gate naming and no-auto-execute metadata.",
    "hunks": []
  },
  {
    "file_path": "test_cleanmac.py",
    "target_type": "method",
    "symbol": "CleanMacCLITests.test_plan_command_generates_reusable_cleanup_plan",
    "locator": "test_cleanmac.py:3864",
    "source": "test_entry",
    "reason": "Extract reusable cleanup plan contract, filters, AI summary, and contract validation.",
    "hunks": []
  },
  {
    "file_path": "test_cleanmac.py",
    "target_type": "method",
    "symbol": "CleanMacCLITests.test_require_plan_context_*",
    "locator": "test_cleanmac.py:4113",
    "source": "test_entry",
    "reason": "Ratchet plan-context required, root mismatch, and home mismatch failure contracts.",
    "hunks": []
  },
  {
    "file_path": "test_cleanmac.py",
    "target_type": "method",
    "symbol": "CleanMacCLITests.test_inspect_lists_direct_children_sorted_by_size",
    "locator": "test_cleanmac.py:4417",
    "source": "test_entry",
    "reason": "Extract inspect direct child sorting and AI summary coverage.",
    "hunks": []
  },
  {
    "file_path": "test_cleanmac.py",
    "target_type": "method",
    "symbol": "CleanMacCLITests.test_inspect_supports_recursive_min_size_and_path_sort",
    "locator": "test_cleanmac.py:4444",
    "source": "test_entry",
    "reason": "Ratchet recursive inspect min-size and path sort behavior.",
    "hunks": []
  },
  {
    "file_path": "test_cleanmac.py",
    "target_type": "method",
    "symbol": "CleanMacCLITests.test_inspect_accepts_budget_flags_as_non_destructive_preview",
    "locator": "test_cleanmac.py:4476",
    "source": "test_entry",
    "reason": "Ratchet inspect budget flags as preview-only non-destructive metadata.",
    "hunks": []
  },
  {
    "file_path": "test_cleanmac.py",
    "target_type": "method",
    "symbol": "CleanMacCLITests.test_invalid_name_regex_is_rejected_before_deletion",
    "locator": "test_cleanmac.py:4507",
    "source": "test_entry",
    "reason": "Extract invalid name-regex fail-before-delete contract.",
    "hunks": []
  },
  {
    "file_path": "test_cleanmac.py",
    "target_type": "method",
    "symbol": "CleanMacCLITests.test_incomplete_downloads_skip_active_files",
    "locator": "test_cleanmac.py:4526",
    "source": "test_entry",
    "reason": "Ratchet incomplete download active-file skip behavior.",
    "hunks": []
  },
  {
    "file_path": "test_cleanmac.py",
    "target_type": "method",
    "symbol": "CleanMacCLITests.test_mail_downloads_use_age_and_size_defaults",
    "locator": "test_cleanmac.py:4544",
    "source": "test_entry",
    "reason": "Ratchet Mail Downloads age and minimum-size defaults.",
    "hunks": []
  },
  {
    "file_path": "test_cleanmac.py",
    "target_type": "method",
    "symbol": "CleanMacCLITests.test_gpu_cache_provider_only_returns_stale_allowlisted_dirs",
    "locator": "test_cleanmac.py:4573",
    "source": "test_entry",
    "reason": "Extract GPU cache stale allowlist behavior.",
    "hunks": []
  },
  {
    "file_path": "test_cleanmac.py",
    "target_type": "method",
    "symbol": "CleanMacCLITests.test_browser_code_sign_cache_provider_uses_x_shard",
    "locator": "test_cleanmac.py:4605",
    "source": "test_entry",
    "reason": "Ratchet browser code-sign X-shard discovery and outside-root safety guard.",
    "hunks": []
  },
  {
    "file_path": "test_cleanmac.py",
    "target_type": "method",
    "symbol": "CleanMacCLITests.test_older_than_days_filters_new_candidates",
    "locator": "test_cleanmac.py:4677",
    "source": "test_entry",
    "reason": "Extract older-than-days candidate filtering behavior.",
    "hunks": []
  },
  {
    "file_path": "test_cleanmac.py",
    "target_type": "method",
    "symbol": "CleanMacCLITests.test_execute_high_risk_requires_yes",
    "locator": "test_cleanmac.py:4707",
    "source": "test_entry",
    "reason": "Ratchet high-risk execute --yes requirement.",
    "hunks": []
  },
  {
    "file_path": "test_cleanmac.py",
    "target_type": "method",
    "symbol": "CleanMacCLITests.test_clean_risk_policy_strict_requires_yes_for_medium_risk",
    "locator": "test_cleanmac.py:4725",
    "source": "test_entry",
    "reason": "Ratchet strict risk-policy execute guard.",
    "hunks": []
  },
  {
    "file_path": "test_cleanmac.py",
    "target_type": "method",
    "symbol": "CleanMacCLITests.test_clean_risk_policy_permissive_allows_high_risk_without_yes",
    "locator": "test_cleanmac.py:4745",
    "source": "test_entry",
    "reason": "Ratchet permissive risk-policy execute behavior.",
    "hunks": []
  },
  {
    "file_path": "test_cleanmac.py",
    "target_type": "method",
    "symbol": "CleanMacCLITests.test_clean_execute_live_root_requires_explicit_allow_flag / budget gates",
    "locator": "test_cleanmac.py:4767",
    "source": "test_entry",
    "reason": "Extract live-root, max-delete-budget, max-items, and fail-on-skipped execute gates.",
    "hunks": []
  },
  {
    "file_path": "test_cleanmac.py",
    "target_type": "method",
    "symbol": "CleanMacCLITests.test_core_print_report_human_branches_are_covered_in_process",
    "locator": "test_cleanmac.py:5315",
    "source": "test_entry",
    "reason": "Close the batch by ratcheting remaining human print branches and updating closeout docs.",
    "hunks": []
  }
]
```

## BUG_MAP

```json
[]
```

---

## Round 98: Review HTML Selection State

**Aiflow task ID:** `cleanmac-pytest-governance-round-98-review-html-selection-state`

**Files:**
- Modify: `tests/test_review_selection.py`

- [x] Add pytest coverage for review HTML selection summary, selected/excluded classes, disabled checkbox state, and escaped IDs.
- [x] Validate with targeted pytest, ruff format/check, and `make pytest-test`.
- [x] Commit with `test(pytest): cover review html selection state`.

## Round 99: Review Startup Privacy Evidence

**Aiflow task ID:** `cleanmac-pytest-governance-round-99-review-startup-privacy-evidence`

**Files:**
- Modify: `tests/test_review_selection.py`

- [x] Add pytest coverage for startup/privacy plans normalized through review with candidate review evidence and registered schemas.
- [x] Validate with targeted pytest, ruff format/check, and `make pytest-test`.
- [x] Commit with `test(pytest): cover review startup privacy evidence`.

## Round 100: Review Clean Report Evidence

**Aiflow task ID:** `cleanmac-pytest-governance-round-100-review-clean-report-evidence`

**Files:**
- Modify: `tests/test_review_selection.py`

- [x] Add pytest coverage for review synthesizing clean report candidate evidence and matching clean rule metadata.
- [x] Validate with targeted pytest, ruff format/check, and `make pytest-test`.
- [x] Commit with `test(pytest): cover review clean report evidence`.

## Round 101: Startup Privacy Execution Gates

**Aiflow task ID:** `cleanmac-pytest-governance-round-101-startup-privacy-execution-gates`

**Files:**
- Modify: `tests/test_startup_governance.py`
- Modify: `tests/test_privacy_governance.py`

- [x] Add pytest coverage for startup/privacy plan explicit execute gates and no-auto-execute metadata.
- [x] Validate with targeted pytest, ruff format/check, and `make pytest-test`.
- [x] Commit with `test(pytest): cover startup privacy execution gates`.

## Round 102: Reusable Cleanup Plan Contract

**Aiflow task ID:** `cleanmac-pytest-governance-round-102-reusable-cleanup-plan-contract`

**Files:**
- Modify: `tests/test_clean_execution.py`

- [x] Add pytest coverage for plan filter metadata, AI summary, embedded confirmation token, and contract validation.
- [x] Validate with targeted pytest, ruff format/check, and `make pytest-test`.
- [x] Commit with `test(pytest): cover reusable cleanup plan contract`.

## Round 103: Plan Context Failure Contracts

**Aiflow task ID:** `cleanmac-pytest-governance-round-103-plan-context-failure-contracts`

**Files:**
- Modify: `tests/test_clean_execution.py`

- [x] Add pytest coverage for require-plan-context missing plan, root mismatch, and home mismatch failures.
- [x] Validate with targeted pytest, ruff format/check, and `make pytest-test`.
- [x] Commit with `test(pytest): cover plan context failure contracts`.

## Round 104: Inspect Direct Child Sorting

**Aiflow task ID:** `cleanmac-pytest-governance-round-104-inspect-direct-child-sorting`

**Files:**
- Modify: `tests/test_cli_workflows.py`

- [x] Add pytest coverage for inspect direct child size sorting, limit behavior, and AI summary metadata.
- [x] Validate with targeted pytest, ruff format/check, and `make pytest-test`.
- [x] Commit with `test(pytest): cover inspect direct child sorting`.

## Round 105: Inspect Recursive Path Sort

**Aiflow task ID:** `cleanmac-pytest-governance-round-105-inspect-recursive-path-sort`

**Files:**
- Modify: `tests/test_cli_workflows.py`

- [x] Add pytest coverage for recursive inspect min-size filtering, path sort, and depth metadata.
- [x] Validate with targeted pytest, ruff format/check, and `make pytest-test`.
- [x] Commit with `test(pytest): cover inspect recursive path sort`.

## Round 106: Inspect Budget Preview Flags

**Aiflow task ID:** `cleanmac-pytest-governance-round-106-inspect-budget-preview-flags`

**Files:**
- Modify: `tests/test_cli_workflows.py`

- [x] Add pytest coverage for inspect budget flags as non-destructive preview metadata.
- [x] Validate with targeted pytest, ruff format/check, and `make pytest-test`.
- [x] Commit with `test(pytest): cover inspect budget preview flags`.

## Round 107: Invalid Name Regex Gate

**Aiflow task ID:** `cleanmac-pytest-governance-round-107-invalid-name-regex-gate`

**Files:**
- Modify: `tests/test_cli_workflows.py`

- [x] Add pytest coverage that invalid `--name-regex` is rejected before candidate deletion.
- [x] Validate with targeted pytest, ruff format/check, and `make pytest-test`.
- [x] Commit with `test(pytest): cover invalid name regex gate`.

## Round 108: Incomplete Downloads Active Skip

**Aiflow task ID:** `cleanmac-pytest-governance-round-108-incomplete-downloads-active-skip`

**Files:**
- Modify: `tests/test_cli_workflows.py`

- [x] Add pytest coverage for active incomplete-download files being skipped with explicit reason.
- [x] Validate with targeted pytest, ruff format/check, and `make pytest-test`.
- [x] Commit with `test(pytest): cover incomplete downloads active skip`.

## Round 109: Mail Downloads Age Size Defaults

**Aiflow task ID:** `cleanmac-pytest-governance-round-109-mail-downloads-age-size-defaults`

**Files:**
- Modify: `tests/test_cli_workflows.py`

- [x] Add pytest coverage for Mail Downloads age and minimum-size defaults.
- [x] Validate with targeted pytest, ruff format/check, and `make pytest-test`.
- [x] Commit with `test(pytest): cover mail downloads age size defaults`.

## Round 110: GPU Cache Stale Allowlist

**Aiflow task ID:** `cleanmac-pytest-governance-round-110-gpu-cache-stale-allowlist`

**Files:**
- Modify: `tests/test_cli_workflows.py`

- [x] Add pytest coverage for GPU cache provider stale allowlisted directories and not-stale skip reason.
- [x] Validate with targeted pytest, ruff format/check, and `make pytest-test`.
- [x] Commit with `test(pytest): cover gpu cache stale allowlist`.

## Round 111: Browser Code Sign Shard Safety

**Aiflow task ID:** `cleanmac-pytest-governance-round-111-browser-code-sign-shard-safety`

**Files:**
- Modify: `tests/test_cli_workflows.py`

- [x] Add pytest coverage for browser code-sign X-shard discovery and outside-root safety rejection.
- [x] Validate with targeted pytest, ruff format/check, and `make pytest-test`.
- [x] Commit with `test(pytest): cover browser code sign shard safety`.

## Round 112: Older Than Days Filtering

**Aiflow task ID:** `cleanmac-pytest-governance-round-112-older-than-days-filtering`

**Files:**
- Modify: `tests/test_cli_workflows.py`

- [x] Add pytest coverage for `--older-than-days` filtering new candidates and emitting too-new skip reason.
- [x] Validate with targeted pytest, ruff format/check, and `make pytest-test`.
- [x] Commit with `test(pytest): cover older than days filtering`.

## Round 113: High Risk Requires Yes

**Aiflow task ID:** `cleanmac-pytest-governance-round-113-high-risk-requires-yes`

**Files:**
- Modify: `tests/test_clean_execution.py`

- [x] Add pytest coverage that high-risk execute without `--yes` fails before deletion.
- [x] Validate with targeted pytest, ruff format/check, and `make pytest-test`.
- [x] Commit with `test(pytest): cover high risk requires yes`.

## Round 114: Strict Risk Policy Requires Yes

**Aiflow task ID:** `cleanmac-pytest-governance-round-114-strict-risk-policy-requires-yes`

**Files:**
- Modify: `tests/test_clean_execution.py`

- [x] Add pytest coverage for strict risk policy blocking medium-risk execution without `--yes`.
- [x] Validate with targeted pytest, ruff format/check, and `make pytest-test`.
- [x] Commit with `test(pytest): cover strict risk policy requires yes`.

## Round 115: Permissive Risk Policy Allows Execute

**Aiflow task ID:** `cleanmac-pytest-governance-round-115-permissive-risk-policy-execute`

**Files:**
- Modify: `tests/test_clean_execution.py`

- [x] Add pytest coverage for permissive risk policy allowing high-risk execution without `--yes` in sandbox.
- [x] Validate with targeted pytest, ruff format/check, and `make pytest-test`.
- [x] Commit with `test(pytest): cover permissive risk policy execute`.

## Round 116: Execute Safety Budget Gates

**Aiflow task ID:** `cleanmac-pytest-governance-round-116-execute-safety-budget-gates`

**Files:**
- Modify: `tests/test_clean_execution.py`

- [ ] Add pytest coverage for live-root, max-delete-budget, max-items, and fail-on-skipped execute gates.
- [ ] Validate with targeted pytest, ruff format/check, and `make pytest-test`.
- [ ] Commit with `test(pytest): cover execute safety budget gates`.

## Round 117: Human Report Branch Closeout

**Aiflow task ID:** `cleanmac-pytest-governance-round-117-human-report-branch-closeout`

**Files:**
- Modify: `tests/test_report_renderers.py`
- Modify: `docs/superpowers/plans/2026-06-25-pytest-governance-cycle-closeout.md`

- [ ] Add pytest coverage for remaining in-process human report branches and close out Rounds 98-117.
- [ ] Validate with targeted pytest, ruff format/check, and `make pytest-test`.
- [ ] Commit with `test(pytest): cover human report branch closeout`.

---

## Acceptance Criteria

- Twenty aiflow tasks are submitted with IDs `cleanmac-pytest-governance-round-98-*` through `cleanmac-pytest-governance-round-117-*`.
- Each completed round has one focused commit.
- `docs/superpowers/plans/2026-06-25-pytest-governance-cycle-closeout.md` is updated after Round 117.
- Runtime state remains uncommitted: `.harness/store.json`, `.coverage`, `.pytest_cache`, `.venv`, `.mypy_cache`, `.ruff_cache`, and generated caches are excluded.
