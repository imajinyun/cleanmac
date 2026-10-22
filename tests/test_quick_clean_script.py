from __future__ import annotations

import json
import os
import subprocess
import textwrap
from pathlib import Path

from tests.helpers import PROJECT_ROOT

_FAKE_PYTHON = textwrap.dedent(
    """\
    #!/usr/bin/env python3
    from __future__ import annotations

    import json
    import sys
    from pathlib import Path

    call_log = Path({call_log!r})
    argv = sys.argv[1:]
    with call_log.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(argv) + "\\n")

    if argv and argv[0] == "-c":
        print("120")
        print("100")
        raise SystemExit(0)

    if argv[:3] == ["cleanmac.py", "clean", "--profile"]:
        if "--execute" in argv and argv[3] == "developer":
            print(
                "Refusing to execute cleanup because candidate bytes exceed --max-delete-mb budget. "
                "Candidates: 150.00 MB; budget: 120.00 MB",
                file=sys.stderr,
            )
            raise SystemExit(1)
        print("DRY-RUN: fake preview")
        raise SystemExit(0)

    raise SystemExit(f"unexpected argv: {{argv!r}}")
    """
)


def _run_quick_clean(tmp_path: Path, profile: str) -> tuple[subprocess.CompletedProcess[str], Path]:
    fake_python = tmp_path / "fake_python.py"
    call_log = tmp_path / "calls.jsonl"
    fake_python.write_text(_FAKE_PYTHON.format(call_log=str(call_log)), encoding="utf-8")
    fake_python.chmod(0o755)

    env = {**os.environ, "PYTHON": str(fake_python)}
    result = subprocess.run(
        ["bash", "scripts/quick_clean.sh", profile],
        input="y\n",
        capture_output=True,
        text=True,
        env=env,
        cwd=PROJECT_ROOT,
    )
    return result, call_log


def test_quick_clean_passes_profile_args_to_budget_probe(tmp_path: Path) -> None:
    result, call_log = _run_quick_clean(tmp_path, "safe")

    assert result.returncode == 0, f"stdout:\n{result.stdout}\n\nstderr:\n{result.stderr}"
    assert "Safety budget: 120 MB" in result.stdout
    assert "Estimated candidates: 100 MB" in result.stdout
    calls = [json.loads(line) for line in call_log.read_text(encoding="utf-8").splitlines()]

    budget_call = calls[0]
    assert budget_call[0] == "-c"
    assert budget_call[2:5] == ["cleanmac.py", "--json", "clean"]
    assert "--profile" in budget_call
    assert "safe" in budget_call
    assert "p" not in budget_call
    assert "r" not in budget_call

    execute_call = calls[-1]
    budget_flag_index = execute_call.index("--max-delete-mb")
    assert execute_call[budget_flag_index + 1] == "120"
    assert "--delete-mode" in execute_call
    assert "trash" in execute_call


def test_quick_clean_budget_failure_prints_actionable_guidance(tmp_path: Path) -> None:
    result, _call_log = _run_quick_clean(tmp_path, "developer")

    assert result.returncode == 1
    assert "Budget guidance:" in result.stdout
    assert "Estimated candidates : 100 MB" in result.stdout
    assert "Current budget       : 120 MB" in result.stdout
    assert "raise --max-delete-mb only after reviewing" in result.stdout
