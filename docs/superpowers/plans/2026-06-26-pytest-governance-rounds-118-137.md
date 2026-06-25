# Cleanmac Pytest Governance Rounds 118-137

**Goal:** Continue incremental pytest migration from the remaining `test_cleanmac.py` unittest backlog without rewriting the legacy file wholesale.

**Execution contract:**

- Submit all rounds to `/Users/bytedance/Codes/go/src/github/aiflow` before implementation.
- Execute one round at a time.
- Commit after each completed round.
- Use venv-backed validation only: targeted `.venv/bin/python -m pytest`, ruff through `.venv/bin/python`, and `make pytest-test`.
- Do not stage unrelated local changes such as `Makefile` or `scripts/quick_clean.sh`.
- Keep cleanmac AI-first, dry-run-first, zero-resident, and single-shot.

## TARGETS

```json
[
  {
    "round": 118,
    "id": "cleanmac-pytest-governance-round-118-trash-mode-recoverable-routing",
    "legacy_symbol": "CleanMacCLITests.test_clean_trash_delete_mode_routes_candidates_to_recoverable_trash",
    "target_file": "tests/test_trash_mode.py",
    "reason": "Migrate recoverable Trash routing report/log evidence into pytest."
  },
  {
    "round": 119,
    "id": "cleanmac-pytest-governance-round-119-delete-failure-reason-mapping",
    "legacy_symbol": "CleanMacCLITests.test_delete_failure_reason_maps_safety_and_recoverable_failures",
    "target_file": "tests/test_delete_ops.py",
    "reason": "Migrate delete failure reason taxonomy into pytest."
  },
  {
    "round": 120,
    "id": "cleanmac-pytest-governance-round-120-clean-fail-fast-item-failure",
    "legacy_symbol": "CleanMacCLITests.test_clean_execute_fail_fast_stops_on_item_failure",
    "target_file": "tests/test_clean_execution.py",
    "reason": "Migrate fail-fast item failure behavior into pytest."
  },
  {
    "round": 121,
    "id": "cleanmac-pytest-governance-round-121-clean-protected-failure-fail-closed",
    "legacy_symbol": "CleanMacCLITests.test_clean_execute_protected_path_failure_is_fail_closed",
    "target_file": "tests/test_clean_execution.py",
    "reason": "Migrate protected path execution failure fail-closed behavior into pytest."
  },
  {
    "round": 122,
    "id": "cleanmac-pytest-governance-round-122-test-mode-privileged-helper-blocks",
    "legacy_symbol": "CleanMacCLITests.test_test_mode_blocks_privileged_and_automation_helpers",
    "target_file": "tests/test_sudo_guard.py",
    "reason": "Expand pytest coverage for test-mode sudo/automation helper blocking."
  },
  {
    "round": 123,
    "id": "cleanmac-pytest-governance-round-123-hardening-protection-categories",
    "legacy_symbol": "CleanMacCLITests.test_cleanmac_hardening_protection_categories_are_covered",
    "target_file": "tests/test_app_protection.py",
    "reason": "Migrate hardening protection category coverage into pytest."
  },
  {
    "round": 124,
    "id": "cleanmac-pytest-governance-round-124-deep-system-cleanup-categories",
    "legacy_symbol": "CleanMacCLITests.test_deep_system_cleanup_categories_cover_xcode_firmware_apple_silicon_and_diagnostics",
    "target_file": "tests/test_cli_workflows.py",
    "reason": "Migrate deep-system cleanup inspect coverage into pytest."
  },
  {
    "round": 125,
    "id": "cleanmac-pytest-governance-round-125-ai-policy-simulator-guards",
    "legacy_symbol": "CleanMacCLITests.test_ai_policy_simulator_reports_missing_and_satisfied_guards",
    "target_file": "tests/test_ai_contract.py",
    "reason": "Migrate AI policy simulator missing/satisfied guard behavior into pytest."
  },
  {
    "round": 126,
    "id": "cleanmac-pytest-governance-round-126-ai-origin-drifted-plan-rejection",
    "legacy_symbol": "CleanMacCLITests.test_ai_originated_execute_refuses_drifted_plan",
    "target_file": "tests/test_ai_idempotency.py",
    "reason": "Migrate AI-originated drifted plan execute rejection into pytest."
  },
  {
    "round": 127,
    "id": "cleanmac-pytest-governance-round-127-ai-origin-conservative-execute-guards",
    "legacy_symbol": "CleanMacCLITests.test_ai_originated_plan_requires_conservative_execute_guards",
    "target_file": "tests/test_ai_contract.py",
    "reason": "Migrate AI-originated conservative execute guard behavior into pytest."
  },
  {
    "round": 128,
    "id": "cleanmac-pytest-governance-round-128-analyze-tree-markdown-report-links",
    "legacy_symbol": "CleanMacCLITests.test_analyze_tree_writes_markdown_report_with_file_links",
    "target_file": "tests/test_report_renderers.py",
    "reason": "Migrate analyze-tree Markdown report file-link behavior into pytest."
  },
  {
    "round": 129,
    "id": "cleanmac-pytest-governance-round-129-doctor-environment-guidance",
    "legacy_symbol": "CleanMacCLITests.test_doctor_reports_environment_and_full_disk_access_guidance",
    "target_file": "tests/test_cli_basics.py",
    "reason": "Migrate doctor environment and Full Disk Access guidance into pytest."
  },
  {
    "round": 130,
    "id": "cleanmac-pytest-governance-round-130-open-special-finder-targets",
    "legacy_symbol": "CleanMacCLITests.test_open_reports_special_finder_targets",
    "target_file": "tests/test_cli_workflows.py",
    "reason": "Migrate special Finder target preview behavior into pytest."
  },
  {
    "round": 131,
    "id": "cleanmac-pytest-governance-round-131-profiles-safe-budget-defaults",
    "legacy_symbol": "CleanMacCLITests.test_profiles_expand_to_safe_category_and_budget_defaults",
    "target_file": "tests/test_cli_basics.py",
    "reason": "Migrate profile category and budget default expansion into pytest."
  },
  {
    "round": 132,
    "id": "cleanmac-pytest-governance-round-132-links-symbolic-link-mappings",
    "legacy_symbol": "CleanMacCLITests.test_links_reports_symbolic_link_mappings",
    "target_file": "tests/test_cli_workflows.py",
    "reason": "Migrate links mapping preview behavior into pytest."
  },
  {
    "round": 133,
    "id": "cleanmac-pytest-governance-round-133-links-execute-create-remove",
    "legacy_symbol": "CleanMacCLITests.test_links_execute_creates_and_removes_symlink_dirs",
    "target_file": "tests/test_cli_workflows.py",
    "reason": "Migrate links execute create/remove behavior into pytest."
  },
  {
    "round": 134,
    "id": "cleanmac-pytest-governance-round-134-links-remove-dry-run-preserves",
    "legacy_symbol": "CleanMacCLITests.test_links_remove_dry_run_preserves_existing_link_directory",
    "target_file": "tests/test_cli_workflows.py",
    "reason": "Migrate links remove dry-run preservation into pytest."
  },
  {
    "round": 135,
    "id": "cleanmac-pytest-governance-round-135-links-skip-existing-non-symlink",
    "legacy_symbol": "CleanMacCLITests.test_links_execute_skips_existing_non_symlink_mapping",
    "target_file": "tests/test_cli_workflows.py",
    "reason": "Migrate links execute non-symlink skip behavior into pytest."
  },
  {
    "round": 136,
    "id": "cleanmac-pytest-governance-round-136-distribution-governance-files",
    "legacy_symbol": "CleanMacCLITests.test_open_source_governance_files_are_configured",
    "target_file": "tests/test_open_source_governance.py",
    "reason": "Migrate remaining distribution/open-source governance file checks into pytest."
  },
  {
    "round": 137,
    "id": "cleanmac-pytest-governance-round-137-cycle-closeout",
    "legacy_symbol": "CleanMacCLITests.test_core_print_report_human_branches_are_covered_in_process",
    "target_file": "tests/test_report_renderers.py",
    "reason": "Close Rounds 118-137 and refresh the pytest governance cycle closeout."
  }
]
```

## BUG_MAP

```json
[]
```

No production defects are targeted in this batch. The risk being governed is regression risk from legacy `unittest` coverage remaining concentrated in `test_cleanmac.py`.

## Rounds

### Round 118: Trash Mode Recoverable Routing

**Aiflow task ID:** `cleanmac-pytest-governance-round-118-trash-mode-recoverable-routing`

**Files:**
- Modify: `tests/test_trash_mode.py`

- [ ] Add pytest coverage for recoverable Trash routing report fields and deletion log evidence.
- [ ] Validate with targeted pytest, ruff format/check, and `make pytest-test`.
- [ ] Commit with `test(pytest): cover trash recoverable routing`.

### Round 119: Delete Failure Reason Mapping

**Aiflow task ID:** `cleanmac-pytest-governance-round-119-delete-failure-reason-mapping`

**Files:**
- Modify: `tests/test_delete_ops.py`

- [ ] Add pytest coverage for delete failure reason taxonomy.
- [ ] Validate with targeted pytest, ruff format/check, and `make pytest-test`.
- [ ] Commit with `test(pytest): cover delete failure reason mapping`.

### Round 120: Clean Fail-Fast Item Failure

**Aiflow task ID:** `cleanmac-pytest-governance-round-120-clean-fail-fast-item-failure`

**Files:**
- Modify: `tests/test_clean_execution.py`

- [ ] Add pytest coverage that fail-fast stops on item deletion failure.
- [ ] Validate with targeted pytest, ruff format/check, and `make pytest-test`.
- [ ] Commit with `test(pytest): cover clean fail fast item failure`.

### Round 121: Clean Protected Failure Fail-Closed

**Aiflow task ID:** `cleanmac-pytest-governance-round-121-clean-protected-failure-fail-closed`

**Files:**
- Modify: `tests/test_clean_execution.py`

- [ ] Add pytest coverage that protected path execution failures fail closed.
- [ ] Validate with targeted pytest, ruff format/check, and `make pytest-test`.
- [ ] Commit with `test(pytest): cover protected failure fail closed`.

### Round 122: Test Mode Privileged Helper Blocks

**Aiflow task ID:** `cleanmac-pytest-governance-round-122-test-mode-privileged-helper-blocks`

**Files:**
- Modify: `tests/test_sudo_guard.py`

- [ ] Add pytest coverage for test-mode sudo, osascript, and launchctl helper blocking.
- [ ] Validate with targeted pytest, ruff format/check, and `make pytest-test`.
- [ ] Commit with `test(pytest): cover test mode helper blocks`.

### Round 123: Hardening Protection Categories

**Aiflow task ID:** `cleanmac-pytest-governance-round-123-hardening-protection-categories`

**Files:**
- Modify: `tests/test_app_protection.py`

- [ ] Add pytest coverage for hardening protection category metadata and vendor rules.
- [ ] Validate with targeted pytest, ruff format/check, and `make pytest-test`.
- [ ] Commit with `test(pytest): cover hardening protection categories`.

### Round 124: Deep System Cleanup Categories

**Aiflow task ID:** `cleanmac-pytest-governance-round-124-deep-system-cleanup-categories`

**Files:**
- Modify: `tests/test_cli_workflows.py`

- [ ] Add pytest coverage for Xcode, firmware, Apple Silicon, and diagnostics inspect candidates.
- [ ] Validate with targeted pytest, ruff format/check, and `make pytest-test`.
- [ ] Commit with `test(pytest): cover deep system cleanup categories`.

### Round 125: AI Policy Simulator Guards

**Aiflow task ID:** `cleanmac-pytest-governance-round-125-ai-policy-simulator-guards`

**Files:**
- Modify: `tests/test_ai_contract.py`

- [ ] Add pytest coverage for missing and satisfied AI policy simulator guards.
- [ ] Validate with targeted pytest, ruff format/check, and `make pytest-test`.
- [ ] Commit with `test(pytest): cover ai policy simulator guards`.

### Round 126: AI-Origin Drifted Plan Rejection

**Aiflow task ID:** `cleanmac-pytest-governance-round-126-ai-origin-drifted-plan-rejection`

**Files:**
- Modify: `tests/test_ai_idempotency.py`

- [ ] Add pytest coverage for AI-originated execute rejection when plan candidates drift.
- [ ] Validate with targeted pytest, ruff format/check, and `make pytest-test`.
- [ ] Commit with `test(pytest): cover ai drifted plan rejection`.

### Round 127: AI-Origin Conservative Execute Guards

**Aiflow task ID:** `cleanmac-pytest-governance-round-127-ai-origin-conservative-execute-guards`

**Files:**
- Modify: `tests/test_ai_contract.py`

- [ ] Add pytest coverage for AI-originated plan conservative execute guards and success ledger.
- [ ] Validate with targeted pytest, ruff format/check, and `make pytest-test`.
- [ ] Commit with `test(pytest): cover ai conservative execute guards`.

### Round 128: Analyze Tree Markdown Report Links

**Aiflow task ID:** `cleanmac-pytest-governance-round-128-analyze-tree-markdown-report-links`

**Files:**
- Modify: `tests/test_report_renderers.py`

- [ ] Add pytest coverage for analyze-tree Markdown report file links.
- [ ] Validate with targeted pytest, ruff format/check, and `make pytest-test`.
- [ ] Commit with `test(pytest): cover analyze tree markdown links`.

### Round 129: Doctor Environment Guidance

**Aiflow task ID:** `cleanmac-pytest-governance-round-129-doctor-environment-guidance`

**Files:**
- Modify: `tests/test_cli_basics.py`

- [ ] Add pytest coverage for doctor environment and Full Disk Access guidance.
- [ ] Validate with targeted pytest, ruff format/check, and `make pytest-test`.
- [ ] Commit with `test(pytest): cover doctor environment guidance`.

### Round 130: Open Special Finder Targets

**Aiflow task ID:** `cleanmac-pytest-governance-round-130-open-special-finder-targets`

**Files:**
- Modify: `tests/test_cli_workflows.py`

- [ ] Add pytest coverage for special Finder target preview metadata.
- [ ] Validate with targeted pytest, ruff format/check, and `make pytest-test`.
- [ ] Commit with `test(pytest): cover open special finder targets`.

### Round 131: Profiles Safe Budget Defaults

**Aiflow task ID:** `cleanmac-pytest-governance-round-131-profiles-safe-budget-defaults`

**Files:**
- Modify: `tests/test_cli_basics.py`

- [ ] Add pytest coverage for profile category and budget default expansion.
- [ ] Validate with targeted pytest, ruff format/check, and `make pytest-test`.
- [ ] Commit with `test(pytest): cover profiles safe budget defaults`.

### Round 132: Links Symbolic Link Mappings

**Aiflow task ID:** `cleanmac-pytest-governance-round-132-links-symbolic-link-mappings`

**Files:**
- Modify: `tests/test_cli_workflows.py`

- [ ] Add pytest coverage for links mapping preview metadata.
- [ ] Validate with targeted pytest, ruff format/check, and `make pytest-test`.
- [ ] Commit with `test(pytest): cover links symbolic mappings`.

### Round 133: Links Execute Create Remove

**Aiflow task ID:** `cleanmac-pytest-governance-round-133-links-execute-create-remove`

**Files:**
- Modify: `tests/test_cli_workflows.py`

- [ ] Add pytest coverage for links execute create and remove behavior.
- [ ] Validate with targeted pytest, ruff format/check, and `make pytest-test`.
- [ ] Commit with `test(pytest): cover links execute create remove`.

### Round 134: Links Remove Dry-Run Preserves

**Aiflow task ID:** `cleanmac-pytest-governance-round-134-links-remove-dry-run-preserves`

**Files:**
- Modify: `tests/test_cli_workflows.py`

- [ ] Add pytest coverage for links remove dry-run preserving existing link directories.
- [ ] Validate with targeted pytest, ruff format/check, and `make pytest-test`.
- [ ] Commit with `test(pytest): cover links remove dry run`.

### Round 135: Links Skip Existing Non-Symlink

**Aiflow task ID:** `cleanmac-pytest-governance-round-135-links-skip-existing-non-symlink`

**Files:**
- Modify: `tests/test_cli_workflows.py`

- [ ] Add pytest coverage for links execute skipping existing non-symlink mappings.
- [ ] Validate with targeted pytest, ruff format/check, and `make pytest-test`.
- [ ] Commit with `test(pytest): cover links non symlink skip`.

### Round 136: Distribution Governance Files

**Aiflow task ID:** `cleanmac-pytest-governance-round-136-distribution-governance-files`

**Files:**
- Modify: `tests/test_open_source_governance.py`

- [ ] Add pytest coverage for remaining distribution/open-source governance file checks.
- [ ] Validate with targeted pytest, ruff format/check, and `make pytest-test`.
- [ ] Commit with `test(pytest): cover distribution governance files`.

### Round 137: Cycle Closeout

**Aiflow task ID:** `cleanmac-pytest-governance-round-137-cycle-closeout`

**Files:**
- Modify: `tests/test_report_renderers.py`
- Modify: `docs/superpowers/plans/2026-06-25-pytest-governance-cycle-closeout.md`

- [ ] Add final pytest coverage for this batch and update cycle closeout.
- [ ] Validate with targeted pytest, ruff format/check, and `make pytest-test`.
- [ ] Commit with `test(pytest): close pytest governance cycle`.

## Acceptance Criteria

- Twenty aiflow tasks are submitted with IDs `cleanmac-pytest-governance-round-118-*` through `cleanmac-pytest-governance-round-137-*`.
- Each completed round has one focused commit.
- `docs/superpowers/plans/2026-06-25-pytest-governance-cycle-closeout.md` is updated after Round 137.
- Existing dirty files unrelated to this task remain unstaged.
