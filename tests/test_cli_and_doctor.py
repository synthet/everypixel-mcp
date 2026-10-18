from __future__ import annotations

import json
from pathlib import Path

import pytest

from everypixel_mcp.cli import main
from everypixel_mcp.doctor import diagnose


@pytest.mark.asyncio
async def test_doctor_diagnose_offline(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("EVERYPIXEL_CLIENT_ID", "test-id")
    monkeypatch.setenv("EVERYPIXEL_CLIENT_SECRET", "test-secret")
    monkeypatch.setenv("EVERYPIXEL_MEDIA_ROOTS", str(tmp_path))
    report = await diagnose(project_root=tmp_path, live=False)
    assert report["mcp_handshake"] is True
    assert report["credential_present"] is True
    assert report["auth_mode"] == "basic"
    assert report["media_roots_configured"] is True
    assert report["ready"] is True
    assert len(report["tools"]) == 8
    assert len(report["resources"]) == 2


def test_cli_doctor_json_exit_codes(monkeypatch, capsys):
    monkeypatch.setenv("EVERYPIXEL_CLIENT_ID", "test-id")
    monkeypatch.setenv("EVERYPIXEL_CLIENT_SECRET", "test-secret")
    rc = main(["doctor", "--json"])
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert rc == 0
    assert parsed["ready"] is True

    monkeypatch.delenv("EVERYPIXEL_CLIENT_ID", raising=False)
    monkeypatch.delenv("EVERYPIXEL_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("EVERYPIXEL_ACCESS_TOKEN", raising=False)
    monkeypatch.setenv("EVERYPIXEL_ENV_FILE", "")
    rc_missing = main(["doctor", "--json"])
    assert rc_missing == 1
