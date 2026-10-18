"""Everypixel Labs API v1 client wrapper with strict input validation."""

from __future__ import annotations

import json
import math
import os
from collections.abc import Callable
from typing import Any

import anyio
import httpx2

from .catalog import (
    CAPTION_LENGTHS,
    CHAT_MODELS,
    IMAGE_EDIT_MODELS,
    IMAGE_GENERATE_MODELS,
    IMAGE_LIPSYNC_MODELS,
    IMAGE_SIZES,
    IMAGE_UPSCALE_MODELS,
    KEYWORD_LANGUAGES,
    LIPSYNC_RESOLUTIONS,
    TRANSCRIBE_LANGUAGES,
    TTS_CREATE_MODELS,
    TTS_DESIGN_MODELS,
    VIDEO_EDIT_MODELS,
    VIDEO_GENERATE_MODELS,
    VIDEO_UPSCALE_MODELS,
)
from .errors import EverypixelMcpError, error, map_http_error
from .limits import (
    DEFAULT_POLL_INTERVAL_SECONDS,
    DEFAULT_WAIT_TIMEOUT_SECONDS,
    MAX_IMAGE_UPLOAD_BYTES,
    MAX_VIDEO_UPLOAD_BYTES,
    validate_json_payload,
    validate_wait_bounds,
)
from .media import (
    is_http_url,
    load_local_media,
    media_roots,
    resolve_url_or_data_uri,
)
from .transport import BoundedAsyncClient

DEFAULT_BASE_URL = "https://api.everypixel.com/v1"
DEFAULT_TIMEOUT_SECONDS = 60.0


def default_base_url(environ: dict[str, str] | None = None) -> str:
    env = environ if environ is not None else os.environ
    url = (env.get("EVERYPIXEL_BASE_URL") or DEFAULT_BASE_URL).strip().rstrip("/")
    if not url.startswith(("https://", "http://")):
        raise error(
            "invalid_input",
            "EVERYPIXEL_BASE_URL must start with https:// (or http:// for local tests).",
        )
    return url


def default_timeout(environ: dict[str, str] | None = None) -> float:
    env = environ if environ is not None else os.environ
    raw = env.get("EVERYPIXEL_TIMEOUT_SECONDS")
    if raw is None or raw == "":
        return DEFAULT_TIMEOUT_SECONDS
    try:
        value = float(raw)
    except ValueError as exc:
        raise error(
            "invalid_input",
            "EVERYPIXEL_TIMEOUT_SECONDS must be a positive number.",
            next_steps=["Set EVERYPIXEL_TIMEOUT_SECONDS to a positive float, e.g. 60."],
        ) from exc
    if not math.isfinite(value) or value <= 0:
        raise error(
            "invalid_input",
            "EVERYPIXEL_TIMEOUT_SECONDS must be a positive number.",
            next_steps=["Set EVERYPIXEL_TIMEOUT_SECONDS to a positive float, e.g. 60."],
        )
    return value


def resolve_credentials(
    environ: dict[str, str] | None = None,
) -> tuple[tuple[str, str] | None, str | None]:
    """Return ((client_id, client_secret), None) or (None, bearer_token)."""
    env = environ if environ is not None else os.environ
    client_id = (env.get("EVERYPIXEL_CLIENT_ID") or "").strip()
    client_secret = (env.get("EVERYPIXEL_CLIENT_SECRET") or "").strip()
    access_token = (env.get("EVERYPIXEL_ACCESS_TOKEN") or "").strip()

    if access_token and client_secret and access_token == client_secret:
        raise error(
            "invalid_input",
            "Do not use EVERYPIXEL_CLIENT_SECRET as EVERYPIXEL_ACCESS_TOKEN.",
            next_steps=[
                (
                    "Use EVERYPIXEL_CLIENT_ID + EVERYPIXEL_CLIENT_SECRET for HTTP Basic auth, "
                    "or a separate OAuth access token for EVERYPIXEL_ACCESS_TOKEN."
                ),
            ],
        )
    if client_id and client_secret:
        return (client_id, client_secret), None
    if bool(client_id) ^ bool(client_secret):
        raise error(
            "missing_credential",
            (
                "Both EVERYPIXEL_CLIENT_ID and EVERYPIXEL_CLIENT_SECRET must be set "
                "for HTTP Basic authentication."
            ),
            next_steps=[
                (
                    "Set both EVERYPIXEL_CLIENT_ID and EVERYPIXEL_CLIENT_SECRET "
                    "in .env or the environment."
                ),
            ],
        )
    if access_token:
        return None, access_token
    raise error(
        "missing_credential",
        "No Everypixel credentials found in the environment.",
        next_steps=[
            (
                "Set EVERYPIXEL_CLIENT_ID and EVERYPIXEL_CLIENT_SECRET (preferred) "
                "or EVERYPIXEL_ACCESS_TOKEN in .env."
            ),
            "Obtain keys from https://labs.everypixel.com/account/keys and never commit secrets.",
        ],
    )


def has_credentials(environ: dict[str, str] | None = None) -> bool:
    try:
        resolve_credentials(environ)
        return True
    except EverypixelMcpError:
        return False


class EverypixelClient:
    """Async client for Everypixel Labs v1 endpoints."""

    def __init__(
        self,
        *,
        client_id: str | None = None,
        client_secret: str | None = None,
        access_token: str | None = None,
        base_url: str | None = None,
        timeout_seconds: float | None = None,
        async_http_factory: Callable[..., Any] | None = None,
    ) -> None:
        self.base_url = (base_url or default_base_url()).rstrip("/")
        self.timeout_seconds = timeout_seconds if timeout_seconds is not None else default_timeout()
        if (
            isinstance(self.timeout_seconds, bool)
            or not math.isfinite(self.timeout_seconds)
            or self.timeout_seconds <= 0
        ):
            raise error("invalid_input", "Timeout must be finite and positive.")
        self._explicit_client_id = client_id
        self._explicit_client_secret = client_secret
        self._explicit_access_token = access_token
        self._async_http_factory = async_http_factory

    def _require_auth(self) -> tuple[tuple[str, str] | None, dict[str, str]]:
        if self._explicit_client_id or self._explicit_client_secret or self._explicit_access_token:
            env = {
                "EVERYPIXEL_CLIENT_ID": self._explicit_client_id or "",
                "EVERYPIXEL_CLIENT_SECRET": self._explicit_client_secret or "",
                "EVERYPIXEL_ACCESS_TOKEN": self._explicit_access_token or "",
            }
            basic, bearer = resolve_credentials(env)
        else:
            basic, bearer = resolve_credentials()
        headers: dict[str, str] = {}
        if bearer:
            headers["Authorization"] = f"Bearer {bearer}"
        return basic, headers

    def _open_async_http(self) -> Any:
        if self._async_http_factory is not None:
            return self._async_http_factory(
                base_url=self.base_url,
                timeout=self.timeout_seconds,
            )
        return BoundedAsyncClient(
            base_url=self.base_url,
            timeout=self.timeout_seconds,
        )

    async def _request(
        self,
        method: str,
        endpoint: str,
        *,
        auth_required: bool = True,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        files: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        basic_auth: tuple[str, str] | None = None
        headers: dict[str, str] = {}
        if auth_required:
            basic_auth, headers = self._require_auth()

        if json_body is not None:
            validate_json_payload(json_body)

        clean_ep = endpoint if endpoint.startswith("/") else f"/{endpoint}"
        url = f"{self.base_url}{clean_ep}"

        http = self._open_async_http()
        try:
            with anyio.fail_after(self.timeout_seconds):
                req_kwargs: dict[str, Any] = {"headers": headers}
                if basic_auth is not None:
                    req_kwargs["auth"] = basic_auth
                if params is not None:
                    req_kwargs["params"] = params
                if json_body is not None:
                    req_kwargs["json"] = json_body
                if data is not None:
                    req_kwargs["data"] = data
                if files is not None:
                    req_kwargs["files"] = files
                response = await http.request(method, url, **req_kwargs)
        except TimeoutError as exc:
            raise error(
                "request_timeout",
                f"Request to {clean_ep} timed out after {self.timeout_seconds}s.",
                retryable=True,
                next_steps=["Retry or increase EVERYPIXEL_TIMEOUT_SECONDS."],
            ) from exc
        except EverypixelMcpError:
            raise
        except httpx2.HTTPError as exc:
            raise error(
                "network_error",
                f"Network error calling Everypixel {clean_ep}.",
                retryable=True,
                next_steps=["Check network connectivity and retry."],
            ) from exc
        finally:
            with anyio.CancelScope(shield=True):
                await http.aclose()

        parsed: Any = None
        if response.content:
            try:
                parsed = json.loads(response.content.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                if 200 <= response.status_code < 300:
                    raise error(
                        "invalid_response",
                        f"Everypixel returned non-JSON content on {clean_ep}.",
                    ) from exc

        if not (200 <= response.status_code < 300):
            raise map_http_error(response.status_code, parsed, endpoint=clean_ep)

        if not isinstance(parsed, dict):
            raise error(
                "invalid_response",
                f"Expected JSON object from {clean_ep}.",
            )

        if parsed.get("status") == "error":
            raise error(
                "upstream_error",
                str(parsed.get("message") or f"Everypixel reported an error on {clean_ep}."),
                details={"endpoint": clean_ep},
                retryable=False,
                next_steps=["Check parameter values and input media format."],
            )

        req_id = response.headers.get("X-Request-ID") or response.headers.get("x-request-id")
        if req_id and "request_id" not in parsed:
            parsed = {**parsed, "request_id": req_id}
        return parsed

    async def status(
        self,
        *,
        task_id: str,
        wait: bool = False,
        wait_timeout_seconds: float = DEFAULT_WAIT_TIMEOUT_SECONDS,
        poll_interval_seconds: float = DEFAULT_POLL_INTERVAL_SECONDS,
    ) -> dict[str, Any]:
        """Check status of an async task via GET /v1/status (no auth required)."""
        if not isinstance(task_id, str) or not task_id.strip():
            raise error("invalid_input", "task_id must be a non-empty string.")
        wait, timeout_s, interval_s = validate_wait_bounds(
            wait=wait,
            wait_timeout_seconds=wait_timeout_seconds,
            poll_interval_seconds=poll_interval_seconds,
        )
        tid = task_id.strip()
        if not wait:
            return await self._request(
                "GET",
                "/status",
                auth_required=False,
                params={"task_id": tid},
            )

        try:
            with anyio.fail_after(timeout_s):
                while True:
                    state = await self._request(
                        "GET",
                        "/status",
                        auth_required=False,
                        params={"task_id": tid},
                    )
                    status_val = state.get("status")
                    if status_val == "SUCCESS":
                        return state
                    if status_val in ("FAILURE", "REVOKED"):
                        err_msg = (
                            state.get("error")
                            or state.get("message")
                            or f"Task {tid} ended with status {status_val}."
                        )
                        raise error(
                            "task_failed",
                            str(err_msg),
                            details={"task_id": tid, "task_status": status_val},
                            retryable=False,
                            next_steps=[
                                (
                                    "Inspect input media constraints and model parameters "
                                    "before submitting a new task."
                                ),
                            ],
                        )
                    await anyio.sleep(interval_s)
        except TimeoutError as exc:
            raise error(
                "wait_timeout",
                f"Task {tid} is still running after {timeout_s}s.",
                details={"task_id": tid},
                retryable=True,
                next_steps=[
                    f"Call everypixel_status with task_id='{tid}' later to retrieve the result.",
                ],
            ) from exc

    async def _maybe_wait(
        self,
        submitted: dict[str, Any],
        *,
        wait: bool,
        wait_timeout_seconds: float,
        poll_interval_seconds: float,
    ) -> dict[str, Any]:
        if not wait:
            return submitted
        task_id = submitted.get("task_id")
        if not isinstance(task_id, str) or not task_id:
            return submitted
        final_state = await self.status(
            task_id=task_id,
            wait=True,
            wait_timeout_seconds=wait_timeout_seconds,
            poll_interval_seconds=poll_interval_seconds,
        )
        merged = dict(submitted)
        merged.update(final_state)
        return merged

    async def analyze(
        self,
        *,
        operation: str,
        url: str | None = None,
        file_path: str | None = None,
        num_keywords: int | None = None,
        threshold: float | None = None,
        lang: str | None = None,
        colors: bool | None = None,
        num_colors: int | None = None,
        caption_len: str | None = None,
        allow_local_files: bool = False,
    ) -> dict[str, Any]:
        """Run synchronous recognition/quality endpoints."""
        endpoint_map = {
            "keywords": ("/keywords", "image", {".jpg", ".jpeg", ".png"}),
            "video_keywords": (
                "/video_keywords",
                "video",
                {".mp4", ".mpeg", ".mpg", ".mov", ".avi"},
            ),
            "caption": ("/image_captioning", "image", {".jpg", ".jpeg", ".png"}),
            "faces": ("/faces", "image", {".jpg", ".jpeg", ".png"}),
            "quality": ("/quality", "image", {".jpg", ".jpeg", ".png"}),
            "quality_ugc": ("/quality_ugc", "image", {".jpg", ".jpeg", ".png"}),
        }
        if operation not in endpoint_map:
            raise error(
                "invalid_input",
                f"Unsupported analyze operation '{operation}'.",
                next_steps=[f"Use one of: {', '.join(endpoint_map)}."],
            )
        if bool(url) == bool(file_path):
            raise error(
                "invalid_input",
                "Provide exactly one of 'url' or 'file_path'.",
            )

        endpoint, media_kind, valid_exts = endpoint_map[operation]
        params: dict[str, Any] = {}

        if operation in ("keywords", "video_keywords"):
            if num_keywords is not None:
                if (
                    isinstance(num_keywords, bool)
                    or not isinstance(num_keywords, int)
                    or not (1 <= num_keywords <= 50)
                ):
                    raise error(
                        "invalid_input", "num_keywords must be an integer between 1 and 50."
                    )
                params["num_keywords"] = num_keywords
            if threshold is not None:
                if (
                    isinstance(threshold, bool)
                    or not isinstance(threshold, (int, float))
                    or not math.isfinite(threshold)
                    or not (0.0 <= threshold <= 1.0)
                ):
                    raise error("invalid_input", "threshold must be a float between 0.0 and 1.0.")
                params["threshold"] = float(threshold)
        elif any(v is not None for v in (num_keywords, threshold)):
            raise error(
                "invalid_input",
                f"num_keywords and threshold are not supported for operation '{operation}'.",
            )

        if operation == "keywords":
            if lang is not None:
                if lang not in KEYWORD_LANGUAGES:
                    raise error(
                        "invalid_input",
                        f"lang must be one of {KEYWORD_LANGUAGES}.",
                    )
                params["lang"] = lang
            if colors is not None:
                if type(colors) is not bool:
                    raise error("invalid_input", "colors must be a boolean.")
                params["colors"] = colors
            if num_colors is not None:
                if (
                    isinstance(num_colors, bool)
                    or not isinstance(num_colors, int)
                    or num_colors < 1
                ):
                    raise error("invalid_input", "num_colors must be a positive integer.")
                params["num_colors"] = num_colors
        elif any(v is not None for v in (lang, colors, num_colors)):
            raise error(
                "invalid_input",
                (
                    f"lang, colors, and num_colors are only supported for "
                    f"operation='keywords' (not '{operation}')."
                ),
            )

        if operation == "caption":
            if caption_len is not None:
                if caption_len not in CAPTION_LENGTHS:
                    raise error(
                        "invalid_input",
                        f"caption_len must be one of {CAPTION_LENGTHS}.",
                    )
                params["caption_len"] = caption_len
        elif caption_len is not None:
            raise error(
                "invalid_input",
                "caption_len is only supported for operation='caption'.",
            )

        if url is not None:
            if not is_http_url(url):
                raise error("invalid_input", "url must be a valid HTTP(S) URL.")
            params["url"] = url.strip()
            return await self._request("GET", endpoint, params=params)

        assert file_path is not None
        loaded = load_local_media(
            file_path,
            kind=media_kind,
            allow_local_files=allow_local_files,
            roots=media_roots(),
            allowed_extensions=valid_exts,
        )
        return await self._request(
            "POST",
            endpoint,
            params=params or None,
            files={"data": (loaded.filename, loaded.data, loaded.mime_type)},
        )

    async def image(
        self,
        *,
        operation: str,
        prompt: str | None = None,
        model: str | None = None,
        image_url: str | None = None,
        image_path: str | None = None,
        image_urls: list[str] | None = None,
        image_paths: list[str] | None = None,
        image_from_task_id: str | None = None,
        source_url: str | None = None,
        target_url: str | None = None,
        source_path: str | None = None,
        target_path: str | None = None,
        quality: str | None = None,
        image_size: str | None = None,
        resolution: str | None = None,
        style: str | None = None,
        megapixel_ratio: float | None = None,
        seed: int | None = None,
        controls: dict[str, Any] | None = None,
        lora_url: str | None = None,
        use_gfpgan: bool | None = None,
        title: str | None = None,
        callback_url: str | None = None,
        allow_local_files: bool = False,
        wait: bool = False,
        wait_timeout_seconds: float = DEFAULT_WAIT_TIMEOUT_SECONDS,
        poll_interval_seconds: float = DEFAULT_POLL_INTERVAL_SECONDS,
    ) -> dict[str, Any]:
        """Run async image generation, editing, background removal, vectorization, or upscale."""
        wait, timeout_s, interval_s = validate_wait_bounds(
            wait=wait,
            wait_timeout_seconds=wait_timeout_seconds,
            poll_interval_seconds=poll_interval_seconds,
        )
        roots = media_roots()

        if operation == "generate":
            if not isinstance(prompt, str) or not prompt.strip():
                raise error("invalid_input", "prompt is required for image generate.")
            selected_model = (model or "zimage").strip()
            if selected_model not in IMAGE_GENERATE_MODELS:
                raise error(
                    "invalid_input",
                    f"Unsupported image_generate model '{selected_model}'.",
                    next_steps=[f"Choose from: {', '.join(IMAGE_GENERATE_MODELS)}."],
                )
            _validate_gpt_image_options(
                selected_model, quality=quality, resolution=resolution, image_size=image_size
            )
            if image_size is not None and image_size not in IMAGE_SIZES:
                raise error("invalid_input", f"image_size must be one of {IMAGE_SIZES}.")
            if controls is not None and selected_model not in (
                "recraftv4_1_vector",
                "recraftv4_1_pro_vector",
            ):
                raise error(
                    "invalid_input",
                    "controls is only supported for recraftv4_1_vector and recraftv4_1_pro_vector.",
                )
            if style == "transfer" and not (image_url or image_path):
                raise error("invalid_input", "style='transfer' requires image_url or image_path.")
            body: dict[str, Any] = {"prompt": prompt.strip(), "model": selected_model}
            if quality is not None:
                body["quality"] = quality
            if image_size is not None:
                body["image_size"] = image_size
            if resolution is not None:
                body["resolution"] = resolution
            if style is not None:
                body["style"] = style
            if image_url or image_path:
                body["image_url"] = resolve_url_or_data_uri(
                    url_or_uri=image_url,
                    file_path=image_path,
                    kind="image",
                    allow_local_files=allow_local_files,
                    roots=roots,
                    field_name="image_url",
                )
            if seed is not None:
                body["seed"] = seed
            if controls is not None:
                body["controls"] = controls
            if lora_url is not None:
                body["lora_url"] = lora_url
            if callback_url is not None:
                body["callback_url"] = callback_url
            res = await self._request("POST", "/image_generate", json_body=body)
            return await self._maybe_wait(
                res,
                wait=wait,
                wait_timeout_seconds=timeout_s,
                poll_interval_seconds=interval_s,
            )

        if operation == "edit":
            if not isinstance(prompt, str) or not prompt.strip():
                raise error("invalid_input", "prompt is required for image edit.")
            if bool(image_urls) == bool(image_paths):
                raise error(
                    "invalid_input",
                    "Provide either image_urls or image_paths (non-empty list) for image edit.",
                )
            resolved_urls: list[str] = []
            if image_urls:
                for u in image_urls:
                    resolved_urls.append(
                        resolve_url_or_data_uri(
                            url_or_uri=u,
                            kind="image",
                            allow_local_files=allow_local_files,
                            roots=roots,
                            field_name="image_urls item",
                        )
                    )
            elif image_paths:
                for p in image_paths:
                    resolved_urls.append(
                        resolve_url_or_data_uri(
                            file_path=p,
                            kind="image",
                            allow_local_files=allow_local_files,
                            roots=roots,
                            field_name="image_paths item",
                        )
                    )
            if not resolved_urls or len(resolved_urls) > 16:
                raise error("invalid_input", "image_edit requires 1 to 16 source images.")
            selected_model = (model or "flux2").strip()
            if selected_model not in IMAGE_EDIT_MODELS:
                raise error(
                    "invalid_input",
                    f"Unsupported image_edit model '{selected_model}'.",
                    next_steps=[f"Choose from: {', '.join(IMAGE_EDIT_MODELS)}."],
                )
            _validate_gpt_image_options(
                selected_model, quality=quality, resolution=resolution, image_size=image_size
            )
            if image_size is not None and image_size not in IMAGE_SIZES:
                raise error("invalid_input", f"image_size must be one of {IMAGE_SIZES}.")
            if megapixel_ratio is not None and (
                isinstance(megapixel_ratio, bool)
                or not isinstance(megapixel_ratio, (int, float))
                or not (0.5 <= float(megapixel_ratio) <= 1.5)
            ):
                raise error("invalid_input", "megapixel_ratio must be between 0.5 and 1.5.")
            body = {
                "prompt": prompt.strip(),
                "image_urls": resolved_urls,
                "model": selected_model,
            }
            if quality is not None:
                body["quality"] = quality
            if resolution is not None:
                body["resolution"] = resolution
            if image_size is not None:
                body["image_size"] = image_size
            if megapixel_ratio is not None:
                body["megapixel_ratio"] = float(megapixel_ratio)
            if seed is not None:
                body["seed"] = seed
            if callback_url is not None:
                body["callback_url"] = callback_url
            res = await self._request("POST", "/image_edit", json_body=body)
            return await self._maybe_wait(
                res,
                wait=wait,
                wait_timeout_seconds=timeout_s,
                poll_interval_seconds=interval_s,
            )

        if operation == "remove_background":
            if model is not None:
                raise error(
                    "invalid_input",
                    "remove_background does not accept a 'model' parameter.",
                )
            resolved_img = resolve_url_or_data_uri(
                url_or_uri=image_url,
                file_path=image_path,
                kind="image",
                allow_local_files=allow_local_files,
                roots=roots,
                field_name="image_url",
            )
            body = {"image_url": resolved_img}
            if callback_url is not None:
                body["callback_url"] = callback_url
            res = await self._request("POST", "/image_remove_background", json_body=body)
            return await self._maybe_wait(
                res,
                wait=wait,
                wait_timeout_seconds=timeout_s,
                poll_interval_seconds=interval_s,
            )

        if operation == "vectorize":
            if model is not None:
                raise error(
                    "invalid_input",
                    "vectorize does not accept a 'model' parameter.",
                )
            resolved_img = resolve_url_or_data_uri(
                url_or_uri=image_url,
                file_path=image_path,
                kind="image",
                allow_local_files=allow_local_files,
                roots=roots,
                allowed_extensions={".png", ".jpg", ".jpeg", ".webp"},
                max_bytes=10 * 1024 * 1024,
                field_name="image_url",
            )
            body = {"image_url": resolved_img}
            if callback_url is not None:
                body["callback_url"] = callback_url
            res = await self._request("POST", "/image_vectorize", json_body=body)
            return await self._maybe_wait(
                res,
                wait=wait,
                wait_timeout_seconds=timeout_s,
                poll_interval_seconds=interval_s,
            )

        if operation == "upscale":
            has_direct = bool(image_url or image_path)
            has_task = bool(image_from_task_id and image_from_task_id.strip())
            if has_direct == has_task:
                raise error(
                    "invalid_input",
                    (
                        "Provide exactly one of image_url/image_path or "
                        "image_from_task_id for image upscale."
                    ),
                )
            selected_model = (model or "seedvr2").strip()
            if selected_model not in IMAGE_UPSCALE_MODELS:
                raise error(
                    "invalid_input",
                    f"image upscale model must be one of {IMAGE_UPSCALE_MODELS}.",
                )
            body = {"model": selected_model}
            if has_direct:
                body["image_url"] = resolve_url_or_data_uri(
                    url_or_uri=image_url,
                    file_path=image_path,
                    kind="image",
                    allow_local_files=allow_local_files,
                    roots=roots,
                    field_name="image_url",
                )
            else:
                assert image_from_task_id is not None
                body["image_from_task_id"] = image_from_task_id.strip()
            if callback_url is not None:
                body["callback_url"] = callback_url
            res = await self._request("POST", "/image_upscale", json_body=body)
            return await self._maybe_wait(
                res,
                wait=wait,
                wait_timeout_seconds=timeout_s,
                poll_interval_seconds=interval_s,
            )

        if operation == "face_swap":
            res = await self._face_swap(
                endpoint="/imageswap/create",
                target_kind="image",
                source_url=source_url,
                target_url=target_url,
                source_path=source_path,
                target_path=target_path,
                use_gfpgan=use_gfpgan,
                title=title,
                callback_url=callback_url,
                allow_local_files=allow_local_files,
                roots=roots,
            )
            return await self._maybe_wait(
                res,
                wait=wait,
                wait_timeout_seconds=timeout_s,
                poll_interval_seconds=interval_s,
            )

        raise error(
            "invalid_input",
            f"Unsupported image operation '{operation}'.",
            next_steps=["Use generate, edit, remove_background, vectorize, upscale, or face_swap."],
        )

    async def _face_swap(
        self,
        *,
        endpoint: str,
        target_kind: str,
        source_url: str | None,
        target_url: str | None,
        source_path: str | None,
        target_path: str | None,
        use_gfpgan: bool | None,
        title: str | None,
        callback_url: str | None,
        allow_local_files: bool,
        roots: list[Any],
    ) -> dict[str, Any]:
        using_urls = bool(source_url or target_url)
        using_paths = bool(source_path or target_path)
        if using_urls == using_paths:
            raise error(
                "invalid_input",
                "Provide either (source_url and target_url) or (source_path and target_path).",
            )
        if using_urls:
            if not (
                source_url and target_url and is_http_url(source_url) and is_http_url(target_url)
            ):
                raise error(
                    "invalid_input",
                    "Both source_url and target_url must be valid HTTP(S) URLs.",
                )
            params: dict[str, Any] = {
                "source_url": source_url.strip(),
                "target_url": target_url.strip(),
            }
            if use_gfpgan is not None:
                params["use_gfpgan"] = bool(use_gfpgan)
            if title is not None:
                params["title"] = title
            if callback_url is not None:
                params["callback"] = callback_url
            return await self._request("GET", endpoint, params=params)

        if not (source_path and target_path):
            raise error(
                "invalid_input", "Both source_path and target_path are required for local upload."
            )
        source_media = load_local_media(
            source_path,
            kind="image",
            allow_local_files=allow_local_files,
            roots=roots,
            max_bytes=MAX_IMAGE_UPLOAD_BYTES,
        )
        target_media = load_local_media(
            target_path,
            kind=target_kind,
            allow_local_files=allow_local_files,
            roots=roots,
            max_bytes=MAX_VIDEO_UPLOAD_BYTES if target_kind == "video" else MAX_IMAGE_UPLOAD_BYTES,
        )
        form_data: dict[str, Any] = {
            "use_gfpgan": bool(use_gfpgan) if use_gfpgan is not None else False,
        }
        if title is not None:
            form_data["title"] = title
        if callback_url is not None:
            form_data["callback"] = callback_url
        return await self._request(
            "POST",
            endpoint,
            data=form_data,
            files={
                "source": (source_media.filename, source_media.data, source_media.mime_type),
                "target": (target_media.filename, target_media.data, target_media.mime_type),
            },
        )

    async def video(
        self,
        *,
        operation: str,
        model: str | None = None,
        prompt: str | None = None,
        video_url: str | None = None,
        video_path: str | None = None,
        video_from_task_id: str | None = None,
        image_url: str | None = None,
        image_path: str | None = None,
        image_last_url: str | None = None,
        reference_image_urls: list[str] | None = None,
        reference_video_urls: list[str] | None = None,
        reference_audio_urls: list[str] | None = None,
        content: list[dict[str, Any]] | None = None,
        keyframes: list[dict[str, Any]] | None = None,
        duration: int | None = None,
        resolution: str | None = None,
        aspect_ratio: str | None = None,
        target_aspect_ratio: str | None = None,
        public_figure_threshold: str | None = None,
        generate_audio: bool | None = None,
        seed: int | None = None,
        source_url: str | None = None,
        target_url: str | None = None,
        source_path: str | None = None,
        target_path: str | None = None,
        use_gfpgan: bool | None = None,
        title: str | None = None,
        callback_url: str | None = None,
        allow_local_files: bool = False,
        wait: bool = False,
        wait_timeout_seconds: float = DEFAULT_WAIT_TIMEOUT_SECONDS,
        poll_interval_seconds: float = DEFAULT_POLL_INTERVAL_SECONDS,
    ) -> dict[str, Any]:
        """Run async video generation, editing, upscaling, matting, soundtrack, or face swap."""
        wait, timeout_s, interval_s = validate_wait_bounds(
            wait=wait,
            wait_timeout_seconds=wait_timeout_seconds,
            poll_interval_seconds=poll_interval_seconds,
        )
        roots = media_roots()

        if operation == "generate":
            if not isinstance(model, str) or model.strip() not in VIDEO_GENERATE_MODELS:
                raise error(
                    "invalid_input",
                    f"video generate requires model in {VIDEO_GENERATE_MODELS}.",
                )
            if not isinstance(prompt, str) or not prompt.strip():
                raise error("invalid_input", "prompt is required for video generate.")
            selected_model = model.strip()
            if selected_model in ("grok-imagine-1.5", "grok15") and not (image_url or image_path):
                raise error(
                    "invalid_input",
                    f"{selected_model} requires image_url or image_path as the first frame.",
                )
            body: dict[str, Any] = {
                "model": selected_model,
                "prompt": prompt.strip(),
            }
            if duration is not None:
                if isinstance(duration, bool) or not isinstance(duration, int) or duration < 1:
                    raise error("invalid_input", "duration must be a positive integer.")
                body["duration"] = duration
            if resolution is not None:
                body["resolution"] = resolution
            if aspect_ratio is not None:
                body["aspect_ratio"] = aspect_ratio
            if generate_audio is not None:
                body["generate_audio"] = bool(generate_audio)
            if seed is not None:
                body["seed"] = seed
            if image_url or image_path:
                body["image_url"] = resolve_url_or_data_uri(
                    url_or_uri=image_url,
                    file_path=image_path,
                    kind="image",
                    allow_local_files=allow_local_files,
                    roots=roots,
                    field_name="image_url",
                )
            if image_last_url is not None:
                body["image_last_url"] = image_last_url
            if reference_image_urls is not None:
                body["reference_image_urls"] = reference_image_urls
            if reference_video_urls is not None:
                body["reference_video_urls"] = reference_video_urls
            if reference_audio_urls is not None:
                body["reference_audio_urls"] = reference_audio_urls
            if callback_url is not None:
                body["callback_url"] = callback_url
            res = await self._request("POST", "/video_generate", json_body=body)
            return await self._maybe_wait(
                res,
                wait=wait,
                wait_timeout_seconds=timeout_s,
                poll_interval_seconds=interval_s,
            )

        if operation == "edit":
            if not isinstance(model, str) or model.strip() not in VIDEO_EDIT_MODELS:
                raise error(
                    "invalid_input",
                    f"video edit requires model in {VIDEO_EDIT_MODELS}.",
                )
            selected_model = model.strip()
            if selected_model != "aleph2" and (not isinstance(prompt, str) or not prompt.strip()):
                raise error(
                    "invalid_input",
                    f"prompt is required for video edit with model='{selected_model}'.",
                )
            if selected_model == "gemini-omni-1.1-flash":
                if not video_from_task_id:
                    raise error(
                        "invalid_input",
                        "gemini-omni-1.1-flash video edit requires video_from_task_id.",
                    )
                if any(
                    v is not None
                    for v in (
                        video_url,
                        video_path,
                        duration,
                        aspect_ratio,
                        generate_audio,
                        reference_image_urls,
                    )
                ):
                    raise error(
                        "invalid_input",
                        (
                            "For gemini-omni-1.1-flash video edit, omit video_url, duration, "
                            "aspect_ratio, reference_image_urls, and generate_audio."
                        ),
                    )
            else:
                sources_count = (
                    int(bool(video_url or video_path))
                    + int(bool(video_from_task_id))
                    + int(bool(content))
                )
                if sources_count == 0:
                    raise error(
                        "invalid_input",
                        (
                            "Provide a video source via video_url/video_path, "
                            "video_from_task_id, or content."
                        ),
                    )
                if int(bool(video_url or video_path)) + int(bool(video_from_task_id)) > 1:
                    raise error(
                        "invalid_input",
                        "Provide either video_url/video_path or video_from_task_id, not both.",
                    )

            body = {"model": selected_model}
            if prompt is not None:
                body["prompt"] = prompt.strip()
            if video_url or video_path:
                body["video_url"] = resolve_url_or_data_uri(
                    url_or_uri=video_url,
                    file_path=video_path,
                    kind="video",
                    allow_local_files=allow_local_files,
                    roots=roots,
                    field_name="video_url",
                )
            if video_from_task_id is not None:
                body["video_from_task_id"] = video_from_task_id.strip()
            if content is not None:
                body["content"] = content
            if keyframes is not None:
                body["keyframes"] = keyframes
            if reference_image_urls is not None:
                body["reference_image_urls"] = reference_image_urls
            if duration is not None:
                body["duration"] = duration
            if resolution is not None:
                body["resolution"] = resolution
            if aspect_ratio is not None:
                body["aspect_ratio"] = aspect_ratio
            if target_aspect_ratio is not None:
                body["target_aspect_ratio"] = target_aspect_ratio
            if public_figure_threshold is not None:
                body["public_figure_threshold"] = public_figure_threshold
            if generate_audio is not None:
                body["generate_audio"] = bool(generate_audio)
            if seed is not None:
                body["seed"] = seed
            if callback_url is not None:
                body["callback_url"] = callback_url
            res = await self._request("POST", "/video_edit", json_body=body)
            return await self._maybe_wait(
                res,
                wait=wait,
                wait_timeout_seconds=timeout_s,
                poll_interval_seconds=interval_s,
            )

        if operation == "upscale":
            selected_model = (model or "seedvr2").strip()
            if selected_model not in VIDEO_UPSCALE_MODELS:
                raise error(
                    "invalid_input",
                    f"video upscale model must be one of {VIDEO_UPSCALE_MODELS}.",
                )
            if resolution is not None:
                allowed_res = (
                    ("720p", "1080p", "1440p")
                    if selected_model == "seedvr2"
                    else ("720p", "1080p", "1440p", "4k")
                )
                if resolution not in allowed_res:
                    raise error(
                        "invalid_input",
                        f"resolution for {selected_model} must be one of {allowed_res}.",
                    )
            resolved_vid = resolve_url_or_data_uri(
                url_or_uri=video_url,
                file_path=video_path,
                kind="video",
                allow_local_files=allow_local_files,
                roots=roots,
                field_name="video_url",
            )
            body = {"video_url": resolved_vid, "model": selected_model}
            if resolution is not None:
                body["resolution"] = resolution
            if callback_url is not None:
                body["callback_url"] = callback_url
            res = await self._request("POST", "/video_upscale", json_body=body)
            return await self._maybe_wait(
                res,
                wait=wait,
                wait_timeout_seconds=timeout_s,
                poll_interval_seconds=interval_s,
            )

        if operation == "matting":
            if model is not None or resolution is not None:
                raise error(
                    "invalid_input",
                    "video matting does not accept model or resolution parameters.",
                )
            resolved_vid = resolve_url_or_data_uri(
                url_or_uri=video_url,
                file_path=video_path,
                kind="video",
                allow_local_files=allow_local_files,
                roots=roots,
                field_name="video_url",
            )
            body = {"video_url": resolved_vid}
            if prompt is not None:
                if not isinstance(prompt, str) or not prompt.strip():
                    raise error(
                        "invalid_input", "prompt for video matting must be non-empty when provided."
                    )
                body["prompt"] = prompt.strip()
            if callback_url is not None:
                body["callback_url"] = callback_url
            res = await self._request("POST", "/video_matting", json_body=body)
            return await self._maybe_wait(
                res,
                wait=wait,
                wait_timeout_seconds=timeout_s,
                poll_interval_seconds=interval_s,
            )

        if operation == "soundtrack":
            if model is not None or resolution is not None:
                raise error(
                    "invalid_input",
                    "video soundtrack does not accept model or resolution parameters.",
                )
            resolved_vid = resolve_url_or_data_uri(
                url_or_uri=video_url,
                file_path=video_path,
                kind="video",
                allow_local_files=allow_local_files,
                roots=roots,
                field_name="video_url",
            )
            body = {"video_url": resolved_vid}
            if prompt is not None:
                if len(prompt) > 2000:
                    raise error(
                        "invalid_input", "video soundtrack prompt must be at most 2000 characters."
                    )
                body["prompt"] = prompt
            if seed is not None:
                body["seed"] = seed
            if callback_url is not None:
                body["callback_url"] = callback_url
            res = await self._request("POST", "/video_soundtrack", json_body=body)
            return await self._maybe_wait(
                res,
                wait=wait,
                wait_timeout_seconds=timeout_s,
                poll_interval_seconds=interval_s,
            )

        if operation == "face_swap":
            res = await self._face_swap(
                endpoint="/videoswap/create",
                target_kind="video",
                source_url=source_url,
                target_url=target_url,
                source_path=source_path,
                target_path=target_path,
                use_gfpgan=use_gfpgan,
                title=title,
                callback_url=callback_url,
                allow_local_files=allow_local_files,
                roots=roots,
            )
            return await self._maybe_wait(
                res,
                wait=wait,
                wait_timeout_seconds=timeout_s,
                poll_interval_seconds=interval_s,
            )

        raise error(
            "invalid_input",
            f"Unsupported video operation '{operation}'.",
            next_steps=["Use generate, edit, upscale, matting, soundtrack, or face_swap."],
        )

    async def lipsync(
        self,
        *,
        operation: str,
        audio_url: str | None = None,
        audio_path: str | None = None,
        image_url: str | None = None,
        image_path: str | None = None,
        video_url: str | None = None,
        video_path: str | None = None,
        model: str | None = None,
        resolution: str | None = None,
        callback_url: str | None = None,
        allow_local_files: bool = False,
        wait: bool = False,
        wait_timeout_seconds: float = DEFAULT_WAIT_TIMEOUT_SECONDS,
        poll_interval_seconds: float = DEFAULT_POLL_INTERVAL_SECONDS,
    ) -> dict[str, Any]:
        """Run image_lipsync or video_lipsync (requires Data URI payloads)."""
        wait, timeout_s, interval_s = validate_wait_bounds(
            wait=wait,
            wait_timeout_seconds=wait_timeout_seconds,
            poll_interval_seconds=poll_interval_seconds,
        )
        roots = media_roots()

        if resolution is not None and resolution not in LIPSYNC_RESOLUTIONS:
            raise error(
                "invalid_input",
                f"lipsync resolution must be one of {LIPSYNC_RESOLUTIONS}.",
            )

        audio_data_uri = resolve_url_or_data_uri(
            url_or_uri=audio_url,
            file_path=audio_path,
            kind="audio",
            allow_local_files=allow_local_files,
            require_data_uri=True,
            roots=roots,
            field_name="audio_url",
        )

        if operation == "image_lipsync":
            if model is not None and model not in IMAGE_LIPSYNC_MODELS:
                raise error(
                    "invalid_input",
                    f"image_lipsync model must be one of {IMAGE_LIPSYNC_MODELS}.",
                )
            image_data_uri = resolve_url_or_data_uri(
                url_or_uri=image_url,
                file_path=image_path,
                kind="image",
                allow_local_files=allow_local_files,
                require_data_uri=True,
                roots=roots,
                field_name="image_url",
            )
            body: dict[str, Any] = {
                "audio_url": audio_data_uri,
                "image_url": image_data_uri,
            }
            if model is not None:
                body["model"] = model
            if resolution is not None:
                body["resolution"] = resolution
            if callback_url is not None:
                body["callback_url"] = callback_url
            res = await self._request("POST", "/image_lipsync", json_body=body)
            return await self._maybe_wait(
                res,
                wait=wait,
                wait_timeout_seconds=timeout_s,
                poll_interval_seconds=interval_s,
            )

        if operation == "video_lipsync":
            if model is not None:
                raise error(
                    "invalid_input",
                    "video_lipsync does not accept a 'model' parameter.",
                )
            video_data_uri = resolve_url_or_data_uri(
                url_or_uri=video_url,
                file_path=video_path,
                kind="video",
                allow_local_files=allow_local_files,
                require_data_uri=True,
                roots=roots,
                field_name="video_url",
            )
            body = {
                "audio_url": audio_data_uri,
                "video_url": video_data_uri,
            }
            if resolution is not None:
                body["resolution"] = resolution
            if callback_url is not None:
                body["callback_url"] = callback_url
            res = await self._request("POST", "/video_lipsync", json_body=body)
            return await self._maybe_wait(
                res,
                wait=wait,
                wait_timeout_seconds=timeout_s,
                poll_interval_seconds=interval_s,
            )

        raise error(
            "invalid_input",
            f"Unsupported lipsync operation '{operation}'.",
            next_steps=["Use 'image_lipsync' or 'video_lipsync'."],
        )

    async def tts(
        self,
        *,
        operation: str,
        model: str | None = None,
        text: str | None = None,
        prompt: str | None = None,
        speaker: str | None = None,
        voice_id: str | None = None,
        character: str | None = None,
        style: str | None = None,
        language: str | None = None,
        seed: int | None = None,
        audio_url: str | None = None,
        audio_path: str | None = None,
        audio_urls: list[str] | None = None,
        audio_paths: list[str] | None = None,
        name: str | None = None,
        provider: str | None = None,
        preview_id: str | None = None,
        description: str | None = None,
        offset: int | None = None,
        limit: int | None = None,
        callback_url: str | None = None,
        confirmed: bool = False,
        allow_local_files: bool = False,
        wait: bool = False,
        wait_timeout_seconds: float = DEFAULT_WAIT_TIMEOUT_SECONDS,
        poll_interval_seconds: float = DEFAULT_POLL_INTERVAL_SECONDS,
    ) -> dict[str, Any]:
        """Run Text-to-Speech synthesis, cloning, voice design, or voice library CRUD."""
        wait, timeout_s, interval_s = validate_wait_bounds(
            wait=wait,
            wait_timeout_seconds=wait_timeout_seconds,
            poll_interval_seconds=poll_interval_seconds,
        )
        roots = media_roots()

        if operation == "create":
            selected_model = (model or "qwen3").strip()
            if selected_model not in TTS_CREATE_MODELS:
                raise error(
                    "invalid_input",
                    f"tts create model must be one of {TTS_CREATE_MODELS}.",
                )
            if not isinstance(text, str) or not text:
                raise error("invalid_input", "text is required for tts create.")
            max_chars = 200 if selected_model == "qwen3" else 2048
            if len(text) > max_chars:
                raise error(
                    "invalid_input",
                    f"text for model '{selected_model}' must be 1 to {max_chars} characters.",
                )
            if selected_model != "qwen3":
                if not voice_id:
                    raise error(
                        "invalid_input",
                        f"ElevenLabs model '{selected_model}' requires a saved voice_id.",
                    )
                if any(v is not None for v in (prompt, speaker, character, style, language, seed)):
                    raise error(
                        "invalid_input",
                        (
                            "ElevenLabs tts create rejects prompt, speaker, "
                            "character, style, language, and seed."
                        ),
                    )
            else:
                if prompt is not None and len(prompt) > 1000:
                    raise error(
                        "invalid_input", "Qwen tts create prompt must be at most 1000 characters."
                    )

            body: dict[str, Any] = {"model": selected_model, "text": text}
            if speaker is not None:
                body["speaker"] = speaker
            if voice_id is not None:
                body["voice_id"] = voice_id
            if prompt is not None:
                body["prompt"] = prompt
            if character is not None:
                body["character"] = character
            if style is not None:
                body["style"] = style
            if language is not None:
                body["language"] = language
            if seed is not None:
                body["seed"] = seed
            if callback_url is not None:
                body["callback_url"] = callback_url
            res = await self._request("POST", "/tts_create", json_body=body)
            return await self._maybe_wait(
                res,
                wait=wait,
                wait_timeout_seconds=timeout_s,
                poll_interval_seconds=interval_s,
            )

        if operation == "clone":
            selected_model = (model or "qwen3").strip()
            if selected_model != "qwen3":
                raise error("invalid_input", "tts clone only supports model='qwen3'.")
            if not isinstance(text, str) or not (1 <= len(text) <= 200):
                raise error("invalid_input", "tts clone requires text of 1 to 200 characters.")
            has_audio = bool(audio_url or audio_path)
            has_voice = bool(voice_id and voice_id.strip())
            if has_audio == has_voice:
                raise error(
                    "invalid_input",
                    "tts clone requires exactly one of audio_url/audio_path or voice_id.",
                )
            body = {"model": "qwen3", "text": text}
            if has_audio:
                body["audio_url"] = resolve_url_or_data_uri(
                    url_or_uri=audio_url,
                    file_path=audio_path,
                    kind="audio",
                    allow_local_files=allow_local_files,
                    roots=roots,
                    field_name="audio_url",
                )
            else:
                assert voice_id is not None
                body["voice_id"] = voice_id.strip()
            if callback_url is not None:
                body["callback_url"] = callback_url
            res = await self._request("POST", "/tts_clone", json_body=body)
            return await self._maybe_wait(
                res,
                wait=wait,
                wait_timeout_seconds=timeout_s,
                poll_interval_seconds=interval_s,
            )

        if operation == "design":
            selected_model = (model or "qwen3").strip()
            if selected_model not in TTS_DESIGN_MODELS:
                raise error(
                    "invalid_input",
                    f"tts design model must be one of {TTS_DESIGN_MODELS}.",
                )
            if not isinstance(text, str) or not text:
                raise error("invalid_input", "text is required for tts design.")
            if not isinstance(prompt, str) or not prompt:
                raise error("invalid_input", "prompt is required for tts design.")
            if selected_model == "qwen3":
                if len(text) > 200 or len(prompt) > 1000:
                    raise error(
                        "invalid_input",
                        "Qwen tts design requires text (1-200 chars) and prompt (1-1000 chars).",
                    )
            else:
                if not (100 <= len(text) <= 1000) or not (20 <= len(prompt) <= 1000):
                    raise error(
                        "invalid_input",
                        (
                            "ElevenLabs tts design requires text (100-1000 chars) "
                            "and prompt (20-1000 chars)."
                        ),
                    )
            body = {"model": selected_model, "text": text, "prompt": prompt}
            if callback_url is not None:
                body["callback_url"] = callback_url
            res = await self._request("POST", "/tts_design", json_body=body)
            return await self._maybe_wait(
                res,
                wait=wait,
                wait_timeout_seconds=timeout_s,
                poll_interval_seconds=interval_s,
            )

        if operation == "save_voice":
            if not isinstance(name, str) or not name.strip():
                raise error("invalid_input", "name is required for save_voice.")
            has_samples = bool(audio_urls or audio_paths)
            has_preview = bool(preview_id and preview_id.strip())
            if has_samples == has_preview:
                raise error(
                    "invalid_input",
                    "save_voice requires either audio_urls/audio_paths OR preview_id, not both.",
                )
            body = {"name": name.strip()}
            if description is not None:
                body["description"] = description
            if has_preview:
                if provider is not None:
                    raise error(
                        "invalid_input",
                        "Do not pass 'provider' when saving a voice from preview_id.",
                    )
                assert preview_id is not None
                body["preview_id"] = preview_id.strip()
            else:
                if bool(audio_urls) == bool(audio_paths):
                    raise error(
                        "invalid_input",
                        "Provide either audio_urls or audio_paths for save_voice.",
                    )
                prov = (provider or "labs").strip()
                if prov not in ("labs", "elevenlabs"):
                    raise error("invalid_input", "provider must be 'labs' or 'elevenlabs'.")
                resolved_samples: list[str] = []
                if audio_urls:
                    for u in audio_urls:
                        resolved_samples.append(
                            resolve_url_or_data_uri(
                                url_or_uri=u,
                                kind="audio",
                                allow_local_files=allow_local_files,
                                roots=roots,
                                field_name="audio_urls item",
                            )
                        )
                elif audio_paths:
                    for p in audio_paths:
                        resolved_samples.append(
                            resolve_url_or_data_uri(
                                file_path=p,
                                kind="audio",
                                allow_local_files=allow_local_files,
                                roots=roots,
                                field_name="audio_paths item",
                            )
                        )
                max_samples = 1 if prov == "labs" else 10
                if not (1 <= len(resolved_samples) <= max_samples):
                    raise error(
                        "invalid_input",
                        f"provider='{prov}' accepts 1 to {max_samples} audio sample(s).",
                    )
                body["provider"] = prov
                body["audio_urls"] = resolved_samples
            return await self._request("POST", "/tts_voice", json_body=body)

        if operation == "list_voices":
            params: dict[str, Any] = {}
            if provider is not None:
                if provider not in ("labs", "elevenlabs"):
                    raise error("invalid_input", "provider must be 'labs' or 'elevenlabs'.")
                params["provider"] = provider
            if offset is not None:
                if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
                    raise error("invalid_input", "offset must be a non-negative integer.")
                params["offset"] = offset
            if limit is not None:
                if isinstance(limit, bool) or not isinstance(limit, int) or not (1 <= limit <= 100):
                    raise error("invalid_input", "limit must be an integer between 1 and 100.")
                params["limit"] = limit
            return await self._request("GET", "/tts_voices", params=params or None)

        if operation == "delete_voice":
            if not isinstance(voice_id, str) or not voice_id.strip():
                raise error("invalid_input", "voice_id is required for delete_voice.")
            if type(confirmed) is not bool or not confirmed:
                raise error(
                    "confirmation_required",
                    "Deleting a saved voice is destructive and requires confirmed=true.",
                    next_steps=[
                        "Confirm the target voice_id with the user and pass confirmed=true."
                    ],
                )
            return await self._request(
                "DELETE",
                "/tts_voice",
                params={"voice_id": voice_id.strip()},
            )

        raise error(
            "invalid_input",
            f"Unsupported tts operation '{operation}'.",
            next_steps=["Use create, clone, design, save_voice, list_voices, or delete_voice."],
        )

    async def transcribe(
        self,
        *,
        audio_url: str | None = None,
        audio_path: str | None = None,
        language: str = "auto",
        hints: str | None = None,
        denoise: bool = True,
        callback_url: str | None = None,
        allow_local_files: bool = False,
        wait: bool = False,
        wait_timeout_seconds: float = DEFAULT_WAIT_TIMEOUT_SECONDS,
        poll_interval_seconds: float = DEFAULT_POLL_INTERVAL_SECONDS,
    ) -> dict[str, Any]:
        """Submit audio for speech-to-text transcription via POST /v1/transcribe."""
        wait, timeout_s, interval_s = validate_wait_bounds(
            wait=wait,
            wait_timeout_seconds=wait_timeout_seconds,
            poll_interval_seconds=poll_interval_seconds,
        )
        if language not in TRANSCRIBE_LANGUAGES:
            raise error(
                "invalid_input",
                f"Unsupported transcribe language '{language}'.",
                next_steps=[f"Choose from: {', '.join(TRANSCRIBE_LANGUAGES[:10])}, ..."],
            )
        if type(denoise) is not bool:
            raise error("invalid_input", "denoise must be a boolean.")
        resolved_audio = resolve_url_or_data_uri(
            url_or_uri=audio_url,
            file_path=audio_path,
            kind="audio",
            allow_local_files=allow_local_files,
            roots=media_roots(),
            field_name="audio_url",
        )
        body: dict[str, Any] = {
            "audio_url": resolved_audio,
            "language": language,
            "denoise": denoise,
        }
        if hints is not None:
            body["hints"] = hints
        if callback_url is not None:
            body["callback_url"] = callback_url
        res = await self._request("POST", "/transcribe", json_body=body)
        return await self._maybe_wait(
            res,
            wait=wait,
            wait_timeout_seconds=timeout_s,
            poll_interval_seconds=interval_s,
        )

    async def chat(
        self,
        *,
        messages: list[dict[str, Any]],
        model: str = "glm-5.3",
        max_tokens: int | None = None,
        max_completion_tokens: int | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
        do_sample: bool | None = None,
        reasoning_effort: str | None = None,
        thinking: dict[str, Any] | None = None,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | None = None,
        stop: str | list[str] | None = None,
        response_format: dict[str, Any] | None = None,
        user: str | None = None,
    ) -> dict[str, Any]:
        """Call POST /v1/chat/completions with GLM-5.3."""
        if model not in CHAT_MODELS:
            raise error(
                "invalid_input",
                f"Unsupported chat model '{model}'. Allowed: {CHAT_MODELS}.",
            )
        if not isinstance(messages, list) or not messages:
            raise error("invalid_input", "messages must be a non-empty list of message objects.")
        allowed_roles = {"system", "developer", "user", "assistant", "tool"}
        has_user_or_tool = False
        for msg in messages:
            if not isinstance(msg, dict):
                raise error("invalid_input", "Each item in messages must be an object.")
            role = msg.get("role")
            if role not in allowed_roles:
                raise error(
                    "invalid_input",
                    f"Message role '{role}' must be one of {sorted(allowed_roles)}.",
                )
            if role in ("user", "tool"):
                has_user_or_tool = True
            content = msg.get("content")
            if content is None:
                if role != "assistant" or not msg.get("tool_calls"):
                    raise error(
                        "invalid_input",
                        (
                            "Message content may be null only for an assistant "
                            "message with tool_calls."
                        ),
                    )
            elif isinstance(content, list):
                for part in content:
                    if not isinstance(part, dict) or part.get("type") != "text":
                        raise error(
                            "invalid_input",
                            (
                                "Only text content parts ({'type': 'text', 'text': '...'}) "
                                "are accepted in chat."
                            ),
                        )
            elif not isinstance(content, str):
                raise error(
                    "invalid_input", "Message content must be a string or list of text parts."
                )

        if not has_user_or_tool:
            raise error(
                "invalid_input",
                "messages must contain at least one 'user' or 'tool' message.",
            )
        if max_tokens is not None and max_completion_tokens is not None:
            raise error(
                "invalid_input",
                "Send at most one of max_tokens or max_completion_tokens.",
            )
        for tok_name, tok_val in (
            ("max_tokens", max_tokens),
            ("max_completion_tokens", max_completion_tokens),
        ):
            if tok_val is not None and (
                isinstance(tok_val, bool)
                or not isinstance(tok_val, int)
                or not (1 <= tok_val <= 131072)
            ):
                raise error("invalid_input", f"{tok_name} must be an integer between 1 and 131072.")

        if temperature is not None and (
            isinstance(temperature, bool)
            or not isinstance(temperature, (int, float))
            or not (0.0 <= float(temperature) <= 1.0)
        ):
            raise error("invalid_input", "temperature must be between 0.0 and 1.0.")
        if top_p is not None and (
            isinstance(top_p, bool)
            or not isinstance(top_p, (int, float))
            or not (0.01 <= float(top_p) <= 1.0)
        ):
            raise error("invalid_input", "top_p must be between 0.01 and 1.0.")
        if reasoning_effort is not None and reasoning_effort not in ("low", "high", "max"):
            raise error("invalid_input", "reasoning_effort must be 'low', 'high', or 'max'.")
        if tool_choice is not None and (tool_choice != "auto" or not tools):
            raise error("invalid_input", "tool_choice must be 'auto' and requires tools.")
        if user is not None and (not isinstance(user, str) or not (6 <= len(user) <= 128)):
            raise error("invalid_input", "user identifier must be 6 to 128 characters.")

        body: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
        }
        if max_tokens is not None:
            body["max_tokens"] = max_tokens
        if max_completion_tokens is not None:
            body["max_completion_tokens"] = max_completion_tokens
        if temperature is not None:
            body["temperature"] = float(temperature)
        if top_p is not None:
            body["top_p"] = float(top_p)
        if do_sample is not None:
            body["do_sample"] = bool(do_sample)
        if reasoning_effort is not None:
            body["reasoning_effort"] = reasoning_effort
        if thinking is not None:
            body["thinking"] = thinking
        if tools is not None:
            body["tools"] = tools
        if tool_choice is not None:
            body["tool_choice"] = tool_choice
        if stop is not None:
            body["stop"] = stop
        if response_format is not None:
            body["response_format"] = response_format
        if user is not None:
            body["user"] = user

        return await self._request("POST", "/chat/completions", json_body=body)


def _validate_gpt_image_options(
    model: str,
    *,
    quality: str | None,
    resolution: str | None,
    image_size: str | None,
) -> None:
    if quality is not None:
        if model == "gpt-image-2":
            allowed_q = ("low", "medium", "high")
        elif model == "gpt-image-2.5-sunburst":
            allowed_q = ("low", "medium", "high", "xhigh", "max")
        else:
            raise error(
                "invalid_input",
                f"quality is only supported on GPT Image models, not '{model}'.",
            )
        if quality not in allowed_q:
            raise error(
                "invalid_input",
                f"quality for {model} must be one of {allowed_q}.",
            )
    if (
        model in ("gpt-image-2", "gpt-image-2.5-sunburst")
        and resolution == "3k"
        and image_size not in (None, "square")
    ):
        raise error(
            "invalid_input",
            f"{model} at resolution='3k' supports only image_size='square'.",
        )
