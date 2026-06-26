from __future__ import annotations

import pytest

from cleancli import delete_ops
from tests.helpers import cleanmac_test_env


@pytest.mark.parametrize(
    "argv",
    [
        ["sudo", "true"],
        ["sudo", "-n", "true"],
        ["osascript", "-e", "return 1"],
        ["launchctl", "print", "system"],
    ],
)
def test_test_mode_blocks_privileged_and_automation_helpers(argv: list[str]) -> None:
    with cleanmac_test_env():
        assert delete_ops.run_text_command(argv) is None
