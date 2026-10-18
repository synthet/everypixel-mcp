from __future__ import annotations

import importlib.util
import json
import tomllib
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "installer",
    Path(__file__).resolve().parents[1] / "scripts/install_everypixel_mcp_workstation.py",
)
assert spec is not None and spec.loader is not None
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


@pytest.mark.parametrize(
    "header",
    [
        '[mcp_servers."everypixel-rw-labs"]',
        "[mcp_servers.'everypixel-rw-labs']",
        "[ mcp_servers.everypixel-rw-labs ] # local server",
    ],
)
def test_codex_update_handles_valid_table_spelling(tmp_path: Path, monkeypatch, header: str):
    path = tmp_path / "config.toml"
    path.write_text(
        'model = "keep-me"\n' + header + '\ncommand = "old"\n'
        '[mcp_servers.other]\ncommand = "keep-other"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(
        installer,
        "mcp_entry",
        lambda: {
            "command": "uv",
            "args": ["run", "server.py"],
            "env": {"EVERYPIXEL_ENV_FILE": "test.env"},
        },
    )
    installer.upsert_codex_toml(path)
    installer.upsert_codex_toml(path)
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    assert data["model"] == "keep-me"
    assert data["mcp_servers"]["other"]["command"] == "keep-other"
    assert data["mcp_servers"][installer.SERVER_KEY]["command"] == "uv"


def test_json_update_accepts_windows_utf8_bom(tmp_path: Path, monkeypatch):
    path = tmp_path / "mcp.json"
    path.write_text('{"mcpServers":{"other":{"command":"keep"}}}', encoding="utf-8-sig")
    monkeypatch.setattr(installer, "mcp_entry", lambda: {"command": "uv", "args": []})
    assert installer.upsert_json_mcp(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["mcpServers"]["other"]["command"] == "keep"
    assert data["mcpServers"][installer.SERVER_KEY]["command"] == "uv"


def test_codex_unsupported_layout_is_not_overwritten(tmp_path: Path, monkeypatch):
    path = tmp_path / "config.toml"
    original = '[mcp_servers]\neverypixel-rw-labs = {command = "old"}\n'
    path.write_text(original, encoding="utf-8")
    monkeypatch.setattr(installer, "mcp_entry", lambda: {"command": "uv", "args": []})
    with pytest.raises(ValueError):
        installer.upsert_codex_toml(path)
    assert path.read_text(encoding="utf-8") == original


def test_atomic_replace_failure_preserves_original(tmp_path: Path, monkeypatch):
    path = tmp_path / "mcp.json"
    original = '{"mcpServers":{"other":{"command":"keep"}}}'
    path.write_text(original, encoding="utf-8")
    monkeypatch.setattr(installer, "mcp_entry", lambda: {"command": "uv", "args": []})

    def fail(*args):
        raise OSError("simulated replace failure")

    monkeypatch.setattr(installer.os, "replace", fail)
    with pytest.raises(OSError):
        installer.upsert_json_mcp(path)
    assert path.read_text(encoding="utf-8") == original
    assert list(tmp_path.iterdir()) == [path]


def test_dry_run_does_not_create_files_or_directories(tmp_path: Path, monkeypatch):
    path = tmp_path / "missing" / "mcp.json"
    monkeypatch.setattr(installer, "mcp_entry", lambda: {"command": "uv", "args": []})
    assert installer.upsert_json_mcp(path, create=True, dry_run=True)
    installer.upsert_codex_toml(tmp_path / "codex" / "config.toml", dry_run=True)
    assert list(tmp_path.iterdir()) == []
