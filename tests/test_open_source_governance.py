from __future__ import annotations

import re

from tests.helpers import PROJECT_ROOT


def test_open_source_governance_files_are_configured() -> None:
    required_files = [
        "LICENSE",
        "CONTRIBUTING.md",
        "SECURITY.md",
        "CODE_OF_CONDUCT.md",
        "AGENTS.md",
        ".gitleaks.toml",
        ".github/PULL_REQUEST_TEMPLATE.md",
        ".github/dependabot.yml",
        ".github/workflows/ci.yml",
        ".github/workflows/bundle_audit.yml",
        ".github/workflows/codeql.yml",
        ".github/workflows/dependency-review.yml",
        ".github/workflows/nightly.yml",
        ".github/workflows/release.yml",
        ".github/workflows/scorecards.yml",
        ".github/ISSUE_TEMPLATE/bug_report.yml",
        ".github/ISSUE_TEMPLATE/feature_request.yml",
        ".github/ISSUE_TEMPLATE/config.yml",
        "scripts/generate_sbom.py",
    ]

    for relative_path in required_files:
        assert (PROJECT_ROOT / relative_path).is_file(), relative_path
    assert not (PROJECT_ROOT / ".github/templates").exists()
    assert not (PROJECT_ROOT / ".github/CODEOWNERS").exists()


def test_open_source_security_and_ci_governance_are_pinned() -> None:
    license_text = (PROJECT_ROOT / "LICENSE").read_text(encoding="utf-8")
    contributing = (PROJECT_ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
    security = (PROJECT_ROOT / "SECURITY.md").read_text(encoding="utf-8")
    codeql = (PROJECT_ROOT / ".github/workflows/codeql.yml").read_text(encoding="utf-8")
    dependency_review = (PROJECT_ROOT / ".github/workflows/dependency-review.yml").read_text(encoding="utf-8")
    nightly = (PROJECT_ROOT / ".github/workflows/nightly.yml").read_text(encoding="utf-8")
    scorecards = (PROJECT_ROOT / ".github/workflows/scorecards.yml").read_text(encoding="utf-8")
    dependabot = (PROJECT_ROOT / ".github/dependabot.yml").read_text(encoding="utf-8")
    gitleaks = (PROJECT_ROOT / ".gitleaks.toml").read_text(encoding="utf-8")

    assert "MIT License" in license_text
    assert "make open-source-smoke" in contributing
    assert "path traversal" in security.lower()
    assert "github/codeql-action/init@v3" in codeql
    assert "actions/dependency-review-action" in dependency_review
    assert "fail-on-severity: high" in dependency_review
    assert "make release-check" in nightly
    assert "make no-cache-check" in nightly
    assert "PYTHON: .venv/bin/python" in nightly
    assert "Create venv and install release-check dependencies" in nightly
    assert "$PYTHON -m pip install -e '.[dev,build]'" in nightly
    assert "ossf/scorecard-action" in scorecards
    assert "results_format: sarif" in scorecards
    assert "github/codeql-action/upload-sarif" in scorecards
    assert "package-ecosystem: github-actions" in dependabot
    assert "useDefault = true" in gitleaks
    assert "README\\.md" not in gitleaks
    assert "README\\.CN" not in gitleaks

    uses_lines = []
    for workflow in (PROJECT_ROOT / ".github/workflows").glob("*.yml"):
        uses_lines.extend(
            line.strip()
            for line in workflow.read_text(encoding="utf-8").splitlines()
            if line.strip().startswith("uses: ")
        )

    assert uses_lines
    for line in uses_lines:
        assert re.search(r"@[0-9a-f]{40}(?:\s|$)", line), line


def test_readme_and_agent_guide_preserve_ai_first_zero_resident_positioning() -> None:
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    readme_cn = (PROJECT_ROOT / "README.CN.md").read_text(encoding="utf-8")
    agents = (PROJECT_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    local_developer_path = "/" + "Users" + "/" + "bytedance"

    for expected in (
        "Dry-run first",
        "MCP Server",
        "AI-first macOS cleanup CLI",
        "AI discovery summary",
        "AI-first, zero-resident macOS cleanup CLI",
        "MCP-ready execution kernel",
        "What AI agents should know",
        "Recommended GitHub topics for discoverability",
        "model-context-protocol",
        "Common questions cleanmac should answer",
        "Zero-resident by design",
        "no resident GUI, TUI, menu bar process",
    ):
        assert expected in readme

    for expected in (
        "AI-first macOS 清理 CLI",
        "零常驻的 macOS 清理 CLI",
        "AI Agent 应该如何理解 cleanmac",
        "model-context-protocol",
        "设计上零常驻",
        "不提供常驻 GUI、TUI、菜单栏进程",
    ):
        assert expected in readme_cn

    assert local_developer_path not in readme
    assert local_developer_path not in readme_cn

    for expected in (
        "cleancli/delete_ops.py",
        "AI-first, single-shot Python CLI",
        "## 🤖 Agent Summary for GEO and AI Search",
        "AI-first, zero-resident macOS cleanup CLI",
        "Do not describe cleanmac as a GUI cleaner",
        "background daemon",
        "## 🚧 Product Boundary Red Lines",
        "launchctl",
        "tests/data/dangerous_paths.txt",
        "## 🗺️ Project Map",
        "## ⚙️ Common Commands",
        "## 🛡️ Critical Safety Rules",
        "## 🧪 High-Risk Module Ownership and Required Tests",
        "## 🧭 Historical Incidents and Pitfalls",
        "cleancli/protection_data.py",
        "cleancli/protection.py",
        "cleancli/scripts.py",
        "cleancli/governance.py",
        "Symlink to a system path",
        "Group Container wildcard",
        "Trash fail-closed",
        "sudo prompt",
        "Plan replay root/home mismatch",
        "Operation log not writable",
        "Shell template unsafe auto execution",
        "temporary venv",
        "All documentation optimizations must be written in English by default",
    ):
        assert expected in agents


def test_pyproject_exposes_open_source_ai_first_metadata() -> None:
    pyproject = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert 'license-files = ["LICENSE"]' in pyproject
    assert "AI-first zero-resident macOS cleanup CLI" in pyproject
    assert '"ai-first"' in pyproject
    assert '"model-context-protocol"' in pyproject
    assert '"zero-resident"' in pyproject
    assert '"agent-tools"' in pyproject
    assert "[project.urls]" in pyproject
    assert "Security =" in pyproject
    assert "pip-audit>=" in pyproject


def test_distribution_release_governance_files_are_pinned() -> None:
    release = (PROJECT_ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")
    manifest_script = (PROJECT_ROOT / "scripts/generate_release_manifest.py").read_text(encoding="utf-8")
    homebrew_script = (PROJECT_ROOT / "scripts/generate_homebrew_formula.py").read_text(encoding="utf-8")

    assert "Generate release manifest and SHA256SUMS" in release
    assert "scripts/generate_sbom.py --output release-assets/SBOM.json" in release
    assert "scripts/generate_homebrew_formula.py" in release
    assert "scripts/generate_release_manifest.py --dist-dir dist --assets-dir release-assets" in release
    assert "cleanmac.release-artifact-manifest.v1" in release
    assert "Verify governed release evidence" in release
    assert "needs: verify-release-artifacts" in release
    assert "attest-build-provenance" in release
    assert "pypa/gh-action-pypi-publish" in release
    assert "id-token: write" in release
    assert "attestations: write" in release
    for artifact in (
        "release-assets/SBOM.json",
        "release-assets/SHA256SUMS",
        "release-assets/ARTIFACT-MANIFEST.json",
        "release-assets/RELEASE-EVIDENCE.json",
        "release-assets/RELEASE-PROMOTION-DECISION.json",
        "release-assets/RELEASE-ROLLBACK-PLAN.json",
        "release-assets/cleanmac.rb",
    ):
        assert artifact in release

    assert "write_release_artifact_outputs" in manifest_script
    assert "write_release_evidence_bundle_output" in manifest_script
    assert "RELEASE-POST-PUBLISH-EVIDENCE.example.json" in manifest_script
    assert "render_homebrew_formula" in homebrew_script
    assert "github.com/cleanmac/cleanmac/archive/refs/tags" in homebrew_script


def test_project_files_do_not_contain_removed_product_references() -> None:
    forbidden = ("clean" + "me", "Clean" + " Me", "clean" + " me", "mo" + "le", "MO" + "LE")
    local_developer_path = "/" + "users" + "/" + "bytedance"
    scanned = [
        PROJECT_ROOT / "cleanmac.py",
        PROJECT_ROOT / "test_cleanmac.py",
        PROJECT_ROOT / "README.md",
        PROJECT_ROOT / "README.CN.md",
        PROJECT_ROOT / "Makefile",
        PROJECT_ROOT / ".github/workflows/ci.yml",
    ]

    for path in scanned:
        content = path.read_text(encoding="utf-8")
        lowered = content.lower()
        for token in forbidden:
            assert token.lower() not in lowered, path.name
        assert local_developer_path not in lowered, path.name
