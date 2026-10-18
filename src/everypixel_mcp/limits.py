"""Local request, upload, polling, and response budgets."""

from __future__ import annotations

import json
import math
from typing import Any

from .errors import error

MAX_REQUEST_BYTES = 32 * 1024 * 1024  # 32 MiB JSON payload cap (including Data URIs)
MAX_RESPONSE_BYTES = 512_000
MAX_IMAGE_UPLOAD_BYTES = 16 * 1024 * 1024  # 16 MiB
MAX_AUDIO_UPLOAD_BYTES = 25 * 1024 * 1024  # 25 MiB (ElevenLabs sample max)
MAX_VIDEO_UPLOAD_BYTES = 100 * 1024 * 1024  # 100 MiB
DEFAULT_WAIT_TIMEOUT_SECONDS = 120.0
MAX_WAIT_TIMEOUT_SECONDS = 600.0
DEFAULT_POLL_INTERVAL_SECONDS = 2.0
MIN_POLL_INTERVAL_SECONDS = 0.5
MAX_POLL_INTERVAL_SECONDS = 30.0


def validate_json_payload(payload: Any, *, max_bytes: int = MAX_REQUEST_BYTES) -> None:
    """Verify payload contains finite JSON values and fits the local byte budget."""
    size = 0
    try:
        encoder = json.JSONEncoder(ensure_ascii=False, allow_nan=False)
        for chunk in encoder.iterencode(payload):
            size += len(chunk.encode("utf-8"))
            if size > max_bytes:
                raise error(
                    "request_too_large",
                    "Request payload exceeds the local byte budget.",
                    next_steps=[
                        "Use smaller media files or pass public HTTP(S) URLs where supported."
                    ],
                )
    except (TypeError, ValueError, RecursionError) as exc:
        raise error(
            "invalid_input",
            "Request parameters must contain finite JSON-serializable values.",
        ) from exc


def validate_wait_bounds(
    *,
    wait: bool,
    wait_timeout_seconds: float = DEFAULT_WAIT_TIMEOUT_SECONDS,
    poll_interval_seconds: float = DEFAULT_POLL_INTERVAL_SECONDS,
) -> tuple[bool, float, float]:
    if type(wait) is not bool:
        raise error("invalid_input", "wait must be a boolean.")
    if (
        isinstance(wait_timeout_seconds, bool)
        or not isinstance(wait_timeout_seconds, (int, float))
        or not math.isfinite(wait_timeout_seconds)
        or wait_timeout_seconds <= 0
        or wait_timeout_seconds > MAX_WAIT_TIMEOUT_SECONDS
    ):
        raise error(
            "invalid_input",
            f"wait_timeout_seconds must be a finite number in (0, {MAX_WAIT_TIMEOUT_SECONDS}].",
        )
    if (
        isinstance(poll_interval_seconds, bool)
        or not isinstance(poll_interval_seconds, (int, float))
        or not math.isfinite(poll_interval_seconds)
        or poll_interval_seconds < MIN_POLL_INTERVAL_SECONDS
        or poll_interval_seconds > MAX_POLL_INTERVAL_SECONDS
    ):
        raise error(
            "invalid_input",
            (
                f"poll_interval_seconds must be in "
                f"[{MIN_POLL_INTERVAL_SECONDS}, {MAX_POLL_INTERVAL_SECONDS}]."
            ),
        )
    return wait, float(wait_timeout_seconds), float(poll_interval_seconds)
