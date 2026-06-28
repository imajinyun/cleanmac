from __future__ import annotations

import json
import os
import subprocess
import textwrap
import unittest
from pathlib import Path


class QuickCleanScriptTests(unittest.TestCase):
    def test_quick_clean_passes_profile_args_to_budget_probe(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            fake_python = tmp_path / "fake_python.py"
            call_log = tmp_path / "calls.jsonl"
            fake_python.write_text(
                textwrap.dedent(
                    f"""\
                    #!/usr/bin/env python3
                    from __future__ import annotations

                    import json
                    import sys
                    from pathlib import Path

                    call_log = Path({str(call_log)!r})
                    argv = sys.argv[1:]
                    with call_log.open("a", encoding="utf-8") as fh:
                        fh.write(json.dumps(argv) + "\\n")

                    if argv and argv[0] == "-c":
                        print("120")
                        raise SystemExit(0)

                    if argv[:3] == ["cleanmac.py", "clean", "--profile"]:
                        print("DRY-RUN: fake preview")
                        raise SystemExit(0)

                    raise SystemExit(f"unexpected argv: {{argv!r}}")
                    """
                ),
                encoding="utf-8",
            )
            fake_python.chmod(0o755)

            env = {
                **os.environ,
                "PYTHON": str(fake_python),
            }
            result = subprocess.run(
                ["bash", "scripts/quick_clean.sh", "developer"],
                input="y\n",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
            )
            self.assertEqual(
                result.returncode,
                0,
                f"stdout:\n{result.stdout}\n\nstderr:\n{result.stderr}",
            )

            self.assertIn("Safety budget: 120 MB", result.stdout)
            calls = [json.loads(line) for line in call_log.read_text(encoding="utf-8").splitlines()]

            budget_call = calls[0]
            self.assertEqual(budget_call[0], "-c")
            self.assertEqual(budget_call[2:5], ["cleanmac.py", "--json", "clean"])
            self.assertIn("--profile", budget_call)
            self.assertIn("developer", budget_call)
            self.assertNotIn("p", budget_call)
            self.assertNotIn("r", budget_call)

            execute_call = calls[-1]
            budget_flag_index = execute_call.index("--max-delete-mb")
            self.assertEqual(execute_call[budget_flag_index + 1], "120")
            self.assertIn("--delete-mode", execute_call)
            self.assertIn("trash", execute_call)


if __name__ == "__main__":
    unittest.main()
