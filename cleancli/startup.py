"""Read-only startup item audit and disable planning."""

from __future__ import annotations

import plistlib
from pathlib import Path
from typing import Any

from cleancli import protection


def _display_path(path: Path | str) -> str:
    return str(path)


def _home_root(root: Path, home: Path) -> Path:
    return root / str(home).lstrip("/") if root != Path("/") else home


def _system_path(root: Path, path: str) -> Path:
    return root / path.lstrip("/") if root != Path("/") else Path(path)


def _path_size(path: Path) -> int:
    try:
        if not path.exists() and not path.is_symlink():
            return 0
        if path.is_file() or path.is_symlink():
            return path.lstat().st_size
        return sum(child.lstat().st_size for child in path.rglob("*") if child.exists() or child.is_symlink())
    except OSError:
        return 0


def _load_plist(path: Path) -> dict[str, Any]:
    try:
        with path.open("rb") as handle:
            payload = plistlib.load(handle)
        return payload if isinstance(payload, dict) else {}
    except (OSError, plistlib.InvalidFileException, ValueError):
        return {}


def _startup_locations(root: Path, home: Path) -> list[tuple[str, Path, bool]]:
    home_root = _home_root(root, home)
    return [
        ("user-launch-agent", home_root / "Library/LaunchAgents", False),
        ("system-launch-agent", _system_path(root, "/Library/LaunchAgents"), True),
        ("system-launch-daemon", _system_path(root, "/Library/LaunchDaemons"), True),
        ("user-startup-item", home_root / "Library/StartupItems", False),
        ("system-startup-item", _system_path(root, "/Library/StartupItems"), True),
    ]


def _count_by(items: list[dict[str, Any]], field: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        key = str(item.get(field) or "unknown")
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def _item_from_plist(path: Path, *, kind: str, requires_privilege: bool) -> dict[str, Any]:
    plist = _load_plist(path)
    label = str(plist.get("Label") or path.stem)
    disabled = bool(plist.get("Disabled") is True)
    run_at_load = bool(plist.get("RunAtLoad") is True)
    keep_alive = bool(plist.get("KeepAlive") not in (None, False))
    program = plist.get("Program") or plist.get("ProgramArguments") or []
    if isinstance(program, list):
        program_display = [str(part) for part in program]
    else:
        program_display = [str(program)] if program else []
    protected = label.startswith("com.apple.") or protection.should_protect_path(path)
    if protected:
        risk = "critical"
        recommendation = "preserve"
    elif disabled:
        risk = "low"
        recommendation = "already-disabled"
    elif kind == "system-launch-daemon" or requires_privilege:
        risk = "high"
        recommendation = "review-disable"
    elif run_at_load or keep_alive:
        risk = "medium"
        recommendation = "review-disable"
    else:
        risk = "low"
        recommendation = "leave-enabled"
    return {
        "id": f"startup:{kind}:{label}:{_display_path(path)}",
        "path": _display_path(path),
        "kind": kind,
        "label": label,
        "program": program_display,
        "run_at_load": run_at_load,
        "keep_alive": keep_alive,
        "disabled": disabled,
        "requires_privilege": requires_privilege,
        "bytes": _path_size(path),
        "risk": risk,
        "protected": protected,
        "recommendation": recommendation,
        "default_selected": recommendation == "review-disable" and not requires_privilege and not protected,
        "disable_method": "launchctl bootout/disable or move plist after explicit governed execution",
    }


def _item_from_directory(path: Path, *, kind: str, requires_privilege: bool) -> dict[str, Any]:
    protected = protection.should_protect_path(path)
    recommendation = "preserve" if protected else "review-disable"
    return {
        "id": f"startup:{kind}:{path.name}:{_display_path(path)}",
        "path": _display_path(path),
        "kind": kind,
        "label": path.name,
        "program": [],
        "run_at_load": True,
        "keep_alive": False,
        "disabled": False,
        "requires_privilege": requires_privilege,
        "bytes": _path_size(path),
        "risk": "high" if requires_privilege else "medium",
        "protected": protected,
        "recommendation": recommendation,
        "default_selected": recommendation == "review-disable" and not requires_privilege,
        "disable_method": "move StartupItems entry after explicit governed execution",
    }


def audit_startup(*, root: Path, home: Path) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    scanned_locations: list[str] = []
    for kind, location, requires_privilege in _startup_locations(root, home):
        scanned_locations.append(_display_path(location))
        if not location.exists():
            continue
        if "launch" in kind:
            entries = sorted(location.glob("*.plist"))
            items.extend(_item_from_plist(path, kind=kind, requires_privilege=requires_privilege) for path in entries)
        else:
            entries = sorted(path for path in location.iterdir() if path.exists() or path.is_symlink())
            items.extend(
                _item_from_directory(path, kind=kind, requires_privilege=requires_privilege) for path in entries
            )
    risk_counts = _count_by(items, "risk")
    recommendation_counts = _count_by(items, "recommendation")
    kind_counts = _count_by(items, "kind")
    return {
        "schema": "cleanmac.startup-audit.v1",
        "destructive": False,
        "dry_run": True,
        "root": _display_path(root),
        "home": _display_path(home),
        "scanned_locations": scanned_locations,
        "item_count": len(items),
        "items": items,
        "requires_privilege_count": sum(1 for item in items if item["requires_privilege"]),
        "review_disable_count": sum(1 for item in items if item["recommendation"] == "review-disable"),
        "risk_counts": risk_counts,
        "recommendation_counts": recommendation_counts,
        "kind_counts": kind_counts,
        "recommended_next_action": "review_disable_plan"
        if recommendation_counts.get("review-disable", 0)
        else "no_action_needed",
    }


def plan_startup(*, root: Path, home: Path) -> dict[str, Any]:
    audit = audit_startup(root=root, home=home)
    candidates = [item for item in audit["items"] if item["recommendation"] == "review-disable"]
    risk_counts = _count_by(candidates, "risk")
    kind_counts = _count_by(candidates, "kind")
    return {
        "schema": "cleanmac.startup-plan.v1",
        "destructive": False,
        "dry_run": True,
        "root": _display_path(root),
        "home": _display_path(home),
        "valid": True,
        "blocked_reasons": [],
        "source_audit_item_count": audit["item_count"],
        "disable_plan": {
            "requires_explicit_future_execute": True,
            "safe_to_auto_execute": False,
            "candidate_count": len(candidates),
            "default_selected_count": sum(1 for item in candidates if item["default_selected"]),
            "requires_privilege_count": sum(1 for item in candidates if item["requires_privilege"]),
            "risk_counts": risk_counts,
            "kind_counts": kind_counts,
            "candidates": candidates,
            "preserve_recommendations": [
                item for item in audit["items"] if item["recommendation"] in {"preserve", "already-disabled"}
            ],
        },
    }


def render_startup(action: str, *, root: Path, home: Path) -> dict[str, Any]:
    if action == "plan":
        return plan_startup(root=root, home=home)
    return audit_startup(root=root, home=home)
