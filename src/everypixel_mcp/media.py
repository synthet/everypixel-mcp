"""Validated opt-in local media access confined to EVERYPIXEL_MEDIA_ROOTS."""

from __future__ import annotations

import base64
import os
from dataclasses import dataclass
from pathlib import Path

from .errors import error
from .limits import (
    MAX_AUDIO_UPLOAD_BYTES,
    MAX_IMAGE_UPLOAD_BYTES,
    MAX_VIDEO_UPLOAD_BYTES,
)

MEDIA_ROOTS_ENV = "EVERYPIXEL_MEDIA_ROOTS"

IMAGE_MIMES: dict[str, str] = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".svg": "image/svg+xml",
    ".bmp": "image/bmp",
    ".tiff": "image/tiff",
    ".tif": "image/tiff",
    ".avif": "image/avif",
    ".ico": "image/x-icon",
    ".jfif": "image/jpeg",
    ".pjpeg": "image/jpeg",
    ".apng": "image/apng",
    ".svgz": "image/svg+xml",
    ".xbm": "image/x-xbitmap",
}

VIDEO_MIMES: dict[str, str] = {
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
    ".avi": "video/x-msvideo",
    ".webm": "video/webm",
    ".mpeg": "video/mpeg",
    ".mpg": "video/mpeg",
    ".m4v": "video/x-m4v",
    ".wmv": "video/x-ms-wmv",
    ".ogv": "video/ogg",
    ".ogm": "video/ogg",
    ".asx": "video/x-ms-asf",
}

AUDIO_MIMES: dict[str, str] = {
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".m4a": "audio/mp4",
    ".ogg": "audio/ogg",
    ".flac": "audio/flac",
    ".opus": "audio/opus",
    ".aiff": "audio/aiff",
    ".wma": "audio/x-ms-wma",
    ".webm": "audio/webm",
    ".weba": "audio/webm",
    ".oga": "audio/ogg",
    ".mid": "audio/midi",
    ".au": "audio/basic",
}


@dataclass(frozen=True)
class LoadedMedia:
    path: Path
    data: bytes
    mime_type: str
    filename: str


def media_roots(environ: dict[str, str] | None = None) -> list[Path]:
    env = environ if environ is not None else os.environ
    return [
        Path(p.strip()).resolve()
        for p in env.get(MEDIA_ROOTS_ENV, "").split(os.pathsep)
        if p.strip()
    ]


def is_http_url(value: str) -> bool:
    if not isinstance(value, str):
        return False
    lowered = value.strip().lower()
    return lowered.startswith("http://") or lowered.startswith("https://")


def is_data_uri(value: str, *, expected_prefix: str = "data:") -> bool:
    if not isinstance(value, str):
        return False
    stripped = value.strip()
    return stripped.startswith(expected_prefix) and ";base64," in stripped


def load_local_media(
    raw_path: str,
    *,
    kind: str,
    allow_local_files: bool,
    roots: list[Path] | None = None,
    allowed_extensions: set[str] | None = None,
    max_bytes: int | None = None,
) -> LoadedMedia:
    """Read and validate a local media file inside EVERYPIXEL_MEDIA_ROOTS."""
    if type(allow_local_files) is not bool:
        raise error("invalid_input", "allow_local_files must be a boolean.")
    if not allow_local_files:
        raise error(
            "local_files_disabled",
            "Local file paths require allow_local_files=true.",
            next_steps=[
                "Set allow_local_files=true on the request and configure EVERYPIXEL_MEDIA_ROOTS.",
                "Or pass a public HTTP(S) URL or data URI instead.",
            ],
        )
    configured_roots = roots if roots is not None else media_roots()
    if not configured_roots:
        raise error(
            "local_files_disabled",
            f"Local file paths require {MEDIA_ROOTS_ENV} to be configured.",
            next_steps=[
                f"Set {MEDIA_ROOTS_ENV} in .env or environment to the allowed directory path(s).",
            ],
        )
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise error("invalid_input", f"{kind} path must be a non-empty string.")
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        raise error(
            "invalid_input",
            f"Local {kind} path must be absolute.",
            next_steps=["Pass an absolute path inside EVERYPIXEL_MEDIA_ROOTS."],
        )
    try:
        resolved = candidate.resolve(strict=True)
    except (OSError, ValueError, RuntimeError) as exc:
        raise error("invalid_input", f"Local {kind} file could not be resolved.") from exc

    if not any(resolved.is_relative_to(root.resolve()) for root in configured_roots):
        raise error(
            "invalid_input",
            f"Local {kind} file is outside the allowed {MEDIA_ROOTS_ENV} directories.",
            next_steps=[f"Place the file under an allowed {MEDIA_ROOTS_ENV} directory."],
        )
    if not resolved.is_file():
        raise error("invalid_input", f"Local {kind} path must be a regular file.")

    ext = resolved.suffix.lower()
    if kind == "image":
        mime_map = IMAGE_MIMES
        default_limit = MAX_IMAGE_UPLOAD_BYTES
    elif kind == "video":
        mime_map = VIDEO_MIMES
        default_limit = MAX_VIDEO_UPLOAD_BYTES
    elif kind == "audio":
        mime_map = AUDIO_MIMES
        default_limit = MAX_AUDIO_UPLOAD_BYTES
    else:
        raise error("invalid_input", f"Unsupported media kind '{kind}'.")

    valid_exts = allowed_extensions if allowed_extensions is not None else set(mime_map)
    if ext not in valid_exts or ext not in mime_map:
        allowed_list = ", ".join(sorted(valid_exts))
        raise error(
            "invalid_input",
            f"Unsupported {kind} file extension '{ext or '<none>'}'. Allowed: {allowed_list}.",
        )

    limit = max_bytes if max_bytes is not None else default_limit
    try:
        with resolved.open("rb") as f:
            data = f.read(limit + 1)
    except OSError as exc:
        raise error("invalid_input", f"Local {kind} file could not be read.") from exc

    if not data:
        raise error("invalid_input", f"Local {kind} file is empty.")
    if len(data) > limit:
        raise error(
            "request_too_large",
            f"Local {kind} file exceeds the {limit // (1024 * 1024)} MiB upload limit.",
        )

    return LoadedMedia(
        path=resolved,
        data=data,
        mime_type=mime_map[ext],
        filename=resolved.name,
    )


def to_data_uri(media: LoadedMedia) -> str:
    encoded = base64.b64encode(media.data).decode("ascii")
    return f"data:{media.mime_type};base64,{encoded}"


def resolve_url_or_data_uri(
    *,
    url_or_uri: str | None = None,
    file_path: str | None = None,
    kind: str,
    allow_local_files: bool = False,
    require_data_uri: bool = False,
    roots: list[Path] | None = None,
    allowed_extensions: set[str] | None = None,
    max_bytes: int | None = None,
    field_name: str = "media",
) -> str:
    """Resolve either an HTTP(S) URL / Data URI or a confined local file path."""
    if url_or_uri and file_path:
        raise error(
            "invalid_input",
            f"Pass either {field_name} URL/data URI or local path, not both.",
        )
    if file_path:
        loaded = load_local_media(
            file_path,
            kind=kind,
            allow_local_files=allow_local_files,
            roots=roots,
            allowed_extensions=allowed_extensions,
            max_bytes=max_bytes,
        )
        return to_data_uri(loaded)
    if not url_or_uri or not isinstance(url_or_uri, str) or not url_or_uri.strip():
        raise error("invalid_input", f"{field_name} is required.")
    cleaned = url_or_uri.strip()
    if require_data_uri:
        if not is_data_uri(cleaned, expected_prefix=f"data:{kind}/"):
            raise error(
                "invalid_input",
                (
                    f"{field_name} must be a full 'data:{kind}/...;base64,...' Data URI "
                    "(or provide a local path with allow_local_files=true)."
                ),
            )
        return cleaned
    if is_http_url(cleaned) or is_data_uri(cleaned):
        return cleaned
    raise error(
        "invalid_input",
        f"{field_name} must be a valid HTTP(S) URL or base64 Data URI.",
    )
