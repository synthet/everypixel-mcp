"""Published MCP output types and normalized envelopes for Everypixel MCP."""

from __future__ import annotations

from typing import Any, Literal, Required

from typing_extensions import TypedDict

AnalyzeOperation = Literal[
    "keywords",
    "video_keywords",
    "caption",
    "faces",
    "quality",
    "quality_ugc",
]

ImageOperation = Literal[
    "generate",
    "edit",
    "remove_background",
    "vectorize",
    "upscale",
    "face_swap",
]

VideoOperation = Literal[
    "generate",
    "edit",
    "upscale",
    "matting",
    "soundtrack",
    "face_swap",
]

LipsyncOperation = Literal[
    "image_lipsync",
    "video_lipsync",
]

TtsOperation = Literal[
    "create",
    "clone",
    "design",
    "save_voice",
    "list_voices",
    "delete_voice",
]


class ErrorDetails(TypedDict):
    code: str
    message: str
    details: dict[str, Any]
    retryable: bool
    next_steps: list[str]


class ToolEnvelope(TypedDict, total=False):
    ok: Required[bool]
    result: dict[str, Any]
    error: ErrorDetails
