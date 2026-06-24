# Cleanmac Pytest Release Tests Migration Plan

> For agentic workers: implement this plan task-by-task. Keep each task small, behavior-preserving, and validated with the pytest-safe release test gate.

**Goal:** Improve the existing release-related `unittest` tests by migrating them to pytest-native style while preserving the current safety contracts, release evidence coverage, and `make pytest-test` validation path.

**Architecture:** This is a test-only modernization. The migration keeps the existing release coverage scope and does not change production cleanup, deletion, protection, AI Host, MCP, release, or governance behavior. The pytest-safe test target remains the single project-standard validation surface for this slice.

**Tech Stack:** Python 3.10+, pytest, pytest fixtures, native `assert`, `pytest.raises`, `tmp_path`, existing cleanmac release helper APIs, Makefile `pytest-test`.

---

## Current Baseline

- `pyproject.toml` already configures pytest with strict config and strict markers.
- `Makefile` already defines `PYTEST_SAFE_TARGETS` as:
  - `tests/test_release_readiness.py`
  - `tests/test_release_orchestration.py`
  - `tests/test_release_artifacts.py`
- `make pytest-test` creates an isolated temporary venv and runs the safe pytest targets.
- `tests/helpers.py` already contains pytest-friendly helpers for CLI and sandbox workflows.
- The selected release tests currently run under pytest but mostly use `unittest.TestCase`, `self.assert*`, and `tempfile.TemporaryDirectory`.

---

## Non-Goals

- Do not change production code behavior.
- Do not expand the pytest-safe target list in this phase.
- Do not migrate broad legacy tests such as `test_cleanmac.py` in this phase.
- Do not weaken release readiness, artifact, governance, AI Host, MCP, or deletion safety checks.
- Do not add GUI, TUI, daemon, background scanner, or resident-process behavior.

---

## Task 1: Migrate Release Artifact Tests To Pytest Style

**Files:**
- Modify: `tests/test_release_artifacts.py`

- [ ] Replace `unittest.TestCase` classes with pytest function tests.
- [ ] Replace `tempfile.TemporaryDirectory()` with `tmp_path`.
- [ ] Replace `self.assertEqual`, `self.assertTrue`, `self.assertFalse`, and `self.assertIn` with native `assert`.
- [ ] Replace `self.assertRaisesRegex` with `pytest.raises(..., match=...)`.
- [ ] Keep subprocess script coverage unchanged, including `capture_output=True`, `check=True`, and JSON stdout assertions.
- [ ] Run focused validation:

```bash
python3 -m pytest tests/test_release_artifacts.py -q
```

If local pytest dependencies are missing, use the project-standard target instead:

```bash
make pytest-test
```

---

## Task 2: Migrate Release Orchestration Tests To Pytest Style

**Files:**
- Modify: `tests/test_release_orchestration.py`

- [ ] Replace the `ReleaseOrchestrationTests` class with pytest function tests.
- [ ] Replace temporary directory setup with `tmp_path`.
- [ ] Keep `_write_ready_release_assets()` as the shared fixture helper unless a pytest fixture clearly reduces repetition.
- [ ] Preserve all existing release rehearsal, promotion decision, rollback, and post-publish evidence assertions.
- [ ] Avoid parameterization unless it makes the existing invariants easier to read.
- [ ] Run focused validation:

```bash
python3 -m pytest tests/test_release_orchestration.py -q
```

If local pytest dependencies are missing, use:

```bash
make pytest-test
```

---

## Task 3: Migrate Release Readiness Tests To Pytest Style

**Files:**
- Modify: `tests/test_release_readiness.py`

- [ ] Replace the `ReleaseReadinessTests` class with pytest function tests.
- [ ] Convert temporary release manifest fixtures to `tmp_path`.
- [ ] Replace all `self.assert*` calls with native pytest assertions.
- [ ] Keep existing pytest-style tests at the bottom as functions and avoid unnecessary churn.
- [ ] Consider extracting tiny local helpers only if repeated setup becomes harder to read.
- [ ] Run focused validation:

```bash
python3 -m pytest tests/test_release_readiness.py -q
```

If local pytest dependencies are missing, use:

```bash
make pytest-test
```

---

## Task 4: Validate The Full Pytest-Safe Release Slice

**Files:**
- Verify: `Makefile`
- Verify: `pyproject.toml`

- [ ] Run the project-standard pytest gate:

```bash
make pytest-test
```

- [ ] Confirm the target still uses the same three release-safe files.
- [ ] Confirm no production code changed.
- [ ] Confirm no runtime queue state is staged for commit unless explicitly requested.

---

## Acceptance Criteria

- The three `PYTEST_SAFE_TARGETS` files no longer depend on `unittest.TestCase`.
- Assertions use pytest-native `assert` / `pytest.raises` style.
- Temporary filesystem setup uses pytest `tmp_path` where practical.
- `make pytest-test` passes.
- The diff is limited to test modernization plus this plan and aiflow queue setup artifacts if intentionally added.
