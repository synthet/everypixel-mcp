"""Load local .env files without logging values."""

from __future__ import annotations

import os
from pathlib import Path


def load_dotenv(path: Path) -> int:
    """Load KEY=VALUE pairs without overriding existing process env.

    Returns the number of newly set keys. Values are never logged or returned.
    """
    if not path.is_file():
        return 0
    loaded = 0
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        key, value = line.split("=", 1)
        key = key.strip()
        if not key or key in os.environ:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        os.environ[key] = value
        loaded += 1
    return loaded


def load_credential_env(*, project_root: Path) -> None:
    """Load credentials for MCP/CLI from project ``.env`` then optional env-file pointers.

    Existing process env always wins (``load_dotenv`` does not override). Project
    ``.env`` is preferred over ``EVERYPIXEL_ENV_FILE`` / ``DOTENV_PATH`` so a local key
    is what the Everypixel client uses for the connection.
    """
    load_dotenv(project_root / ".env")
    for key in ("EVERYPIXEL_ENV_FILE", "DOTENV_PATH"):
        raw = os.environ.get(key)
        if raw:
            load_dotenv(Path(raw))
