"""Offline readiness checks; live upstream check requires an explicit --live flag."""

from __future__ import annotations

import os
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

import anyio
from mcp import Client

from .client import EverypixelClient, default_base_url, default_timeout, has_credentials
from .errors import EverypixelMcpError
from .mcp_server import create_server
from .media import media_roots


def _safe_version(pkg: str) -> str:
    try:
        return version(pkg)
    except PackageNotFoundError:
        return "0.1.0"


async def diagnose(*, project_root: Path, live: bool = False) -> dict[str, Any]:
    auth_mode = "none"
    if os.environ.get("EVERYPIXEL_CLIENT_ID") and os.environ.get("EVERYPIXEL_CLIENT_SECRET"):
        auth_mode = "basic"
    elif os.environ.get("EVERYPIXEL_ACCESS_TOKEN"):
        auth_mode = "bearer"

    report: dict[str, Any] = {
        "live": live,
        "executable": sys.executable,
        "versions": {name: _safe_version(name) for name in ("everypixel-mcp", "mcp", "httpx2")},
        "credential_present": has_credentials(),
        "auth_mode": auth_mode,
        "media_roots_configured": len(media_roots()) > 0,
        "env_files": {
            "project": (project_root / ".env").is_file(),
            **{
                key: bool(os.environ.get(key)) and Path(os.environ[key]).is_file()
                for key in ("EVERYPIXEL_ENV_FILE", "DOTENV_PATH")
            },
        },
        "mcp_handshake": False,
        "ready": False,
    }
    try:
        report.update(
            base_url=default_base_url(),
            timeout_seconds=default_timeout(),
        )
        with anyio.fail_after(10):
            async with Client(create_server()) as client:
                tools = await client.list_tools()
                resources = await client.list_resources()
        report["tools"] = sorted(tool.name for tool in tools.tools)
        report["resources"] = sorted(str(res.uri) for res in resources.resources)
        report["mcp_handshake"] = len(tools.tools) == 8 and len(resources.resources) == 2
        if live:
            await EverypixelClient().tts(operation="list_voices", limit=1)
            report["live_ok"] = True
        report["ready"] = (
            report["mcp_handshake"]
            and report["credential_present"]
            and (not live or bool(report.get("live_ok")))
        )
    except EverypixelMcpError as exc:
        report["error"] = exc.as_dict()
    except Exception:
        report["error"] = {
            "code": "diagnostic_failed",
            "message": "Local diagnostic failed.",
        }
    return report
