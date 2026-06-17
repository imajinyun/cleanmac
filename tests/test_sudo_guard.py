from __future__ import annotations

from cleancli import delete_ops
from tests.helpers import cleanmac_test_env


def test_test_mode_blocks_any_sudo_execution() -> None:
    with cleanmac_test_env():
        assert delete_ops.run_text_command(["sudo", "true"]) is None
        assert delete_ops.run_text_command(["sudo", "-n", "true"]) is None
