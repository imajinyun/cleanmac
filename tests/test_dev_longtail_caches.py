"""Developer long-tail tool cache categories (Mole clean_dev_* parity).

Covers exact regenerable cache leaves for other language toolchains
(Composer/Bazel/Zig/Hex/opam), CI/CD tools (Terraform/Grafana/GitLab
Runner/GitHub Actions/CircleCI/SonarQube), and developer utilities
(Prisma/Oh My Zsh/curl/wget), plus uv under pythonPackageCaches and
OpenCode under aiToolCaches. Credentials, configuration, installed
toolchains, and Jenkins workspaces must never become candidates.
"""

from __future__ import annotations

import json
from pathlib import Path

from cleancli.protection_data import APP_CLEANUP_RULES
from tests.helpers import make_sandbox, run_cli

CATEGORIES = "otherLanguageCaches,ciCdCaches,devUtilityCaches,pythonPackageCaches,aiToolCaches"

# Cache leaf (a file inside a declared cache root) -> category that owns it.
CACHE_FIXTURES: dict[str, str] = {
    # otherLanguageCaches
    ".composer/cache/repo/entry": "otherLanguageCaches",
    "Library/Caches/composer/repo/entry": "otherLanguageCaches",
    ".cache/bazel/_bazel/user/action/entry": "otherLanguageCaches",
    ".cache/zig/zig-cache/o/x.o": "otherLanguageCaches",
    ".hex/cache/repo/entry": "otherLanguageCaches",
    ".opam/download-cache/mirror/pkg": "otherLanguageCaches",
    # ciCdCaches
    ".cache/terraform/registry/file": "ciCdCaches",
    ".grafana/cache/plugins/file": "ciCdCaches",
    ".cache/gitlab-runner/cache/key/archive": "ciCdCaches",
    ".github/cache/oidc/blob": "ciCdCaches",
    ".circleci/cache/key/archive": "ciCdCaches",
    ".sonar/cache/key/file": "ciCdCaches",
    # devUtilityCaches
    ".cache/prisma/engines/engine-bin": "devUtilityCaches",
    ".oh-my-zsh/cache/completions/_git": "devUtilityCaches",
    ".cache/curl/http.bin": "devUtilityCaches",
    ".cache/wget/http.bin": "devUtilityCaches",
    "Library/Caches/curl/http.bin": "devUtilityCaches",
    "Library/Caches/wget/http.bin": "devUtilityCaches",
    # uv rides with the other Python package-manager caches (both locations).
    "Library/Caches/uv/built-wheels/wheel": "pythonPackageCaches",
    ".cache/uv/built-wheels/wheel": "pythonPackageCaches",
    # OpenCode rides with the other AI tool caches.
    ".cache/opencode/downloads/blob": "aiToolCaches",
}

# Sibling state, credentials, and spoof paths that must never be candidates.
PROTECTED_FIXTURES = (
    ".composer/auth.json",
    ".config/composer/auth.json",
    ".opam/config",
    ".opam/5.2.0/bin/opam",
    ".bazelrc",
    ".terraformrc",
    ".terraform.d/credentials.tfrc.json",
    ".circleci/cli.yml",
    ".grafana/grafana.ini",
    ".zshrc",
    ".config/opencode/opencode.json",
    ".local/share/opencode/storage/session.jsonl",
    # Exact-leaf discipline: a similar name is not the declared cache root.
    ".composer/cache-evil/entry",
    ".cache/opencode-evil/entry",
    ".hex/cache2/entry",
    # Jenkins workspaces are active CI checkouts, never a redundant cache.
    ".jenkins/workspace/job/target/classes/A.class",
)


def _inspect(root: Path, home: Path) -> list[dict[str, object]]:
    result = run_cli(
        "--root",
        str(root),
        "--home",
        str(home),
        "--json",
        "clean",
        "inspect",
        "--categories",
        CATEGORIES,
    )
    report = json.loads(result.stdout)
    items = report["items"]
    assert isinstance(items, list)
    return [row for row in items if isinstance(row, dict)]


def _write(root: Path, relative: str) -> Path:
    path = root / "Users/tester" / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("x", encoding="utf-8")
    return path


def test_cache_leaves_are_discovered_and_default_selected() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        expected_by_category: dict[str, set[str]] = {}
        for relative, category in CACHE_FIXTURES.items():
            _write(root, relative)
            # Candidates surface as the child directory directly under the
            # declared cache root, not the fixture file itself.
            expected_by_category.setdefault(category, set())

        rows = _inspect(root, home)
        rows_by_category: dict[str, list[dict[str, object]]] = {}
        for row in rows:
            category = str(row["category"])
            rows_by_category.setdefault(category, []).append(row)
            assert row["default_selected"] is True
            assert row.get("skip_reason") is None

        assert set(rows_by_category) == set(expected_by_category)
        for category in expected_by_category:
            assert rows_by_category[category], f"no candidates for {category}"


def test_each_cache_fixture_is_reachable_from_its_owning_category() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        for relative in CACHE_FIXTURES:
            _write(root, relative)
        rows = _inspect(root, home)
        user_root = str(root / "Users/tester")
        row_paths_by_category: dict[str, list[str]] = {}
        for row in rows:
            row_paths_by_category.setdefault(str(row["category"]), []).append(str(row["path"]))

        for relative, category in CACHE_FIXTURES.items():
            # Candidates are the cache root's direct children, so every fixture
            # file must be a descendant of one of its owning category's rows.
            fixture_abs = f"{user_root}/{relative}"
            owning_paths = row_paths_by_category.get(category, [])
            assert any(
                fixture_abs == candidate_path or fixture_abs.startswith(candidate_path + "/")
                for candidate_path in owning_paths
            ), f"{relative} not reachable from {category} candidates {owning_paths}"


def test_credentials_state_and_jenkins_workspaces_never_become_candidates() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        protected = [_write(root, relative) for relative in PROTECTED_FIXTURES]
        # One benign cache leaf per category so inspection actually scans.
        _write(root, ".composer/cache/repo/entry")
        _write(root, ".cache/terraform/registry/file")
        _write(root, ".cache/prisma/engines/engine-bin")

        rows = _inspect(root, home)
        candidate_paths = {str(row["path"]) for row in rows}
        for path in protected:
            assert not any(
                candidate == str(path) or str(path).startswith(candidate + "/")
                for candidate in candidate_paths
            ), f"protected path became a candidate or descendant: {path}"


def test_new_rules_target_exact_leaves_with_wildcard_home_dotdirs() -> None:
    for key in ("otherLanguageCaches", "ciCdCaches", "devUtilityCaches"):
        rule = APP_CLEANUP_RULES[key]
        paths = rule["paths"]
        assert paths and all(path.startswith("~/") for path in paths)
        # Rules must name exact cache directories, never broad dotdir roots.
        forbidden_roots = {
            "~/.composer/",
            "~/.opam/",
            "~/.hex/",
            "~/.sonar/",
            "~/.grafana/",
            "~/.circleci/",
            "~/.github/",
            "~/.oh-my-zsh/",
            "~/.cache/",
        }
        assert not forbidden_roots.intersection(paths)
        assert rule["protected_patterns"]


def test_jenkins_is_not_part_of_any_dev_cache_rule() -> None:
    joined = " ".join(
        path
        for rule in APP_CLEANUP_RULES.values()
        for path in rule.get("paths", ())
    ).lower()
    assert "jenkins" not in joined


def test_rules_are_registered_as_advanced_medium_risk_categories() -> None:
    from cleancli.core import CATEGORY_BY_KEY

    for key in ("otherLanguageCaches", "ciCdCaches", "devUtilityCaches"):
        category = CATEGORY_BY_KEY[key]
        assert category.advanced is True
        assert category.risk == "medium"
        assert category.default is False
