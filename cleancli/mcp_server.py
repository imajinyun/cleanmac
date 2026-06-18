"""Cleanmac MCP stdio server entry point for cleanmac-mcp console script.

When installed via pip, this module provides the ``cleanmac-mcp`` console script
that starts the MCP stdio server for LLM tool integration.
"""

from __future__ import annotations

import os
import sys


def main() -> None:
    """Run the cleanmac MCP stdio server.

    Re-exports from ``scripts.cleanmac_mcp_server`` so the server can be run
    as a console script (``cleanmac-mcp``) after pip install.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, ".."))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    from scripts.cleanmac_mcp_server import main as _mcp_main  # type: ignore[import-untyped]

    _mcp_main()


if __name__ == "__main__":
    main()
