from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


def load_security_module():
    path = Path(__file__).resolve().parents[1] / "scripts" / "security_scan.py"
    spec = importlib.util.spec_from_file_location("cleanmac_security_scan", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SecurityScanTests(unittest.TestCase):
    def test_security_scan_flags_raw_delete_and_privileged_business_calls(self) -> None:
        scanner = load_security_module()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            module = root / "cleancli" / "feature.py"
            module.parent.mkdir()
            module.write_text(
                "import subprocess\nsubprocess.run(['sudo', 'true'])\nsubprocess.run(['rm', '-rf', '/tmp/example'])\n",
                encoding="utf-8",
            )

            violations = scanner.scan_repo(root)

        self.assertTrue(any("privileged command 'sudo'" in violation for violation in violations), violations)
        self.assertTrue(
            any("subprocess must not directly invoke rm" in violation for violation in violations), violations
        )

    def test_security_scan_flags_python_shell_strings_and_absolute_commands(self) -> None:
        scanner = load_security_module()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            module = root / "cleancli" / "feature.py"
            module.parent.mkdir()
            module.write_text(
                "import subprocess\n"
                "subprocess.run('/usr/bin/osascript -e return', shell=True)\n"
                "subprocess.Popen(('/bin/rm', '-rf', '/tmp/example'))\n",
                encoding="utf-8",
            )

            violations = scanner.scan_repo(root)

        self.assertTrue(any("privileged command 'osascript'" in violation for violation in violations), violations)
        self.assertTrue(
            any("subprocess must not directly invoke rm" in violation for violation in violations), violations
        )

    def test_security_scan_ignores_local_virtualenvs(self) -> None:
        scanner = load_security_module()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            vendored = root / ".venv" / "lib" / "python3.12" / "site-packages" / "pip" / "_internal" / "cleanup.py"
            vendored.parent.mkdir(parents=True)
            vendored.write_text("import shutil\nshutil.rmtree('/tmp/example')\n", encoding="utf-8")

            violations = scanner.scan_repo(root)

        self.assertEqual(violations, [])

    def test_security_scan_flags_shell_privileged_commands(self) -> None:
        scanner = load_security_module()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            script = root / "scripts" / "unsafe.sh"
            script.parent.mkdir()
            script.write_text(
                "#!/bin/sh\n"
                "sudo launchctl bootout system/com.example.daemon\n"
                'osascript -e \'tell app "Finder" to delete POSIX file "/tmp/example"\'\n',
                encoding="utf-8",
            )

            violations = scanner.scan_repo(root)

        self.assertTrue(
            any("shell must not invoke privileged command 'sudo'" in violation for violation in violations), violations
        )
        self.assertTrue(
            any("shell must not invoke privileged command 'launchctl'" in violation for violation in violations),
            violations,
        )
        self.assertTrue(
            any("shell must not invoke privileged command 'osascript'" in violation for violation in violations),
            violations,
        )

    def test_security_scan_flags_workflow_privileged_run_blocks(self) -> None:
        scanner = load_security_module()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            workflow = root / ".github" / "workflows" / "unsafe.yml"
            workflow.parent.mkdir(parents=True)
            workflow.write_text(
                "name: unsafe\n"
                "jobs:\n"
                "  unsafe:\n"
                "    runs-on: macos-15\n"
                "    steps:\n"
                "      - run: |\n"
                "          launchctl bootout system/com.example.daemon\n"
                "          osascript -e 'return 1'\n",
                encoding="utf-8",
            )

            violations = scanner.scan_repo(root)

        self.assertTrue(
            any("workflow must not invoke privileged command 'launchctl'" in violation for violation in violations),
            violations,
        )
        self.assertTrue(
            any("workflow must not invoke privileged command 'osascript'" in violation for violation in violations),
            violations,
        )

    def test_security_scan_allows_test_runner_privileged_stubs(self) -> None:
        scanner = load_security_module()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            script = root / "scripts" / "test.sh"
            script.parent.mkdir()
            script.write_text(
                "#!/bin/sh\n"
                "cat > \"$TEST_SYSTEM_STUB_DIR/sudo\" <<'EOF'\n"
                "printf 'cleanmac test blocked sudo: %s\\n' \"$*\" >&2\n"
                "EOF\n"
                "cat > \"$TEST_SYSTEM_STUB_DIR/osascript\" <<'EOF'\n"
                "printf 'cleanmac test blocked osascript: %s\\n' \"$*\" >&2\n"
                "EOF\n"
                "cat > \"$TEST_SYSTEM_STUB_DIR/launchctl\" <<'EOF'\n"
                "printf 'cleanmac test blocked launchctl: %s\\n' \"$*\" >&2\n"
                "EOF\n",
                encoding="utf-8",
            )

            violations = scanner.scan_repo(root)

        self.assertEqual(violations, [])

    def test_security_scan_allows_delete_ops_boundary(self) -> None:
        scanner = load_security_module()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            module = root / "cleancli" / "delete_ops.py"
            module.parent.mkdir()
            module.write_text(
                "import subprocess\nsubprocess.run(['sudo', '-n', 'rm', '-rf', '/tmp/example'])\n", encoding="utf-8"
            )

            violations = scanner.scan_repo(root)

        self.assertEqual(violations, [])

    def test_security_scan_flags_gui_tui_and_resident_product_surfaces(self) -> None:
        scanner = load_security_module()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            module = root / "cleancli" / "gui.py"
            module.parent.mkdir()
            module.write_text("import curses\nfrom tkinter import Tk\nimport rumps\n", encoding="utf-8")
            pyproject = root / "pyproject.toml"
            pyproject.write_text('[project]\ndependencies = ["textual", "PyQt6"]\n', encoding="utf-8")
            plist = root / "LaunchAgents" / "com.cleanmac.agent.plist"
            plist.parent.mkdir()
            plist.write_text("<plist><dict><key>RunAtLoad</key><true/></dict></plist>\n", encoding="utf-8")

            violations = scanner.scan_repo(root)

        self.assertTrue(any("forbidden TUI framework import 'curses'" in violation for violation in violations), violations)
        self.assertTrue(any("forbidden GUI framework import 'tkinter'" in violation for violation in violations), violations)
        self.assertTrue(any("forbidden menu bar app framework import 'rumps'" in violation for violation in violations), violations)
        self.assertTrue(any("forbidden TUI framework dependency 'textual'" in violation for violation in violations), violations)
        self.assertTrue(any("forbidden GUI framework dependency 'pyqt'" in violation for violation in violations), violations)
        self.assertTrue(any("autostart product surface is forbidden" in violation for violation in violations), violations)
        self.assertTrue(any("LaunchAgent/LaunchDaemon plist is forbidden" in violation for violation in violations), violations)


if __name__ == "__main__":
    unittest.main()
