from __future__ import annotations

import os
from pathlib import Path

import pytest

from everypixel_mcp.errors import EverypixelMcpError
from everypixel_mcp.media import (
    load_local_media,
    media_roots,
    resolve_url_or_data_uri,
    to_data_uri,
)


def test_local_media_requires_opt_in_flag(tmp_path: Path):
    img = tmp_path / "sample.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\nfake")
    with pytest.raises(EverypixelMcpError) as exc:
        load_local_media(
            str(img),
            kind="image",
            allow_local_files=False,
            roots=[tmp_path],
        )
    assert exc.value.code == "local_files_disabled"


def test_local_media_requires_configured_roots(tmp_path: Path):
    img = tmp_path / "sample.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\nfake")
    with pytest.raises(EverypixelMcpError) as exc:
        load_local_media(
            str(img),
            kind="image",
            allow_local_files=True,
            roots=[],
        )
    assert exc.value.code == "local_files_disabled"


def test_local_media_rejects_paths_outside_roots(tmp_path: Path):
    allowed = tmp_path / "allowed"
    outside = tmp_path / "outside"
    allowed.mkdir()
    outside.mkdir()
    secret_img = outside / "secret.png"
    secret_img.write_bytes(b"\x89PNG\r\n\x1a\nfake")

    with pytest.raises(EverypixelMcpError) as exc:
        load_local_media(
            str(secret_img),
            kind="image",
            allow_local_files=True,
            roots=[allowed.resolve()],
        )
    assert exc.value.code == "invalid_input"


def test_local_media_loads_and_encodes_data_uri(tmp_path: Path):
    img = tmp_path / "sample.png"
    img.write_bytes(b"hello-png")
    loaded = load_local_media(
        str(img),
        kind="image",
        allow_local_files=True,
        roots=[tmp_path.resolve()],
    )
    assert loaded.mime_type == "image/png"
    uri = to_data_uri(loaded)
    assert uri.startswith("data:image/png;base64,")

    resolved = resolve_url_or_data_uri(
        file_path=str(img),
        kind="image",
        allow_local_files=True,
        require_data_uri=True,
        roots=[tmp_path.resolve()],
    )
    assert resolved == uri


def test_media_roots_parses_env(tmp_path: Path):
    root1 = tmp_path / "r1"
    root2 = tmp_path / "r2"
    root1.mkdir()
    root2.mkdir()
    raw = f"{root1}{os.pathsep}{root2}"
    parsed = media_roots({"EVERYPIXEL_MEDIA_ROOTS": raw})
    assert parsed == [root1.resolve(), root2.resolve()]
