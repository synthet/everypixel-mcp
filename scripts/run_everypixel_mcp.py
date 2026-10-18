"""Launch the Everypixel MCP server relative to this checkout."""

from __future__ import annotations

from pathlib import Path

from everypixel_mcp.dotenv_util import load_credential_env
from everypixel_mcp.mcp_server import run_stdio

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    load_credential_env(project_root=ROOT)
    run_stdio()


if __name__ == "__main__":
    main()
