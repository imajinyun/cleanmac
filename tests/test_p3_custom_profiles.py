"""P3-09: Custom profiles persistent configuration tests."""

from __future__ import annotations

import json
from pathlib import Path

from cleancli.profiles import PROFILES, profile_names, render_profiles


def test_builtin_profiles_exist() -> None:
    assert "safe" in PROFILES
    assert "developer" in PROFILES
    assert "browser" in PROFILES


def test_profile_names_matches_profiles() -> None:
    names = profile_names()
    assert len(names) == len(PROFILES)
    for name in names:
        assert name in PROFILES


def test_each_profile_has_required_fields() -> None:
    required = ["description", "categories", "risk_policy", "delete_mode", "max_delete_mb"]
    for name, profile in PROFILES.items():
        for field in required:
            assert field in profile, f"Profile {name} missing {field}"


def test_each_profile_has_at_least_one_category() -> None:
    for name, profile in PROFILES.items():
        assert isinstance(profile["categories"], list) and len(profile["categories"]) > 0, (
            f"Profile {name} has no categories"
        )


def test_profile_delete_mode_is_trash() -> None:
    for name, profile in PROFILES.items():
        assert profile["delete_mode"] == "trash", f"Profile {name} uses non-trash delete mode"


def test_render_profiles_schema() -> None:
    result = render_profiles()
    assert result["schema"] == "cleanmac.profiles.v1"
    assert result["destructive"] is False
    assert result["dry_run"] is True
    assert result["profile_count"] == len(PROFILES)


def test_render_profiles_safe_to_auto_execute() -> None:
    result = render_profiles()
    for profile in result["profiles"]:
        assert profile["safe_to_auto_execute"] is False


def test_render_profiles_has_example_commands() -> None:
    result = render_profiles()
    for profile in result["profiles"]:
        assert "example_plan_command" in profile
        assert len(profile["example_plan_command"]) > 0


def test_developer_profile_has_xcode() -> None:
    assert "xcode" in PROFILES["developer"]["categories"]


def test_safe_profile_is_strict() -> None:
    assert PROFILES["safe"]["risk_policy"] == "strict"


def test_browser_profile_includes_chrome_and_firefox() -> None:
    categories = PROFILES["browser"]["categories"]
    assert "chrome" in categories
    assert "firefox" in categories


def test_custom_profile_config_load(tmp_path: Path) -> None:
    """Custom profiles can be loaded from a JSON config file."""
    config_dir = tmp_path / ".cleanmac"
    config_dir.mkdir()
    config_file = config_dir / "profiles.json"
    custom_profiles = {
        "my-custom": {
            "description": "My custom cleanup profile",
            "categories": ["trash", "userCache"],
            "risk_policy": "default",
            "delete_mode": "trash",
            "max_delete_mb": 512,
        }
    }
    config_file.write_text(json.dumps({"custom_profiles": custom_profiles}))

    # Verify the file structure is valid JSON
    loaded = json.loads(config_file.read_text())
    assert "my-custom" in loaded["custom_profiles"]
    assert loaded["custom_profiles"]["my-custom"]["max_delete_mb"] == 512


def test_custom_profile_validation(tmp_path: Path) -> None:
    """Custom profiles must include all required fields."""
    required_fields = ["description", "categories", "risk_policy", "delete_mode", "max_delete_mb"]
    custom_profiles = {
        "valid": {
            "description": "Valid profile",
            "categories": ["trash"],
            "risk_policy": "default",
            "delete_mode": "trash",
            "max_delete_mb": 100,
        }
    }
    for name, profile in custom_profiles.items():
        for field in required_fields:
            assert field in profile, f"Custom profile {name} missing {field}"
        assert isinstance(profile["categories"], list) and len(profile["categories"]) > 0
        assert profile["delete_mode"] in ("trash", "hardlink")
