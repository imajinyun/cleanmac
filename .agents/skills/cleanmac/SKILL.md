---
name: cleanmac
description: cleanmac development patterns and pytest migration workflows for the AI-first, zero-resident macOS cleanup CLI. Use when working on cleanmac test governance, unittest-to-pytest migration, Makefile validation targets, or repository workflow conventions.
---

# cleanmac Development Patterns

> Auto-generated skill from repository analysis

## Overview

This skill teaches the core development conventions and workflows used in the `cleanmac` Python codebase. It covers file organization, coding style, commit patterns, and the main workflows for modernizing and governing test suites—especially migrating from `unittest` to `pytest`. You'll learn how to keep your contributions consistent, how to expand test coverage, and how to document governance changes effectively.

## Coding Conventions

- **File Naming:**  
  Use `snake_case` for all Python files and modules.  
  *Example:*  
  ```python
  # Good
  clean_mac.py
  test_utils.py

  # Bad
  CleanMac.py
  testUtils.py
  ```

- **Imports:**  
  Use relative imports within the package.  
  *Example:*  
  ```python
  from .utils import clean_temp_files
  ```

- **Exports:**  
  Prefer named exports (explicitly listing exported symbols).  
  *Example:*  
  ```python
  __all__ = ['clean_temp_files', 'remove_cache']
  ```

- **Commit Messages:**  
  Follow [Conventional Commits](https://www.conventionalcommits.org/) with prefixes like `test:` and `chore:`.  
  *Example:*  
  ```
  test: migrate cache tests to pytest-native style
  chore: update Makefile for new pytest targets
  ```

## Workflows

### Migrate Unittest to Pytest
**Trigger:** When you want to modernize or standardize test suites from `unittest` to `pytest`.
**Command:** `/migrate-unittest-to-pytest`

1. Identify target test modules using `unittest.TestCase` or similar wrappers.
2. Refactor test files in `tests/` to use `pytest`-native functions, assertions, and fixtures (like `tmp_path`, `pytest.raises`, `@pytest.mark.parametrize`).
   *Example:*
   ```python
   # Before (unittest)
   import unittest

   class TestCleaner(unittest.TestCase):
       def test_removes_temp(self):
           self.assertTrue(clean_temp_files())

   # After (pytest)
   def test_removes_temp(tmp_path):
       assert clean_temp_files(tmp_path)
   ```
3. Update the `Makefile` to include migrated tests in relevant pytest targets (e.g., `pytest-governance-smoke`, `ai-robustness-smoke`, `pytest-test`).
4. Add or update implementation/governance plan documents in `docs/superpowers/plans/` to record the migration.
5. Validate migration by running `pytest` targets and ensuring all tests pass.

### Update Pytest Governance Coverage
**Trigger:** When you want to increase the breadth of test coverage under pytest governance or add new test modules.
**Command:** `/update-pytest-governance`

1. Migrate additional test modules from `unittest` to `pytest`-native style (as above).
2. Update `Makefile` pytest targets to include the new or migrated test files.
3. Add corresponding governance or implementation plan markdown files under `docs/superpowers/plans/`.
4. Validate by running updated pytest targets and confirming successful execution.

### Document Governance or Migration Plan
**Trigger:** When you complete a migration or governance update and need to document the plan or process.
**Command:** `/document-governance-plan`

1. Write a markdown plan document summarizing the migration or governance change.
   *Example:*
   ```markdown
   # 2026-06-24-pytest-migration.md

   ## Summary
   Migrated all cache-related tests from unittest to pytest-native style.
   ```
2. Add the markdown file to `docs/superpowers/plans/` with a date-stamped filename.
3. Reference the plan in the relevant commit message and ensure it matches the migrated/updated test files.

## Testing Patterns

- **Test File Naming:**  
  Test files follow the pattern `*_test.py` and are located in the `tests/` directory.

- **Framework:**  
  Tests are being migrated from `unittest` to `pytest`. Use `pytest`-native functions and fixtures.

- **Example Test (pytest):**  
  ```python
  import pytest

  @pytest.mark.parametrize("input,expected", [
      ("foo", True),
      ("bar", False),
  ])
  def test_is_clean(input, expected):
      assert is_clean(input) is expected
  ```

## Commands

| Command                        | Purpose                                                        |
|--------------------------------|----------------------------------------------------------------|
| /migrate-unittest-to-pytest    | Migrate test files from unittest to pytest-native style         |
| /update-pytest-governance      | Expand or update pytest governance test coverage                |
| /document-governance-plan      | Create or update documentation for test migration/governance    |
