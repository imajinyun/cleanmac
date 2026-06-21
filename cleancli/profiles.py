"""Built-in cleanup profiles for safer CLI onboarding."""

from __future__ import annotations

from typing import Any

PROFILES: dict[str, dict[str, Any]] = {
    "safe": {
        "description": "Conservative everyday cleanup for ordinary user-facing caches, logs, downloads, and Trash.",
        "categories": ["trash", "downloads", "userCache", "userLogs"],
        "risk_policy": "strict",
        "delete_mode": "trash",
        "max_delete_mb": 1024,
    },
    "developer": {
        "description": "Developer cache cleanup for Xcode and language package/build caches.",
        "categories": ["xcode", "nodePackageCaches", "pythonPackageCaches", "goBuildCaches"],
        "risk_policy": "default",
        "delete_mode": "trash",
        "max_delete_mb": 4096,
    },
    "browser": {
        "description": "Browser cache cleanup that avoids credentials and protected profile data.",
        "categories": ["chrome", "firefox"],
        "risk_policy": "strict",
        "delete_mode": "trash",
        "max_delete_mb": 2048,
    },
}


def render_profiles() -> dict[str, Any]:
    return {
        "schema": "cleanmac.profiles.v1",
        "destructive": False,
        "dry_run": True,
        "profile_count": len(PROFILES),
        "profiles": [
            {
                "name": name,
                "description": str(profile["description"]),
                "categories": list(profile["categories"]),
                "risk_policy": str(profile["risk_policy"]),
                "delete_mode": str(profile["delete_mode"]),
                "max_delete_mb": int(profile["max_delete_mb"]),
                "safe_to_auto_execute": False,
                "example_plan_command": ["cleanmac", "--json", "clean", "plan", "--profile", name],
            }
            for name, profile in PROFILES.items()
        ],
    }


def profile_names() -> tuple[str, ...]:
    return tuple(PROFILES)
