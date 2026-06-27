from __future__ import annotations

import shutil
import subprocess

import pytest

from tests.helpers import PROJECT_ROOT


def test_makefile_exposes_validation_targets() -> None:
    makefile = (PROJECT_ROOT / "Makefile").read_text(encoding="utf-8")
    agent_guide = (PROJECT_ROOT / "AGENTS.md").read_text(encoding="utf-8")

    assert "format:" in makefile
    assert "lint:" in makefile
    assert "type-check:" in makefile
    assert "coverage:" in makefile
    assert "quality-check: lint type-check coverage" in makefile
    assert "local-test:" in makefile
    assert "PYTHON=$(PYTHON) ./scripts/test.sh" in makefile
    assert "pytest-parity-test:" in makefile
    assert "pytest-governance-smoke:" in makefile
    assert "pytest-governance-smoke: pytest-no-unittest-regression-smoke" in makefile
    assert "pytest-no-unittest-regression-smoke:" in makefile
    assert "pytest-ai-host-smoke:" in makefile
    assert "pytest-test:" in makefile
    assert "pytest-test: pytest-parity-test" in makefile
    assert "clean-test-artifacts:" in makefile
    assert "[ ! -e .coverage ] || /bin/rm -f .coverage" in makefile
    assert "[ ! -e cleanmac.egg-info ] || /bin/rm -R cleanmac.egg-info" in makefile
    assert "find cleancli tests scripts -type d -name __pycache__" in makefile
    assert "make clean-test-artifacts" in agent_guide
    assert "Validation targets that create caches" in agent_guide
    assert "After validation, remove local test leftovers" in agent_guide
    assert '$(PYTHON) -m venv "$$tmpdir/venv"' in makefile
    assert "\"$$tmpdir/venv/bin/python\" -m pip install -e '.[test]'" in makefile
    assert 'PYTEST_ADDOPTS="-p no:cacheprovider"' in makefile
    assert "CLEANMAC_TEST_MODE=1 CLEANMAC_TEST_NO_AUTH=1 PYTHONDONTWRITEBYTECODE=1" in makefile
    assert (
        "PYTEST_SAFE_TARGETS := tests/test_release_readiness.py tests/test_release_orchestration.py "
        "tests/test_release_artifacts.py tests/test_path_safety.py tests/test_trash_mode.py "
        "tests/test_delete_ops.py tests/test_security_scan.py"
    ) in makefile
    assert (
        "PYTEST_AI_ROBUSTNESS_TARGETS := tests/test_ai_versioning.py tests/test_mcp_protocol.py "
        "tests/test_ai_concurrency.py tests/test_ai_policy.py tests/test_ai_host_integration.py"
    ) in makefile
    assert (
        "PYTEST_AI_HOST_TARGETS := tests/test_ai_runbook.py tests/test_ai_host_policy.py "
        "tests/test_ai_self_test.py tests/test_ai_decision_matrix.py tests/test_ai_governance.py "
        "tests/test_ai_host_evidence.py tests/test_ai_readiness.py tests/test_ai_host_scenarios.py "
        "tests/test_ai_eval.py tests/test_mcp_server.py"
    ) in makefile
    assert "tests/test_ai_trace_persistence.py" in makefile
    assert '"$$tmpdir/venv/bin/python" -m pytest $(PYTEST_SAFE_TARGETS) -q' in makefile
    assert '"$$tmpdir/venv/bin/python" -m pytest $(PYTEST_AI_HOST_TARGETS) -q' in makefile
    assert '"$$tmpdir/venv/bin/python" -m pytest $(PYTEST_AI_ROBUSTNESS_TARGETS) -q' in makefile
    assert "trap 'rm -rf \"$$tmpdir\"; $(MAKE) clean-test-artifacts >/dev/null' EXIT" in makefile
    assert "assert targets == expected, targets" in makefile
    assert "assert robustness_targets ==" in makefile
    assert 'old_all="pytest test_cleanmac.py " + "tests -q"' in makefile
    assert 'old_robustness="python -m unittest " + "tests.test_ai_versioning"' in makefile
    assert "assert old_all not in text" in makefile
    assert "assert old_robustness not in text" in makefile
    assert 'forbidden=("import unittest", "unittest.TestCase", "unittest.main", "self.assert")' in makefile
    assert 'Path("tests/test_mcp_server.py").read_text' in makefile
    assert "build-check:" in makefile
    assert "package-smoke:" in makefile
    assert "script-smoke:" in makefile
    assert "bundle-audit-smoke:" in makefile
    assert "macos-smoke:" in makefile
    assert "security-smoke:" in makefile
    assert "dependency-audit-smoke:" in makefile
    assert "docs-smoke:" in makefile
    assert "governance-smoke:" in makefile
    assert "governance-integrity-smoke:" in makefile
    assert "ai-first-release-checklist-smoke:" in makefile
    assert "ai-governance-smoke:" in makefile
    assert "ai-contract-smoke:" in makefile
    assert "governed-execution-smoke:" in makefile
    assert 'run("ai-contract-samples")' in makefile
    assert 'samples["schema"] == "cleanmac.ai-contract-samples.v1"' in makefile
    assert "cleanmac.mcp-resource-index.v1" in makefile
    assert "mcp-resource-index-smoke:" in makefile
    assert "cleanmac.mcp-prompt-index.v1" in makefile
    assert "mcp-prompt-index-smoke:" in makefile
    assert "cleanmac.mcp-meta-index.v1" in makefile
    assert "mcp-meta-index-smoke:" in makefile
    assert "cleanmac.mcp-tool-index.v1" in makefile
    assert "mcp-tool-index-smoke:" in makefile
    assert "cleanmac.mcp-surface-audit.v1" in makefile
    assert "mcp-surface-audit-smoke:" in makefile
    assert 'payload["ready"] is True, payload' in makefile
    assert 'payload["resource_count"] == 42' in makefile
    assert "cleanmac://mcp/destructive-tool-governance" in makefile
    assert "cleanmac://ai/operation-log-explainability" in makefile
    assert "cleanmac://ai/cold-start-budget" in makefile
    assert "cleanmac://ai/no-disturbance" in makefile
    assert "cleanmac://ai/entrypoints" in makefile
    assert "cleanmac://ai/safety-chain" in makefile
    assert "cleanmac://ai/workflow-contract" in makefile
    assert "contract_samples_roundtrip" in makefile
    assert 'run("ai-eval-run", "--scenario", "contract_samples_roundtrip")' in makefile
    assert "open-source-smoke:" in makefile
    assert "ai-host-smoke:" in makefile
    assert "$(MAKE) pytest-ai-host-smoke" in makefile
    assert "ai-robustness-smoke:" in makefile
    assert "distribution-smoke:" in makefile
    assert "homebrew-formula-smoke:" in makefile
    assert "zipapp" in makefile
    assert "cleanmac.pyz" in makefile
    assert "class Cleanmac < Formula" in makefile
    assert "homebrew_formula" in makefile
    assert "release-artifacts-smoke:" in makefile
    assert "release-readiness-contract-smoke:" in makefile
    assert "release-readiness-smoke:" in makefile
    assert "release-rehearsal-smoke:" in makefile
    assert "release-promotion-smoke:" in makefile
    assert "release-rollback-smoke:" in makefile
    assert "release-post-publish-smoke:" in makefile
    assert "release-post-publish-result-smoke:" in makefile
    assert "--dist-dir" in makefile
    assert "--assets-dir" in makefile
    assert 'assert report["ready"] is True' in makefile
    assert "no-cache-check:" in makefile
    assert "docker-test" in makefile
    assert "no-cache-docker-test:" in makefile
    assert "no-cache-release-check:" in makefile
    assert (
        "release-check: quality-check local-test pytest-test pytest-governance-smoke build-check package-smoke "
        "script-smoke bundle-audit-smoke macos-smoke security-smoke dependency-audit-smoke docs-smoke "
        "governance-smoke governance-integrity-smoke zero-resident-audit-smoke ai-first-release-checklist-smoke "
        "ai-governance-smoke ai-contract-smoke governed-execution-smoke mcp-smoke mcp-meta-index-smoke "
        "mcp-resource-index-smoke mcp-prompt-index-smoke mcp-tool-index-smoke mcp-surface-audit-smoke "
        "ai-host-smoke ai-robustness-smoke open-source-smoke distribution-smoke homebrew-formula-smoke "
        "release-artifacts-smoke release-readiness-contract-smoke release-readiness-smoke "
        "release-diagnostics-smoke release-rehearsal-smoke release-promotion-smoke release-rollback-smoke "
        "release-post-publish-smoke release-post-publish-result-smoke release-post-publish-evidence-template-smoke "
        "docker-test"
    ) in makefile
    assert "PYTHON ?= python3" in makefile
    assert "DOCKER_IMAGE ?= debian:bookworm-slim" in makefile
    assert "RUFF_REQUIREMENT ?= ruff>=0.8" in makefile
    assert "DOCKER_RUN_FLAGS ?=" in makefile
    assert '-v "$(SANDBOX_MOUNT):/work:ro"' in makefile
    assert "$(DOCKER_RUN_FLAGS)" in makefile
    assert '/tmp/cleanmac-venv/bin/python -m pip install -e ".[test]"' in makefile
    assert "PYTHONDONTWRITEBYTECODE=1 /tmp/cleanmac-venv/bin/python -m unittest -v" in makefile
    assert 'DOCKER_RUN_FLAGS="--pull=always" $(MAKE) docker-test' in makefile
    assert "$(PYTHON) -m ruff format --check ." not in makefile
    assert "$(PYTHON) -m ruff check ." not in makefile
    assert "\"$$tmpdir/venv/bin/python\" -m pip install '$(RUFF_REQUIREMENT)'" in makefile
    assert ('RUFF_CACHE_DIR="$$tmpdir/ruff-cache" "$$tmpdir/venv/bin/python" -m ruff format --check .') in makefile
    assert 'RUFF_CACHE_DIR="$$tmpdir/ruff-cache" "$$tmpdir/venv/bin/python" -m ruff check .' in makefile
    assert "$(PYTHON) -m mypy" not in makefile
    assert "$(PYTHON) -m coverage run -m unittest -v" not in makefile
    assert "\"$$tmpdir/venv/bin/python\" -m pip install -e '.[dev]'" in makefile
    assert '"$$tmpdir/venv/bin/python" -m mypy cleanmac.py cleancli test_cleanmac.py tests' in makefile
    assert '"$$tmpdir/venv/bin/python" -m coverage run -m unittest -v' in makefile
    assert "PIP_NO_CACHE_DIR=1" in makefile
    assert '--cache-dir "$$mypy_cache"' in makefile
    assert "/tmp/cleanmac-mypy-cache-$$$$" in makefile
    assert 'coverage run --data-file "$$coverage_dir/.coverage"' in makefile
    assert (
        '"$$venv_python" -m coverage run --data-file "$$coverage_dir/.coverage" -a -m pytest tests/ -q -p no:cacheprovider'
        in makefile
    )
    assert "tests/test_ai_eval.py tests/test_mcp_server.py" in makefile
    assert "$(PYTHON) -m unittest tests.test_ai_eval tests.test_mcp_server" not in makefile
    assert "pip install --no-cache-dir" in makefile
    assert "[ ! -e .pytest_cache ] || /bin/rm -R .pytest_cache" in makefile
    assert "./scripts/test.sh" in makefile
    assert "pytest-test" in makefile
    assert "ai-governance-smoke" in makefile
    assert "$(PYTHON) -m build --wheel --sdist --outdir" in makefile
    assert "$(PYTHON) -m twine check" in makefile
    assert "-m pip install -e ." in makefile
    assert "-m build --wheel --sdist" in makefile
    assert "cleanmac-*.tar.gz" in makefile
    assert "wheel-capabilities.json" in makefile
    assert "sdist-capabilities.json" in makefile
    assert "python3 python3-venv make" in makefile
    assert "trap 'rm -rf" in makefile
    assert "capabilities.json" in makefile
    assert "template_validation" in makefile
    assert "cleanmac.command-template-validation.v1" in makefile
    assert "make docs-smoke" in makefile
    assert "make governance-smoke" in makefile
    assert "make governance-integrity-smoke" in makefile
    assert "make pytest-governance-smoke" in makefile
    assert "make ai-governance-smoke" in makefile
    assert "ai-contract-smoke" in makefile
    assert "make ai-robustness-smoke" in makefile
    assert "make release-readiness-smoke" in makefile
    assert "make open-source-smoke" in makefile
    assert "make dependency-audit-smoke" in makefile
    assert "make no-cache-check" in makefile
    assert "make no-cache-release-check" in makefile
    assert "CONTRIBUTING.md" in makefile
    assert "SECURITY.md" in makefile
    assert "CODE_OF_CONDUCT.md" in makefile
    assert ".github/PULL_REQUEST_TEMPLATE.md" in makefile
    assert ".gitleaks.toml" in makefile
    assert ".github/dependabot.yml" in makefile
    assert ".github/workflows/codeql.yml" in makefile
    assert ".github/workflows/release.yml" in makefile
    assert "SHA256SUMS" in makefile
    assert "SBOM.json" in makefile
    assert "pip-audit" in makefile
    assert "trash_routing_flag" in makefile
    assert "README.CN.md" in makefile
    assert "-m json.tool" in makefile


def test_makefile_release_check_dry_run_orders_quality_gates() -> None:
    if shutil.which("make") is None:
        pytest.skip("make is not installed in this validation environment")
    result = subprocess.run(
        ["make", "-n", "PYTHON=python3", "release-check"],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
    )
    output = result.stdout + result.stderr

    expected_fragments = [
        'python3 -m venv "$tmpdir/venv"',
        "\"$tmpdir/venv/bin/python\" -m pip install 'ruff>=0.8'",
        'RUFF_CACHE_DIR="$tmpdir/ruff-cache" "$tmpdir/venv/bin/python" -m ruff format --check .',
        'RUFF_CACHE_DIR="$tmpdir/ruff-cache" "$tmpdir/venv/bin/python" -m ruff check .',
        "\"$tmpdir/venv/bin/python\" -m pip install -e '.[dev]'",
        '"$tmpdir/venv/bin/python" -m mypy cleanmac.py cleancli test_cleanmac.py tests',
        "\"$tmpdir/venv/bin/python\" -m pip install -e '.[test]'",
        '"$tmpdir/venv/bin/python" -m coverage run -m unittest -v',
        '"$tmpdir/venv/bin/python" -m coverage run -a -m pytest tests/ -q',
        '"$tmpdir/venv/bin/python" -m coverage report',
        "PYTHON=python3 ./scripts/test.sh",
        '"$tmpdir/venv/bin/python" -m pytest tests/test_release_readiness.py tests/test_release_orchestration.py '
        "tests/test_release_artifacts.py tests/test_path_safety.py tests/test_trash_mode.py tests/test_delete_ops.py "
        "tests/test_security_scan.py -q",
        "python3 -m build --wheel --sdist --outdir",
        "python3 -m twine check",
        "-m pip install -e .",
        'cleanmac" --json capabilities',
        "-m json.tool",
        "template_validation",
        "pip_audit --skip-editable --progress-spinner off",
        "scripts/generate_sbom.py",
        "README.CN.md",
        'run("workflow",',
        "CONTRIBUTING.md",
        'build-venv/bin/python" -m build --wheel --sdist',
        "wheel-capabilities.json",
        "sdist-capabilities.json",
        "install-capabilities.json",
        "docker run --rm",
    ]
    assert "SHA256SUMS" in output
    cursor = -1
    for fragment in expected_fragments:
        index = output.find(fragment)
        assert index > cursor, fragment
        cursor = index


def test_makefile_no_cache_release_check_preserves_docker_isolation() -> None:
    makefile = (PROJECT_ROOT / "Makefile").read_text(encoding="utf-8")
    no_cache_check = makefile.split("\nno-cache-check:\n", 1)[1].split("\ndocker-test:\n", 1)[0]
    no_cache_release_check = makefile.split("\nno-cache-release-check:\n", 1)[1]

    no_cache_fragments = [
        "export PIP_NO_CACHE_DIR=1 PYTHONDONTWRITEBYTECODE=1 CLEANMAC_TEST_NO_AUTH=1",
        'CLEANMAC_TEST_MODE=1 PYTEST_ADDOPTS="-p no:cacheprovider"',
        '$(PYTHON) -m venv "$$tmpdir/venv"',
        '"$$venv_python" -m pip install --no-cache-dir --upgrade pip',
        "\"$$venv_python\" -m pip install --no-cache-dir -e '.[dev,build]'",
        'RUFF_CACHE_DIR="$$tmpdir/ruff-cache" "$$venv_python" -m ruff format --check .',
        'mypy --cache-dir "$$mypy_cache" cleanmac.py cleancli test_cleanmac.py tests',
        'coverage run --data-file "$$coverage_dir/.coverage" -m unittest -v',
        'coverage run --data-file "$$coverage_dir/.coverage" -a -m pytest tests/ -q -p no:cacheprovider',
        'coverage report --data-file "$$coverage_dir/.coverage"',
        "[ ! -e .pytest_cache ] || /bin/rm -R .pytest_cache",
        "[ ! -e .mypy_cache ] || /bin/rm -R .mypy_cache",
        "[ ! -e .ruff_cache ] || /bin/rm -R .ruff_cache",
    ]
    for fragment in no_cache_fragments:
        assert fragment in no_cache_check, fragment

    expected_release_fragments = [
        "PIP_NO_CACHE_DIR=1 $(MAKE) no-cache-check",
        "PIP_NO_CACHE_DIR=1 $(MAKE) distribution-smoke homebrew-formula-smoke release-artifacts-smoke",
        "release-readiness-contract-smoke release-readiness-smoke release-diagnostics-smoke",
        "release-post-publish-evidence-template-smoke no-cache-docker-test",
    ]
    cursor = -1
    for fragment in expected_release_fragments:
        index = no_cache_release_check.find(fragment, cursor + 1)
        assert index > cursor, fragment
        cursor = index

    if shutil.which("make") is None:
        pytest.skip("make is not installed in this validation environment")
    result = subprocess.run(
        ["make", "-n", "PYTHON=python3", "no-cache-docker-test"],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    output = result.stdout

    expected_fragments = [
        'DOCKER_RUN_FLAGS="--pull=always"',
        "docker run --rm",
        "--pull=always",
        '-v "',
        ':/work:ro"',
        '-w "/work/cleanmac"',
        "debian:bookworm-slim",
        "python3 -m venv /tmp/cleanmac-venv",
        '/tmp/cleanmac-venv/bin/python -m pip install -e ".[test]"',
        "PYTHONDONTWRITEBYTECODE=1 /tmp/cleanmac-venv/bin/python -m unittest -v",
    ]
    cursor = -1
    for fragment in expected_fragments:
        index = output.find(fragment, cursor + 1)
        assert index > cursor, fragment
        cursor = index

    assert ":/work:rw" not in output
    assert "pip install -e '.[dev,build]'" not in output
    assert "PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v" not in output


def test_makefile_pytest_targets_are_structured_and_ci_gated() -> None:
    makefile = (PROJECT_ROOT / "Makefile").read_text(encoding="utf-8")
    ci = (PROJECT_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

    def make_variable(name: str) -> list[str]:
        line = next(row for row in makefile.splitlines() if row.startswith(f"{name} :="))
        return line.split(":=", 1)[1].split()

    safe_targets = make_variable("PYTEST_SAFE_TARGETS")
    ai_host_targets = make_variable("PYTEST_AI_HOST_TARGETS")
    robustness_targets = make_variable("PYTEST_AI_ROBUSTNESS_TARGETS")

    assert len(safe_targets) >= 7
    assert len(ai_host_targets) >= 10
    assert len(robustness_targets) >= 15
    assert len(safe_targets) == len(set(safe_targets))
    assert len(ai_host_targets) == len(set(ai_host_targets))
    assert len(robustness_targets) == len(set(robustness_targets))
    for target in [*safe_targets, *ai_host_targets, *robustness_targets]:
        assert target.startswith("tests/test_"), target
        assert (PROJECT_ROOT / target).is_file(), target

    pytest_parity = makefile.split("\npytest-parity-test:\n", 1)[1].split("\npytest-ai-host-smoke:\n", 1)[0]
    pytest_ai_host = makefile.split("\npytest-ai-host-smoke:\n", 1)[1].split(
        "\npytest-no-unittest-regression-smoke:\n", 1
    )[0]
    ai_robustness = makefile.split("\nai-robustness-smoke:\n", 1)[1].split("\ndistribution-smoke:\n", 1)[0]

    assert '"$$tmpdir/venv/bin/python" -m pytest $(PYTEST_SAFE_TARGETS) -q' in pytest_parity
    assert '"$$tmpdir/venv/bin/python" -m pytest $(PYTEST_AI_HOST_TARGETS) -q' in pytest_ai_host
    assert '"$$tmpdir/venv/bin/python" -m pytest $(PYTEST_AI_ROBUSTNESS_TARGETS) -q' in ai_robustness
    assert 'PYTEST_ADDOPTS="-p no:cacheprovider"' in pytest_parity
    assert 'PYTEST_ADDOPTS="-p no:cacheprovider"' in pytest_ai_host
    assert 'PYTEST_ADDOPTS="-p no:cacheprovider"' in ai_robustness

    quality_job = ci.split("  quality:\n", 1)[1].split("\n  smoke:\n", 1)[0]
    assert "Run quality checks" in quality_job
    assert "run: make quality-check" in quality_job
    assert "Run pytest compatibility check" in quality_job
    assert "run: make pytest-test" in quality_job
    assert "python -m pytest tests -q" not in ci
    assert "python -m unittest tests.test_ai_" not in ci


def test_pytest_migrated_targets_keep_native_assertions_and_coverage_floor() -> None:
    makefile = (PROJECT_ROOT / "Makefile").read_text(encoding="utf-8")
    pyproject = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")

    target_lines = [
        row
        for row in makefile.splitlines()
        if row.startswith(("PYTEST_SAFE_TARGETS :=", "PYTEST_AI_HOST_TARGETS :=", "PYTEST_AI_ROBUSTNESS_TARGETS :="))
    ]
    migrated_targets = {
        target for line in target_lines for target in line.split(":=", 1)[1].split() if target.startswith("tests/test_")
    }

    assert "tests/test_mcp_server.py" in migrated_targets
    assert "tests/test_ai_eval.py" in migrated_targets
    assert "tests/test_release_readiness.py" in migrated_targets
    forbidden = ("import unittest", "unittest.TestCase", "unittest.main", "self.assert")
    for target in sorted(migrated_targets):
        text = (PROJECT_ROOT / target).read_text(encoding="utf-8")
        assert "def test_" in text, target
        for token in forbidden:
            assert token not in text, f"{target} still contains {token}"

    assert "[tool.coverage.run]" in pyproject
    assert 'source = ["cleancli", "cleanmac"]' in pyproject
    assert "[tool.coverage.report]" in pyproject
    fail_under_line = next(line for line in pyproject.splitlines() if line.startswith("fail_under = "))
    assert int(fail_under_line.split("=", 1)[1].strip()) >= 50


def test_pytest_governance_closeout_documents_remaining_unittest_backlog() -> None:
    closeout = (PROJECT_ROOT / "docs/superpowers/plans/2026-06-25-pytest-governance-cycle-closeout.md").read_text(
        encoding="utf-8"
    )
    next_rounds = (PROJECT_ROOT / "docs/superpowers/plans/2026-06-25-pytest-governance-next-20-rounds.md").read_text(
        encoding="utf-8"
    )
    rounds_118_137 = (PROJECT_ROOT / "docs/superpowers/plans/2026-06-26-pytest-governance-rounds-118-137.md").read_text(
        encoding="utf-8"
    )
    makefile = (PROJECT_ROOT / "Makefile").read_text(encoding="utf-8")
    scanned_files = [
        path
        for path in [PROJECT_ROOT / "test_cleanmac.py", *(PROJECT_ROOT / "tests").glob("test_*.py")]
        if path.is_file()
    ]
    unittest_backlog = [
        path.relative_to(PROJECT_ROOT).as_posix()
        for path in scanned_files
        if path.name != "test_makefile_governance.py"
        and any(
            token in path.read_text(encoding="utf-8") for token in ("unittest.TestCase", "self.assert", "unittest.main")
        )
    ]

    assert unittest_backlog == ["test_cleanmac.py"]
    assert "2026-06-25-pytest-governance-next-20-rounds.md" in closeout
    assert "2026-06-26-pytest-governance-rounds-118-137.md" in closeout
    assert "Round 38-57" in closeout
    assert "Round 118-137" in closeout
    assert next_rounds.count("- [x] Commit with `test(pytest):") == 20
    assert not [line for line in next_rounds.splitlines() if line.startswith("- [ ]")]
    assert rounds_118_137.count("- [x] Commit with `test(pytest):") == 20
    assert not [line for line in rounds_118_137.splitlines() if line.startswith("- [ ]")]
    assert "tests/test_open_source_governance.py" in closeout
    assert "`test_cleanmac.py` is the only intentional large unittest backlog" in closeout
    assert "`tests/test_makefile_governance.py` intentionally contains" in closeout
    assert "`tests/test_clean_execution.py`" in closeout
    assert "`tests/test_app_protection.py`" in closeout
    assert "`tests/test_software_governance.py`" in closeout
    assert "`tests/test_startup_governance.py`" in closeout
    assert "`tests/test_privacy_governance.py`" in closeout
    assert "make pytest-test" in closeout
    assert "make pytest-governance-smoke" in closeout
    assert "make ai-robustness-smoke" in closeout
    assert "Do not migrate `test_cleanmac.py` as one large rewrite" in closeout
    assert "Next backlog slices" in closeout
    assert "release workflow and distribution governance checks" in closeout
    assert "grouped command compatibility" in closeout
    assert ".harness/store.json" in closeout
    assert "PYTEST_SAFE_TARGETS" in makefile
    assert "PYTEST_AI_HOST_TARGETS" in closeout
    assert "PYTEST_AI_ROBUSTNESS_TARGETS" in closeout


def test_python_quality_tooling_is_configured() -> None:
    pyproject = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    precommit = (PROJECT_ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    ci = (PROJECT_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    makefile = (PROJECT_ROOT / "Makefile").read_text(encoding="utf-8")
    security_scan = (PROJECT_ROOT / "scripts/security_scan.py").read_text(encoding="utf-8")

    assert "[project.optional-dependencies]" in pyproject
    assert 'license = "MIT"' in pyproject
    assert "license = {text" not in pyproject
    assert "dev = [" in pyproject
    assert "ruff>=" in pyproject
    assert "mypy>=" in pyproject
    assert "pytest>=" in pyproject
    assert "pytest-cov>=" in pyproject
    assert "coverage[toml]>=" in pyproject
    assert "pip-audit>=" in pyproject
    assert "[tool.ruff]" in pyproject
    assert "[tool.mypy]" in pyproject
    assert "[tool.pytest.ini_options]" in pyproject
    assert "[tool.coverage.run]" in pyproject
    assert "[tool.coverage.report]" in pyproject

    assert "pre-commit-hooks" in precommit
    assert "ruff-pre-commit" in precommit
    assert "mirrors-mypy" in precommit

    assert "actions/setup-python@v6.2.0" in ci
    assert "actions/setup-python@a309ff8b426b58ec0e2a45f0f869d46889d02405" in ci
    assert "PYTHON: .venv/bin/python" in ci
    assert "Create venv and install dev dependencies" in ci
    assert "Create venv and install build dependencies" in ci
    assert "Create venv and install smoke dependencies" in ci
    assert "Create venv and install test dependencies" in ci
    assert "Create no-cache venv bootstrap" in ci
    assert 'python-version: ["3.10", "3.11", "3.12", "3.13"]' in ci
    assert "make quality-check" in ci
    assert "make local-test" in ci
    assert "Run pytest compatibility check" in ci
    assert "make pytest-test" in ci
    assert "make ai-robustness-smoke" in ci
    assert "make build-check" in ci
    assert "make package-smoke" in ci
    assert "make script-smoke" in ci
    assert "make docs-smoke" in ci
    assert "make governance-smoke" in ci
    assert "make open-source-smoke" in ci
    assert "make distribution-smoke" in ci
    assert "make dependency-audit-smoke" in ci
    assert "make docker-test" in ci
    assert "make no-cache-check" in ci
    assert "make no-cache-docker-test" in ci
    assert "Compatibility smoke" in ci
    assert "os: [macos-14, macos-15, ubuntu-latest]" in ci
    assert "CLEANMAC_TEST_NO_AUTH" in ci
    assert "macOS smoke for remap, Trash, plist, and bundle parsing" in ci
    assert "make macos-smoke" in ci
    assert "Ubuntu sandbox, governance JSON, and package build smoke" in ci
    assert "test_grouped_clean_commands_match_flat_alias_reports" in ci
    assert "Linux container smoke" in ci
    assert "Check unsafe delete patterns" in ci
    assert "make security-smoke" in ci
    assert "shutil.rmtree must stay in cleancli/delete_ops.py" in security_scan
    assert "subprocess must not directly invoke rm" in security_scan
    assert "shell must not invoke privileged command" in security_scan
    assert "workflow must not invoke privileged command" in security_scan
    assert "Scan for secrets (gitleaks)" in ci
    assert "gitleaks/gitleaks-action" in ci
    assert "No-cache dependency install" in ci
    assert "no-cache-check:" in makefile
    assert "set -e" in makefile
    assert "--no-cache-dir" in makefile
    assert 'PYTEST_ADDOPTS="-p no:cacheprovider"' in makefile
    fail_under_line = next(line for line in pyproject.splitlines() if line.startswith("fail_under = "))
    assert int(fail_under_line.split("=", 1)[1].strip()) >= 50
    assert "actions/cache@2c8a9bd7457de244a408f35966fab2fb45fda9c8 # pinned from actions/cache@v6.0.0" in ci
