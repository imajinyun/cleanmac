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


if __name__ == "__main__":
    unittest.main()
