"""Single safety exit for destructive cleanup operations.

This module owns the only code paths that perform real deletion or Trash
routing for cleanup candidates. Callers provide project-specific policy
callbacks so the low-level safety gate stays reusable and testable without
importing the main CLI module.
"""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BLOCKED_TEST_COMMANDS = {"sudo", "osascript", "launchctl"}
SUDO_REMOVE_COMMAND = ("sudo", "-n", "rm", "-rf")


def combined_non_removable_file_flags() -> int:
    flags = 0
    for name in (
        "UF_IMMUTABLE",
        "UF_APPEND",
        "UF_NOUNLINK",
        "UF_DATAVAULT",
        "SF_IMMUTABLE",
        "SF_APPEND",
        "SF_NOUNLINK",
        "SF_RESTRICTED",
    ):
        flags |= getattr(stat, name, 0)
    return flags


NON_REMOVABLE_FILE_FLAGS = combined_non_removable_file_flags()


@dataclass(frozen=True)
class DeletePolicy:
    root: Path
    home_root: Path
    critical_path: Callable[[Path], bool]
    private_allowlist: Callable[[Path], bool]
    protected_user_data: Callable[[Path], bool]
    normalize_policy_path: Callable[[Path], str]


OperationLogHook = Callable[[str, Path, str], Any]


class TrashRemovabilityError(PermissionError):
    pass


def require_trash_first_delete_mode(
    delete_mode: str,
    *,
    surface: str,
    non_trashable: bool = False,
    explicit_non_trash_gate: bool = False,
) -> None:
    if delete_mode == "trash":
        return
    if non_trashable and explicit_non_trash_gate:
        return
    raise RuntimeError(
        f"{surface} destructive execution requires --delete-mode trash; "
        "non-Trash deletion requires an explicit non-trashable-object gate."
    )


def is_test_mode() -> bool:
    return os.environ.get("CLEANMAC_TEST_MODE") == "1"


def is_test_no_auth() -> bool:
    return is_test_mode() or os.environ.get("CLEANMAC_TEST_NO_AUTH") == "1"


def run_text_command(argv: Sequence[str], *, timeout: float = 2) -> str | None:
    if is_test_no_auth() and argv and Path(argv[0]).name in BLOCKED_TEST_COMMANDS:
        return None
    try:
        result = subprocess.run(
            list(argv),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def is_relative_to(path: Path, base: Path) -> bool:
    try:
        path.relative_to(base)
        return True
    except ValueError:
        return False


def has_path_traversal(path: Path) -> bool:
    return any(part == ".." for part in path.parts)


def has_control_characters(path: Path) -> bool:
    text = str(path)
    return any(ord(char) < 32 or ord(char) == 127 for char in text)


def coerce_deletion_path(path: str | os.PathLike[str]) -> Path:
    text = os.fspath(path)
    if text == "":
        raise RuntimeError("Refusing to delete empty path")
    return Path(text)


def policy_path_for_resolved(resolved: Path, *, policy: DeletePolicy) -> Path:
    root_resolved = policy.root.resolve(strict=False)
    if policy.root == Path("/"):
        return resolved
    return Path("/") / resolved.relative_to(root_resolved)


def validate_deletion_path(target: str | os.PathLike[str], *, policy: DeletePolicy) -> Path:
    target = coerce_deletion_path(target)
    if not target.is_absolute():
        raise RuntimeError(f"Refusing to delete non-absolute path: {target}")
    if has_path_traversal(target):
        raise RuntimeError(f"Refusing to delete path with traversal component: {target}")
    if has_control_characters(target):
        raise RuntimeError(f"Refusing to delete path with control characters: {target}")

    resolved = target.resolve(strict=False)
    root_resolved = policy.root.resolve(strict=False)
    home_resolved = policy.home_root.resolve(strict=False)
    blocked = {
        Path("/").resolve(strict=False),
        root_resolved,
        home_resolved,
        root_resolved / "Users",
        root_resolved / "Library",
        root_resolved / "var",
        root_resolved / "private",
    }
    if resolved in blocked:
        raise RuntimeError(f"Refusing to delete unsafe top-level path: {target}")
    if policy.root != Path("/") and not is_relative_to(resolved, root_resolved):
        raise RuntimeError(f"Refusing to delete path outside sandbox root {policy.root}: {target}")

    policy_path = policy_path_for_resolved(resolved, policy=policy)
    if target.is_symlink():
        try:
            link_target = target.resolve(strict=False)
        except OSError as exc:
            raise RuntimeError(f"Refusing to delete unreadable symlink: {target}") from exc
        link_policy_path = (
            link_target
            if policy.root == Path("/")
            else Path("/") / link_target.relative_to(root_resolved)
            if is_relative_to(link_target, root_resolved)
            else link_target
        )
        if policy.critical_path(link_policy_path) or policy.protected_user_data(link_policy_path):
            raise RuntimeError(f"Refusing to delete symlink pointing to protected path: {target} -> {link_policy_path}")

    if policy.critical_path(policy_path) and not policy.private_allowlist(policy_path):
        raise RuntimeError(f"Refusing to delete protected system path: {target}")
    if policy.normalize_policy_path(policy_path).startswith("/private/") and not policy.private_allowlist(policy_path):
        raise RuntimeError(f"Refusing to delete non-allowlisted /private path: {target}")
    if policy.protected_user_data(policy_path):
        raise RuntimeError(f"Refusing to delete protected user data path: {target}")
    return target


def assert_safe_to_delete(target: str | os.PathLike[str], *, policy: DeletePolicy) -> None:
    validate_deletion_path(target, policy=policy)


def remove_path_permanently(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink(missing_ok=True)
    elif path.is_dir():
        shutil.rmtree(path)


def unique_trash_path(path: Path, *, trash_root: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    base_name = f"cleanmac-{stamp}-{path.name}"
    candidate = trash_root / base_name
    suffix = 1
    while candidate.exists():
        candidate = trash_root / f"{base_name}-{suffix}"
        suffix += 1
    return candidate


def has_non_removable_file_flags(stat_result: object) -> bool:
    return bool(getattr(stat_result, "st_flags", 0) & NON_REMOVABLE_FILE_FLAGS)


def trash_removability_error(path: Path, detail: str) -> TrashRemovabilityError:
    return TrashRemovabilityError(
        f"Refusing to move path to Trash because it cannot be safely emptied: {path}: {detail}"
    )


def assert_tree_can_be_safely_emptied(path: Path) -> None:
    pending = [path]
    while pending:
        directory = pending.pop()
        try:
            directory_stat = directory.stat(follow_symlinks=False)
            if has_non_removable_file_flags(directory_stat):
                raise trash_removability_error(directory, "non-removable file flags are set")
            with os.scandir(directory) as entries:
                mutation_access_checked = False
                for entry in entries:
                    if not mutation_access_checked:
                        if not os.access(directory, os.W_OK | os.X_OK):
                            raise trash_removability_error(directory, "directory mutation access denied")
                        mutation_access_checked = True
                    entry_stat = entry.stat(follow_symlinks=False)
                    entry_path = Path(entry.path)
                    if has_non_removable_file_flags(entry_stat):
                        raise trash_removability_error(entry_path, "non-removable file flags are set")
                    if entry.is_dir(follow_symlinks=False):
                        pending.append(entry_path)
        except TrashRemovabilityError:
            raise
        except PermissionError as exc:
            raise trash_removability_error(directory, str(exc)) from exc
        except OSError as exc:
            raise trash_removability_error(directory, str(exc)) from exc


def assert_path_can_be_safely_emptied_from_trash(path: Path) -> None:
    try:
        path_stat = path.stat(follow_symlinks=False)
    except OSError as exc:
        raise trash_removability_error(path, str(exc)) from exc
    if has_non_removable_file_flags(path_stat):
        raise trash_removability_error(path, "non-removable file flags are set")
    if path.is_dir():
        assert_tree_can_be_safely_emptied(path)


def safe_remove(
    path: str | os.PathLike[str],
    *,
    policy: DeletePolicy,
    dry_run: bool = False,
    operation_log: OperationLogHook | None = None,
) -> None:
    target = validate_deletion_path(path, policy=policy)
    if not target.exists() and not target.is_symlink():
        return
    if dry_run:
        if operation_log is not None:
            operation_log("dry-run", target, "permanent")
        return
    try:
        remove_path_permanently(target)
    except Exception as exc:
        if operation_log is not None:
            operation_log("failed", target, str(exc))
        raise
    if operation_log is not None:
        operation_log("deleted", target, "permanent")


def route_path_to_trash(path: Path, *, policy: DeletePolicy, trash_root: Path) -> Path:
    trash_path = safe_trash_move(path, policy=policy, trash_root=trash_root)
    if trash_path is None:
        raise RuntimeError(f"Trash routing did not return a destination for: {path}")
    return trash_path


def safe_trash_move(
    path: str | os.PathLike[str],
    *,
    policy: DeletePolicy,
    trash_root: Path,
    dry_run: bool = False,
    operation_log: OperationLogHook | None = None,
) -> Path | None:
    path = validate_deletion_path(path, policy=policy)
    if path.is_symlink():
        raise RuntimeError(f"Refusing to move symlink to Trash: {path}")
    if trash_root.exists() and trash_root.is_symlink():
        raise RuntimeError(f"Refusing to use symlinked Trash directory: {trash_root}")
    trash_root.mkdir(parents=True, exist_ok=True)
    if trash_root.is_symlink():
        raise RuntimeError(f"Refusing to use symlinked Trash directory: {trash_root}")
    trash_path = unique_trash_path(path, trash_root=trash_root)
    if dry_run:
        if operation_log is not None:
            operation_log("dry-run", path, f"trash:{trash_path}")
        return trash_path
    assert_path_can_be_safely_emptied_from_trash(path)
    shutil.move(str(path), str(trash_path))
    if operation_log is not None:
        operation_log("deleted", path, f"trash:{trash_path}")
    return trash_path


def sudo_remove_error_reason(output: str) -> str:
    if any(fragment in output for fragment in ("a password is required", "a terminal is required", "Password:")):
        return "auth required"
    if "Operation not permitted" in output:
        return "sip/mdm protected"
    if "Read-only file system" in output:
        return "readonly filesystem"
    if any(fragment in output for fragment in ("Sorry, try again", "incorrect passphrase", "incorrect credentials")):
        return "auth failed"
    return "sudo error"


def safe_sudo_remove(
    path: str | os.PathLike[str],
    *,
    policy: DeletePolicy,
    dry_run: bool = False,
    operation_log: OperationLogHook | None = None,
    timeout: float = 30,
) -> None:
    target = validate_deletion_path(path, policy=policy)
    if not target.exists() and not target.is_symlink():
        return
    if target.is_symlink():
        raise RuntimeError(f"Refusing to sudo remove symlink: {target}")
    if dry_run:
        if operation_log is not None:
            operation_log("dry-run", target, "sudo permanent")
        return
    if is_test_no_auth():
        if operation_log is not None:
            operation_log("failed", target, "sudo blocked in test/no-auth mode")
        raise RuntimeError(f"Refusing to sudo remove while test/no-auth mode is enabled: sudo blocked for {target}")

    try:
        result = subprocess.run(
            [*SUDO_REMOVE_COMMAND, str(target)],
            text=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            check=False,
            timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        if operation_log is not None:
            operation_log("failed", target, str(exc))
        raise RuntimeError(f"Failed to sudo remove {target}: {exc}") from exc

    if result.returncode == 0:
        if operation_log is not None:
            operation_log("deleted", target, "sudo permanent")
        return

    reason = sudo_remove_error_reason(result.stderr or "")
    if operation_log is not None:
        operation_log("failed", target, reason)
    raise RuntimeError(f"Failed to sudo remove {target}: {reason}")


def hardlink_replace(
    path: str | os.PathLike[str],
    *,
    policy: DeletePolicy,
    target: str | os.PathLike[str],
    dry_run: bool = False,
    operation_log: OperationLogHook | None = None,
) -> Path | None:
    """Replace path with a hardlink pointing to target.

    Both files must reside on the same filesystem. The original path is
    removed and replaced with a hard link sharing inode with target.
    Returns the path on success (same inode as target), None on dry-run.
    """
    dup_path = validate_deletion_path(path, policy=policy)
    target_path = validate_deletion_path(target, policy=policy)
    if not dup_path.is_file() or dup_path.is_symlink():
        raise RuntimeError(f"Hardlink source must be a regular file: {dup_path}")
    if not target_path.is_file() or target_path.is_symlink():
        raise RuntimeError(f"Hardlink target must be a regular file: {target_path}")
    if dup_path.stat().st_ino == target_path.stat().st_ino:
        if operation_log is not None:
            operation_log("skipped", dup_path, "already-hardlinked")
        return dup_path
    if dry_run:
        if operation_log is not None:
            operation_log("dry-run", dup_path, f"hardlink:{target_path}")
        return None
    dup_path.unlink()
    os.link(target_path, dup_path)
    if operation_log is not None:
        operation_log("hardlinked", dup_path, f"target:{target_path}")
    return dup_path


def delete_path(path: Path, *, policy: DeletePolicy, delete_mode: str, trash_root: Path | None = None) -> Path | None:
    if delete_mode == "trash":
        if trash_root is None:
            raise RuntimeError("Trash delete mode requires a trash_root")
        return safe_trash_move(path, policy=policy, trash_root=trash_root)
    if delete_mode != "permanent":
        raise RuntimeError(f"Unsupported delete mode: {delete_mode}")
    safe_remove(path, policy=policy)
    return None
