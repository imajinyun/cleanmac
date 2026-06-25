# Cleanmac Pytest Governance Rounds 78-97 Implementation Plan

> **For agentic workers:** Continue the pytest migration in committed, reviewable rounds. Keep `test_cleanmac.py` runnable until each migrated slice has equivalent pytest-native coverage.

**Goal:** Move the next 20 stable AI, CLI, developer-tool, and review-selection governance slices out of the legacy unittest backlog into focused pytest tests, without changing production cleanup behavior.

**Architecture:** Each round extends one existing `tests/test_*.py` pytest surface where possible. Validate each slice with targeted pytest, ruff format/check for touched Python files, and `make pytest-test`, then commit independently.

**Non-goals:** Do not rewrite `test_cleanmac.py` wholesale. Do not add GUI, TUI, daemons, login items, background scanners, or resident processes. Do not change deletion primitives or execution policy unless a real defect is proven by tests.

---

## Step Status

- Step1 test preparation: completed with `BITS_TMP_ROOT=/var/folders/57/pqx08bk577x758hnslxkfhm40000gn/T/tmp.YNrsOqICWn`.
- Step2 context: `LANG=python`; pytest-native function tests with project helpers and temporary-venv validation.
- Step3 scope: `non_diff`; migrate remaining stable slices from `test_cleanmac.py` into pytest files under `tests/`.
- Step4 defect analysis: `BUG_MAP=[]`; this batch is equivalence and governance coverage unless a pytest exposes a real defect.
- Step5 execution: complete one round at a time with validation and commit.
- Step6 report: update this plan and the cycle closeout as rounds complete.

---

## TARGETS

```json
[
  {
    "file_path": "test_cleanmac.py",
    "target_type": "method",
    "symbol": "CleanMacCLITests.test_capabilities_describes_commands_and_safety_model",
    "locator": "test_cleanmac.py:289",
    "source": "test_entry",
    "reason": "Extract remaining capabilities safety guardrail assertions into pytest-native coverage.",
    "hunks": []
  },
  {
    "file_path": "test_cleanmac.py",
    "target_type": "method",
    "symbol": "CleanMacCLITests.test_provider_export_parity_reports_same_tool_names",
    "locator": "test_cleanmac.py:612",
    "source": "test_entry",
    "reason": "Extract provider export parity assertions into focused AI schema pytest coverage.",
    "hunks": []
  },
  {
    "file_path": "test_cleanmac.py",
    "target_type": "method",
    "symbol": "CleanMacCLITests.test_ai_schema_builds_safe_argv_without_shell_or_implicit_execute",
    "locator": "test_cleanmac.py:621",
    "source": "test_entry",
    "reason": "Extract safe argv and destructive confirmation invariants for AI tool contracts.",
    "hunks": []
  },
  {
    "file_path": "test_cleanmac.py",
    "target_type": "method",
    "symbol": "CleanMacCLITests.test_clean_reports_ai_confirmation_summary_for_dry_run_and_execute",
    "locator": "test_cleanmac.py:822",
    "source": "test_entry",
    "reason": "Ratchet AI confirmation summary, human summary, and execution ledger coverage in pytest.",
    "hunks": []
  },
  {
    "file_path": "test_cleanmac.py",
    "target_type": "method",
    "symbol": "CleanMacCLITests.test_ai_confirmation_token_is_required_and_bound_before_execute",
    "locator": "test_cleanmac.py:910",
    "source": "test_entry",
    "reason": "Ratchet token-required execute gates in pytest.",
    "hunks": []
  },
  {
    "file_path": "test_cleanmac.py",
    "target_type": "method",
    "symbol": "CleanMacCLITests.test_ai_confirmation_token_boundary_conditions",
    "locator": "test_cleanmac.py:1010",
    "source": "test_entry",
    "reason": "Ratchet token context and token boundary behavior in pytest.",
    "hunks": []
  },
  {
    "file_path": "test_cleanmac.py",
    "target_type": "method",
    "symbol": "CleanMacCLITests.test_unknown_category_is_rejected_with_valid_category_guidance",
    "locator": "test_cleanmac.py:1265",
    "source": "test_entry",
    "reason": "Extract unknown-category JSON error taxonomy and guidance coverage.",
    "hunks": []
  },
  {
    "file_path": "test_cleanmac.py",
    "target_type": "method",
    "symbol": "CleanMacCLITests.test_profiles_expand_to_safe_category_and_budget_defaults",
    "locator": "test_cleanmac.py:1306",
    "source": "test_entry",
    "reason": "Ratchet profiles metadata and safe defaults in pytest.",
    "hunks": []
  },
  {
    "file_path": "test_cleanmac.py",
    "target_type": "method",
    "symbol": "CleanMacCLITests.test_permissions_preflight_reports_privilege_and_fda_requirements",
    "locator": "test_cleanmac.py:1918",
    "source": "test_entry",
    "reason": "Expand tool governance contract validation around permissions preflight.",
    "hunks": []
  },
  {
    "file_path": "test_cleanmac.py",
    "target_type": "method",
    "symbol": "CleanMacCLITests.test_tool_plan_is_readonly_and_lists_manual_commands",
    "locator": "test_cleanmac.py:1960",
    "source": "test_entry",
    "reason": "Ratchet readonly/manual command tool-plan behavior.",
    "hunks": []
  },
  {
    "file_path": "test_cleanmac.py",
    "target_type": "method",
    "symbol": "CleanMacCLITests.test_tool_plan_expands_package_manager_dry_run_adapters",
    "locator": "test_cleanmac.py:1982",
    "source": "test_entry",
    "reason": "Ratchet package-manager dry-run adapter expansion.",
    "hunks": []
  },
  {
    "file_path": "test_cleanmac.py",
    "target_type": "method",
    "symbol": "CleanMacCLITests.test_tool_execute_dry_run_uses_allowlisted_commands",
    "locator": "test_cleanmac.py:2024",
    "source": "test_entry",
    "reason": "Ratchet dry-run execution allowlist behavior for developer tools.",
    "hunks": []
  },
  {
    "file_path": "test_cleanmac.py",
    "target_type": "method",
    "symbol": "CleanMacCLITests.test_tool_execute_blocks_destructive_without_yes",
    "locator": "test_cleanmac.py:2084",
    "source": "test_entry",
    "reason": "Ratchet destructive developer-tool execute blocking without explicit yes.",
    "hunks": []
  },
  {
    "file_path": "test_cleanmac.py",
    "target_type": "method",
    "symbol": "CleanMacCLITests.test_review_generates_selection_file_from_plan",
    "locator": "test_cleanmac.py:2413",
    "source": "test_entry",
    "reason": "Extract review selection generation and candidate evidence coverage.",
    "hunks": []
  },
  {
    "file_path": "test_cleanmac.py",
    "target_type": "method",
    "symbol": "CleanMacCLITests.test_review_selection_supports_explicit_include_and_exclude",
    "locator": "test_cleanmac.py:2495",
    "source": "test_entry",
    "reason": "Ratchet explicit include/exclude review selection behavior.",
    "hunks": []
  },
  {
    "file_path": "test_cleanmac.py",
    "target_type": "method",
    "symbol": "CleanMacCLITests.test_review_validates_existing_selection_fingerprint_and_ids",
    "locator": "test_cleanmac.py:2575",
    "source": "test_entry",
    "reason": "Ratchet review fingerprint and ID validation behavior.",
    "hunks": []
  },
  {
    "file_path": "test_cleanmac.py",
    "target_type": "method",
    "symbol": "CleanMacCLITests.test_review_item_scope_filters_display_items_without_changing_selection",
    "locator": "test_cleanmac.py:2653",
    "source": "test_entry",
    "reason": "Ratchet review item scope display filtering.",
    "hunks": []
  },
  {
    "file_path": "test_cleanmac.py",
    "target_type": "method",
    "symbol": "CleanMacCLITests.test_review_item_sort_orders_display_items_without_changing_selection",
    "locator": "test_cleanmac.py:2723",
    "source": "test_entry",
    "reason": "Ratchet review item sort display behavior.",
    "hunks": []
  },
  {
    "file_path": "test_cleanmac.py",
    "target_type": "method",
    "symbol": "CleanMacCLITests.test_core_print_report_human_branches_are_covered_in_process",
    "locator": "test_cleanmac.py:5315",
    "source": "test_entry",
    "reason": "Extract remaining human report branch coverage into pytest.",
    "hunks": []
  },
  {
    "file_path": "test_cleanmac.py",
    "target_type": "method",
    "symbol": "CleanMacCLITests.test_open_source_governance_files_are_configured",
    "locator": "test_cleanmac.py:5550",
    "source": "test_entry",
    "reason": "Close the batch by ratcheting remaining distribution governance checks and updating closeout docs.",
    "hunks": []
  }
]
```

## BUG_MAP

```json
[]
```

---

## Round 78: Capabilities Safety Guardrail Deep Contract

**Aiflow task ID:** `cleanmac-pytest-governance-round-78-capabilities-safety-guardrails`

**Files:**
- Modify: `tests/test_cli_basics.py`

- [x] Add pytest coverage for capabilities safety guardrail command flags, default protected bundle IDs, deletion ownership, and no-resident product safety metadata.
- [x] Validate with targeted pytest, ruff format/check, and `make pytest-test`.
- [x] Commit with `test(pytest): cover capabilities safety guardrails`.

## Round 79: Capabilities Open-Source Gap Governance Metadata

**Aiflow task ID:** `cleanmac-pytest-governance-round-79-open-source-gap-metadata`

**Files:**
- Modify: `tests/test_cli_basics.py`

- [x] Add pytest coverage for open-source gap governance item IDs, evidence fields, non-goals, and release-gate metadata exposed through capabilities.
- [x] Validate with targeted pytest, ruff format/check, and `make pytest-test`.
- [x] Commit with `test(pytest): cover open source gap metadata`.

## Round 80: AI Provider Export Parity

**Aiflow task ID:** `cleanmac-pytest-governance-round-80-ai-provider-export-parity`

**Files:**
- Modify: `tests/test_ai_schema_exports.py`

- [x] Add pytest coverage that OpenAI, Anthropic, MCP, and aggregate exports expose identical tool names and no parity violations.
- [x] Validate with targeted pytest, ruff format/check, and `make pytest-test`.
- [x] Commit with `test(pytest): cover ai provider export parity`.

## Round 81: AI Safe Argv Builder Gates

**Aiflow task ID:** `cleanmac-pytest-governance-round-81-ai-safe-argv-gates`

**Files:**
- Modify: `tests/test_ai_schema_exports.py`

- [x] Add pytest coverage that AI argv templates never use shell invocation, preserve destructive confirmation requirements, and do not imply execute by default.
- [x] Validate with targeted pytest, ruff format/check, and `make pytest-test`.
- [x] Commit with `test(pytest): cover ai safe argv gates`.

## Round 82: Clean AI Confirmation Summary Ledger

**Aiflow task ID:** `cleanmac-pytest-governance-round-82-clean-ai-confirmation-ledger`

**Files:**
- Modify: `tests/test_ai_idempotency.py`

- [x] Add pytest coverage for dry-run AI confirmation summary, human summary next command, execute summary, and execution ledger fields.
- [x] Validate with targeted pytest, ruff format/check, and `make pytest-test`.
- [x] Commit with `test(pytest): cover clean ai confirmation ledger`.

## Round 83: Execute Requires Bound Confirmation Token

**Aiflow task ID:** `cleanmac-pytest-governance-round-83-execute-token-required`

**Files:**
- Modify: `tests/test_clean_execution.py`

- [x] Add pytest coverage that execute rejects missing, malformed, wrong-phrase, and mismatched confirmation tokens before deletion.
- [x] Validate with targeted pytest, ruff format/check, and `make pytest-test`.
- [x] Commit with `test(pytest): cover execute token requirements`.

## Round 84: Confirmation Token Boundary Conditions

**Aiflow task ID:** `cleanmac-pytest-governance-round-84-token-boundary-conditions`

**Files:**
- Modify: `tests/test_clean_execution.py`

- [x] Add pytest coverage for token context stability, category/order sensitivity, delete-mode binding, and plan-derived token boundaries.
- [x] Validate with targeted pytest, ruff format/check, and `make pytest-test`.
- [x] Commit with `test(pytest): cover token boundary conditions`.

## Round 85: JSON Safety Error Taxonomy

**Aiflow task ID:** `cleanmac-pytest-governance-round-85-json-safety-errors`

**Files:**
- Modify: `tests/test_ai_errors.py`

- [x] Add pytest coverage for unknown-category guidance and missing-confirmation JSON error contracts.
- [x] Validate with targeted pytest, ruff format/check, and `make pytest-test`.
- [x] Commit with `test(pytest): cover json safety error taxonomy`.

## Round 86: CLI Unknown Category And Analyze Guidance

**Aiflow task ID:** `cleanmac-pytest-governance-round-86-cli-guidance`

**Files:**
- Modify: `tests/test_cli_workflows.py`

- [x] Add pytest coverage for unknown category CLI guidance and analyze report sandbox-root metadata.
- [x] Validate with targeted pytest, ruff format/check, and `make pytest-test`.
- [x] Commit with `test(pytest): cover cli guidance contracts`.

## Round 87: Profiles And Links Preview Metadata

**Aiflow task ID:** `cleanmac-pytest-governance-round-87-profiles-links-preview`

**Files:**
- Modify: `tests/test_cli_workflows.py`

- [x] Add pytest coverage for profile safe category expansion, budget defaults, link preview metadata, and non-destructive defaults.
- [x] Validate with targeted pytest, ruff format/check, and `make pytest-test`.
- [x] Commit with `test(pytest): cover profiles links preview`.

## Round 88: Links Execute Compatibility

**Aiflow task ID:** `cleanmac-pytest-governance-round-88-links-execute-compatibility`

**Files:**
- Modify: `tests/test_cli_workflows.py`

- [ ] Add pytest coverage for link create/remove execution and existing non-symlink skip behavior.
- [ ] Validate with targeted pytest, ruff format/check, and `make pytest-test`.
- [ ] Commit with `test(pytest): cover links execute compatibility`.

## Round 89: Permissions Preflight Contract

**Aiflow task ID:** `cleanmac-pytest-governance-round-89-permissions-preflight-contract`

**Files:**
- Modify: `tests/test_tool_governance.py`

- [ ] Add pytest coverage for permissions preflight contract validation, privilege requirements, FDA requirements, and read-only semantics.
- [ ] Validate with targeted pytest, ruff format/check, and `make pytest-test`.
- [ ] Commit with `test(pytest): cover permissions preflight contract`.

## Round 90: Tool Plan Readonly Manual Commands

**Aiflow task ID:** `cleanmac-pytest-governance-round-90-tool-plan-readonly-manual`

**Files:**
- Modify: `tests/test_tool_governance.py`

- [ ] Add pytest coverage for readonly tool-plan behavior, manual destructive recommendations, excluded commands, and contract schema validation.
- [ ] Validate with targeted pytest, ruff format/check, and `make pytest-test`.
- [ ] Commit with `test(pytest): cover tool plan readonly manual commands`.

## Round 91: Package Manager Adapter Metadata

**Aiflow task ID:** `cleanmac-pytest-governance-round-91-package-manager-adapters`

**Files:**
- Modify: `tests/test_tool_governance.py`

- [ ] Add pytest coverage for package-manager dry-run commands, cleanup scope, path categories, and risk metadata.
- [ ] Validate with targeted pytest, ruff format/check, and `make pytest-test`.
- [ ] Commit with `test(pytest): cover package manager adapters`.

## Round 92: Tool Execute Dry-Run Allowlist

**Aiflow task ID:** `cleanmac-pytest-governance-round-92-tool-execute-dry-run-allowlist`

**Files:**
- Modify: `tests/test_tool_governance.py`

- [ ] Add pytest coverage for dry-run execution using only allowlisted readonly commands across Docker and package-manager adapters.
- [ ] Validate with targeted pytest, ruff format/check, and `make pytest-test`.
- [ ] Commit with `test(pytest): cover tool execute dry-run allowlist`.

## Round 93: Tool Execute Destructive Blocks

**Aiflow task ID:** `cleanmac-pytest-governance-round-93-tool-execute-destructive-blocks`

**Files:**
- Modify: `tests/test_tool_governance.py`

- [ ] Add pytest coverage that destructive tool execution blocks without explicit yes and reports blocked reasons for all results.
- [ ] Validate with targeted pytest, ruff format/check, and `make pytest-test`.
- [ ] Commit with `test(pytest): cover tool execute destructive blocks`.

## Round 94: Review Selection Generation Evidence

**Aiflow task ID:** `cleanmac-pytest-governance-round-94-review-selection-generation`

**Files:**
- Modify: `tests/test_review_selection.py`

- [ ] Add pytest coverage for review selection generation, candidate evidence, human summary, selected item IDs, and output file contract.
- [ ] Validate with targeted pytest, ruff format/check, and `make pytest-test`.
- [ ] Commit with `test(pytest): cover review selection generation`.

## Round 95: Review Explicit Include Exclude

**Aiflow task ID:** `cleanmac-pytest-governance-round-95-review-include-exclude`

**Files:**
- Modify: `tests/test_review_selection.py`

- [ ] Add pytest coverage for explicit include/exclude selections, protected candidate exclusion, and unknown ID failures.
- [ ] Validate with targeted pytest, ruff format/check, and `make pytest-test`.
- [ ] Commit with `test(pytest): cover review include exclude`.

## Round 96: Review Existing Selection Validation

**Aiflow task ID:** `cleanmac-pytest-governance-round-96-review-selection-validation`

**Files:**
- Modify: `tests/test_review_selection.py`

- [ ] Add pytest coverage for existing selection fingerprint validation, source mismatch handling, and selected ID/path validation.
- [ ] Validate with targeted pytest, ruff format/check, and `make pytest-test`.
- [ ] Commit with `test(pytest): cover review selection validation`.

## Round 97: Review Display Filters And Closeout

**Aiflow task ID:** `cleanmac-pytest-governance-round-97-review-display-closeout`

**Files:**
- Modify: `tests/test_review_selection.py`
- Modify: `docs/superpowers/plans/2026-06-25-pytest-governance-cycle-closeout.md`

- [ ] Add pytest coverage for review item scope/sort display filters without changing selected item state.
- [ ] Update the closeout document with Round 78-97 status and the next backlog slices.
- [ ] Validate with targeted pytest, ruff format/check, and `make pytest-test`.
- [ ] Commit with `test(pytest): cover review display filters`.

---

## Acceptance Criteria

- Twenty aiflow tasks are submitted with IDs `cleanmac-pytest-governance-round-78-*` through `cleanmac-pytest-governance-round-97-*`.
- Each completed round has one focused commit.
- Every round runs targeted pytest, ruff format/check, and `make pytest-test`.
- No production code is changed unless a pytest exposes a real defect.
- `.harness/store.json`, caches, temporary venvs, coverage files, and runtime state are not committed.
