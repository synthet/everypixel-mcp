"""Structured errors for Everypixel MCP tool responses."""

from __future__ import annotations

from typing import Any


class EverypixelMcpError(Exception):
    """Application error safe to return to MCP clients."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        details: dict[str, Any] | None = None,
        retryable: bool = False,
        next_steps: list[str] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}
        self.retryable = retryable
        self.next_steps = next_steps or []

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details,
            "retryable": self.retryable,
            "next_steps": self.next_steps,
        }


def error(
    code: str,
    message: str,
    *,
    details: dict[str, Any] | None = None,
    retryable: bool = False,
    next_steps: list[str] | None = None,
    **extra: Any,
) -> EverypixelMcpError:
    merged = dict(details or {})
    merged.update(extra)
    return EverypixelMcpError(
        code,
        message,
        details=merged,
        retryable=retryable,
        next_steps=next_steps,
    )


def map_http_error(
    status_code: int, payload: Any = None, *, endpoint: str = ""
) -> EverypixelMcpError:
    """Convert an HTTP error status and optional JSON error payload into a structured error."""
    upstream_msg = ""
    if isinstance(payload, dict):
        if isinstance(payload.get("message"), str):
            upstream_msg = payload["message"].strip()
        elif isinstance(payload.get("error"), dict) and isinstance(
            payload["error"].get("message"), str
        ):
            upstream_msg = payload["error"]["message"].strip()
        elif isinstance(payload.get("error"), str):
            upstream_msg = payload["error"].strip()

    details: dict[str, Any] = {"http_status": status_code}
    if endpoint:
        details["endpoint"] = endpoint
    if upstream_msg:
        details["upstream_message"] = upstream_msg[:500]

    if status_code == 400:
        return error(
            "invalid_request",
            upstream_msg or "Everypixel rejected the request as malformed or missing parameters.",
            details=details,
            retryable=False,
            next_steps=[
                "Verify required parameters and value types against everypixel://catalog/endpoints.",
            ],
        )
    if status_code == 401:
        return error(
            "authentication_failed",
            "Everypixel authentication failed (HTTP 401).",
            details={"http_status": status_code, **({"endpoint": endpoint} if endpoint else {})},
            retryable=False,
            next_steps=[
                "Verify EVERYPIXEL_CLIENT_ID and EVERYPIXEL_CLIENT_SECRET in .env or environment.",
                (
                    "If using EVERYPIXEL_ACCESS_TOKEN, ensure it is a valid OAuth token "
                    "(not the Client Secret)."
                ),
            ],
        )
    if status_code == 403:
        return error(
            "permission_denied",
            upstream_msg
            or "Client key lacks the required API scope or account is inactive (HTTP 403).",
            details=details,
            retryable=False,
            next_steps=[
                (
                    "Check API key scopes in https://labs.everypixel.com/account/keys "
                    "(e.g. image_edit, video_edit, chat)."
                ),
                "Confirm the Everypixel Labs account is active and email-verified.",
            ],
        )
    if status_code == 409:
        return error(
            "resource_conflict",
            upstream_msg or "Resource is currently busy (HTTP 409).",
            details=details,
            retryable=True,
            next_steps=[
                "Wait for active synthesis tasks using this voice/resource to complete and retry.",
            ],
        )
    if status_code == 422:
        return error(
            "validation_error",
            upstream_msg
            or "Request body or model/parameter combination is unsupported (HTTP 422).",
            details=details,
            retryable=False,
            next_steps=[
                "Check model-specific parameter compatibility in everypixel://catalog/models.",
            ],
        )
    if status_code == 429:
        return error(
            "rate_or_quota_exceeded",
            upstream_msg
            or "Free trial quota or paid balance is unavailable, or rate limit reached (HTTP 429).",
            details=details,
            retryable=True,
            next_steps=[
                "Check account balance and trial activation in the Everypixel Labs dashboard.",
                "Throttle request rate if sending bursts.",
            ],
        )
    if status_code in (502, 503):
        return error(
            "upstream_unavailable",
            upstream_msg
            or f"Everypixel service temporarily unavailable or rate-spiked (HTTP {status_code}).",
            details=details,
            retryable=True,
            next_steps=[
                "Back off and retry; keep concurrency under 30 RPS (or 10 RPS for /faces).",
            ],
        )
    if status_code in (408, 504):
        return error(
            "request_timeout",
            upstream_msg or f"Everypixel request timed out (HTTP {status_code}).",
            details=details,
            retryable=True,
            next_steps=[
                "Retry with backoff or increase EVERYPIXEL_TIMEOUT_SECONDS for large inputs.",
            ],
        )
    return error(
        "upstream_error",
        upstream_msg or f"Everypixel API failed with HTTP {status_code}.",
        details=details,
        retryable=500 <= status_code < 600,
        next_steps=[
            "Retry if transient (5xx); otherwise inspect parameters and upstream status.",
        ],
    )
