"""Maintained-SDK MCP adapter exposing Everypixel Labs API v1."""

from __future__ import annotations

import json
from collections.abc import Callable
from importlib.metadata import PackageNotFoundError, version
from typing import Annotated, Any

from mcp.server import MCPServer
from mcp.types import ToolAnnotations
from pydantic import Field

from .catalog import CATALOG
from .client import EverypixelClient
from .errors import EverypixelMcpError, error
from .limits import (
    DEFAULT_POLL_INTERVAL_SECONDS,
    DEFAULT_WAIT_TIMEOUT_SECONDS,
    MAX_RESPONSE_BYTES,
)
from .models import (
    AnalyzeOperation,
    ImageOperation,
    LipsyncOperation,
    ToolEnvelope,
    TtsOperation,
    VideoOperation,
)

INSTRUCTIONS = (
    "Everypixel Labs MCP exposes 22 media analysis, generation, voice, transcription, and chat "
    "endpoints through 8 domain tools. Status checks (/v1/status) are public; all other endpoints "
    "require EVERYPIXEL_CLIENT_ID + EVERYPIXEL_CLIENT_SECRET (HTTP Basic) or "
    "EVERYPIXEL_ACCESS_TOKEN. Async operations return a task_id immediately by default "
    "(wait=false); set wait=true to poll until completion within wait_timeout_seconds (max 180s), "
    "or poll later with everypixel_status. Local files require allow_local_files=true and "
    "EVERYPIXEL_MEDIA_ROOTS confinement. Lipsync operations require Data URIs (handled "
    "automatically when passing local paths with allow_local_files=true). Deleting a saved TTS "
    "voice requires confirmed=true. Read everypixel://catalog/endpoints or "
    "everypixel://catalog/models for full model and parameter reference."
)

READONLY_ANNOTATIONS = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=False,
    openWorldHint=True,
)
MUTATING_ANNOTATIONS = ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=False,
    idempotentHint=False,
    openWorldHint=True,
)
DESTRUCTIVE_CAPABLE_ANNOTATIONS = ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=True,
    idempotentHint=False,
    openWorldHint=True,
)


def _pkg_version() -> str:
    try:
        return version("everypixel-mcp")
    except PackageNotFoundError:
        return "0.1.0"


def create_server(
    *,
    client: EverypixelClient | None = None,
    client_factory: Callable[[], EverypixelClient] | None = None,
    max_response_bytes: int = MAX_RESPONSE_BYTES,
) -> MCPServer:
    mcp = MCPServer(
        "everypixel-mcp",
        version=_pkg_version(),
        instructions=INSTRUCTIONS,
    )

    def get_client() -> EverypixelClient:
        if client is not None:
            return client
        if client_factory is not None:
            return client_factory()
        return EverypixelClient()

    async def invoke(coro_fn: Callable[..., Any], **kwargs: Any) -> ToolEnvelope:
        try:
            try:
                payload: ToolEnvelope = {
                    "ok": True,
                    "result": await coro_fn(**kwargs),
                }
            except EverypixelMcpError as exc:
                payload = {"ok": False, "error": exc.as_dict()}
            encoded = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
            if len(encoded) > max_response_bytes:
                raise error(
                    "response_too_large",
                    "Response exceeded the configured MCP size limit.",
                    next_steps=["Request fewer items or narrow response size."],
                )
        except EverypixelMcpError as exc:
            payload = {"ok": False, "error": exc.as_dict()}
        except Exception:
            payload = {
                "ok": False,
                "error": {
                    "code": "internal_error",
                    "message": "The operation failed internally.",
                    "details": {},
                    "retryable": False,
                    "next_steps": [],
                },
            }
        return payload

    @mcp.tool(annotations=READONLY_ANNOTATIONS)
    async def everypixel_status(
        task_id: Annotated[
            str,
            Field(
                description=(
                    "Async job task_id returned by image, video, lipsync, tts, or transcribe."
                )
            ),
        ],
        wait: Annotated[
            bool,
            Field(
                description=(
                    "Poll until terminal state (SUCCESS/FAILURE/REVOKED) or wait_timeout_seconds."
                )
            ),
        ] = False,
        wait_timeout_seconds: Annotated[
            float,
            Field(description="Maximum seconds to poll when wait=true (1 to 180)."),
        ] = DEFAULT_WAIT_TIMEOUT_SECONDS,
        poll_interval_seconds: Annotated[
            float,
            Field(description="Seconds between status checks when wait=true (0.5 to 30)."),
        ] = DEFAULT_POLL_INTERVAL_SECONDS,
    ) -> ToolEnvelope:
        """Check or poll the status of an async Everypixel task (public, no auth needed)."""
        return await invoke(
            get_client().status,
            task_id=task_id,
            wait=wait,
            wait_timeout_seconds=wait_timeout_seconds,
            poll_interval_seconds=poll_interval_seconds,
        )

    @mcp.tool(annotations=READONLY_ANNOTATIONS)
    async def everypixel_analyze(
        operation: Annotated[
            AnalyzeOperation,
            Field(
                description=(
                    "Synchronous analysis operation: keywords, video_keywords, caption, "
                    "faces, quality, or quality_ugc."
                )
            ),
        ],
        url: Annotated[
            str | None,
            Field(description="Public HTTP(S) URL of the image or video to analyze."),
        ] = None,
        file_path: Annotated[
            str | None,
            Field(
                description=(
                    "Local file path inside EVERYPIXEL_MEDIA_ROOTS "
                    "(requires allow_local_files=true)."
                )
            ),
        ] = None,
        num_keywords: Annotated[
            int | None,
            Field(description="Number of keywords (1-50) for keywords or video_keywords."),
        ] = None,
        threshold: Annotated[
            float | None,
            Field(description="Minimum keyword score (0.0-1.0) for keywords or video_keywords."),
        ] = None,
        lang: Annotated[
            str | None,
            Field(
                description=(
                    "Language for image keywords: en, es, de, fr, it, pt, zh, hi, "
                    "ar, bn, ja, ko, ru."
                )
            ),
        ] = None,
        colors: Annotated[
            bool | None,
            Field(description="Include dominant color palette for operation='keywords'."),
        ] = None,
        num_colors: Annotated[
            int | None,
            Field(description="Number of dominant colors to return for operation='keywords'."),
        ] = None,
        caption_len: Annotated[
            str | None,
            Field(description="Caption length for operation='caption': short, medium, or long."),
        ] = None,
        allow_local_files: Annotated[
            bool,
            Field(description="Set true to permit reading file_path from EVERYPIXEL_MEDIA_ROOTS."),
        ] = False,
    ) -> ToolEnvelope:
        """Analyze images or videos synchronously for keywords, captions, faces, or quality."""
        return await invoke(
            get_client().analyze,
            operation=operation,
            url=url,
            file_path=file_path,
            num_keywords=num_keywords,
            threshold=threshold,
            lang=lang,
            colors=colors,
            num_colors=num_colors,
            caption_len=caption_len,
            allow_local_files=allow_local_files,
        )

    @mcp.tool(annotations=MUTATING_ANNOTATIONS)
    async def everypixel_image(
        operation: Annotated[
            ImageOperation,
            Field(
                description=(
                    "Image operation: generate, edit, remove_background, "
                    "vectorize, upscale, or face_swap."
                )
            ),
        ],
        prompt: Annotated[
            str | None,
            Field(description="Text prompt for generate or edit."),
        ] = None,
        model: Annotated[
            str | None,
            Field(description="Model identifier (see everypixel://catalog/models)."),
        ] = None,
        image_url: Annotated[
            str | None,
            Field(
                description=(
                    "Input image URL or Data URI for generate (style transfer), "
                    "remove_background, vectorize, or upscale."
                )
            ),
        ] = None,
        image_path: Annotated[
            str | None,
            Field(description="Local input image path under EVERYPIXEL_MEDIA_ROOTS."),
        ] = None,
        image_urls: Annotated[
            list[str] | None,
            Field(description="1-16 source image URLs or Data URIs for operation='edit'."),
        ] = None,
        image_paths: Annotated[
            list[str] | None,
            Field(description="1-16 local source image paths for operation='edit'."),
        ] = None,
        image_from_task_id: Annotated[
            str | None,
            Field(description="Prior image task_id to upscale (alternative to image_url)."),
        ] = None,
        source_url: Annotated[
            str | None,
            Field(description="Donor face image URL for operation='face_swap'."),
        ] = None,
        target_url: Annotated[
            str | None,
            Field(description="Target image URL for operation='face_swap'."),
        ] = None,
        source_path: Annotated[
            str | None,
            Field(description="Local donor face image path for operation='face_swap'."),
        ] = None,
        target_path: Annotated[
            str | None,
            Field(description="Local target image path for operation='face_swap'."),
        ] = None,
        quality: Annotated[
            str | None,
            Field(description="Quality setting for gpt-image-* models (low, medium, high)."),
        ] = None,
        image_size: Annotated[
            str | None,
            Field(
                description="Aspect ratio/size (e.g. square_1_1, landscape_16_9, portrait_9_16)."
            ),
        ] = None,
        resolution: Annotated[
            str | None,
            Field(description="Output resolution (0.5K, 1K, 2K, 4K)."),
        ] = None,
        style: Annotated[
            str | None,
            Field(description="Style preset for zimage (e.g. photo, anime, transfer)."),
        ] = None,
        megapixel_ratio: Annotated[
            float | None,
            Field(description="Megapixel ratio (0.5-1.5) for flux2 image edit."),
        ] = None,
        seed: Annotated[
            int | None,
            Field(description="Optional seed for reproducibility."),
        ] = None,
        controls: Annotated[
            dict[str, Any] | None,
            Field(description="Color controls for recraftv4_1_vector / recraftv4_1_pro_vector."),
        ] = None,
        lora_url: Annotated[
            str | None,
            Field(description="Custom LoRA weight URL for flux2l image generation."),
        ] = None,
        use_gfpgan: Annotated[
            bool | None,
            Field(description="Enable GFPGAN face enhancement on face_swap."),
        ] = None,
        title: Annotated[
            str | None,
            Field(description="Optional job title for face_swap."),
        ] = None,
        callback_url: Annotated[
            str | None,
            Field(description="Optional webhook URL for async completion notification."),
        ] = None,
        allow_local_files: Annotated[
            bool,
            Field(
                description=(
                    "Set true to permit reading local image paths under EVERYPIXEL_MEDIA_ROOTS."
                )
            ),
        ] = False,
        wait: Annotated[
            bool,
            Field(description="Poll /v1/status until completion or wait_timeout_seconds."),
        ] = False,
        wait_timeout_seconds: Annotated[
            float,
            Field(description="Maximum seconds to poll when wait=true (1 to 180)."),
        ] = DEFAULT_WAIT_TIMEOUT_SECONDS,
        poll_interval_seconds: Annotated[
            float,
            Field(description="Seconds between status polls when wait=true (0.5 to 30)."),
        ] = DEFAULT_POLL_INTERVAL_SECONDS,
    ) -> ToolEnvelope:
        """Generate, edit, remove background, vectorize, upscale, or swap faces in images."""
        return await invoke(
            get_client().image,
            operation=operation,
            prompt=prompt,
            model=model,
            image_url=image_url,
            image_path=image_path,
            image_urls=image_urls,
            image_paths=image_paths,
            image_from_task_id=image_from_task_id,
            source_url=source_url,
            target_url=target_url,
            source_path=source_path,
            target_path=target_path,
            quality=quality,
            image_size=image_size,
            resolution=resolution,
            style=style,
            megapixel_ratio=megapixel_ratio,
            seed=seed,
            controls=controls,
            lora_url=lora_url,
            use_gfpgan=use_gfpgan,
            title=title,
            callback_url=callback_url,
            allow_local_files=allow_local_files,
            wait=wait,
            wait_timeout_seconds=wait_timeout_seconds,
            poll_interval_seconds=poll_interval_seconds,
        )

    @mcp.tool(annotations=MUTATING_ANNOTATIONS)
    async def everypixel_video(
        operation: Annotated[
            VideoOperation,
            Field(
                description=(
                    "Video operation: generate, edit, upscale, matting, soundtrack, or face_swap."
                )
            ),
        ],
        model: Annotated[
            str | None,
            Field(
                description=(
                    "Video model identifier (required for generate and edit; "
                    "default seedvr2 for upscale)."
                )
            ),
        ] = None,
        prompt: Annotated[
            str | None,
            Field(
                description="Text prompt for video generate, edit, matting subject, or soundtrack."
            ),
        ] = None,
        video_url: Annotated[
            str | None,
            Field(
                description="Input video URL or Data URI for edit, upscale, matting, or soundtrack."
            ),
        ] = None,
        video_path: Annotated[
            str | None,
            Field(description="Local input video path under EVERYPIXEL_MEDIA_ROOTS."),
        ] = None,
        video_from_task_id: Annotated[
            str | None,
            Field(description="Prior video task_id for video edit."),
        ] = None,
        image_url: Annotated[
            str | None,
            Field(description="First-frame image URL or Data URI for video generate."),
        ] = None,
        image_path: Annotated[
            str | None,
            Field(description="Local first-frame image path for video generate."),
        ] = None,
        image_last_url: Annotated[
            str | None,
            Field(description="Last-frame image URL for video generate."),
        ] = None,
        reference_image_urls: Annotated[
            list[str] | None,
            Field(description="Reference image URLs for video generate or edit."),
        ] = None,
        reference_video_urls: Annotated[
            list[str] | None,
            Field(description="Reference video URLs for video generate."),
        ] = None,
        reference_audio_urls: Annotated[
            list[str] | None,
            Field(description="Reference audio URLs for video generate."),
        ] = None,
        content: Annotated[
            list[dict[str, Any]] | None,
            Field(description="Structured multimodal content array for aleph2 video edit."),
        ] = None,
        keyframes: Annotated[
            list[dict[str, Any]] | None,
            Field(description="Keyframe specifications for ltx23 video edit."),
        ] = None,
        duration: Annotated[
            int | None,
            Field(description="Output duration in seconds."),
        ] = None,
        resolution: Annotated[
            str | None,
            Field(description="Output resolution (e.g. 480p, 720p, 1080p, 1440p, 4k)."),
        ] = None,
        aspect_ratio: Annotated[
            str | None,
            Field(description="Aspect ratio (e.g. 16:9, 9:16, 1:1)."),
        ] = None,
        target_aspect_ratio: Annotated[
            str | None,
            Field(description="Target aspect ratio for ltx23 retargeting."),
        ] = None,
        public_figure_threshold: Annotated[
            str | None,
            Field(description="Moderation threshold for aleph2 (auto or low)."),
        ] = None,
        generate_audio: Annotated[
            bool | None,
            Field(description="Generate synchronized audio in video generate/edit."),
        ] = None,
        seed: Annotated[
            int | None,
            Field(description="Optional seed for reproducibility."),
        ] = None,
        source_url: Annotated[
            str | None,
            Field(description="Donor face image URL for operation='face_swap'."),
        ] = None,
        target_url: Annotated[
            str | None,
            Field(description="Target video URL for operation='face_swap'."),
        ] = None,
        source_path: Annotated[
            str | None,
            Field(description="Local donor face image path for operation='face_swap'."),
        ] = None,
        target_path: Annotated[
            str | None,
            Field(description="Local target video path for operation='face_swap'."),
        ] = None,
        use_gfpgan: Annotated[
            bool | None,
            Field(description="Enable GFPGAN face enhancement on face_swap."),
        ] = None,
        title: Annotated[
            str | None,
            Field(description="Optional job title for face_swap."),
        ] = None,
        callback_url: Annotated[
            str | None,
            Field(description="Optional webhook URL for async completion notification."),
        ] = None,
        allow_local_files: Annotated[
            bool,
            Field(
                description="Set true to permit reading local files under EVERYPIXEL_MEDIA_ROOTS."
            ),
        ] = False,
        wait: Annotated[
            bool,
            Field(description="Poll /v1/status until completion or wait_timeout_seconds."),
        ] = False,
        wait_timeout_seconds: Annotated[
            float,
            Field(description="Maximum seconds to poll when wait=true (1 to 180)."),
        ] = DEFAULT_WAIT_TIMEOUT_SECONDS,
        poll_interval_seconds: Annotated[
            float,
            Field(description="Seconds between status polls when wait=true (0.5 to 30)."),
        ] = DEFAULT_POLL_INTERVAL_SECONDS,
    ) -> ToolEnvelope:
        """Generate, edit, upscale, extract mattes, add soundtracks, or swap faces in videos."""
        return await invoke(
            get_client().video,
            operation=operation,
            model=model,
            prompt=prompt,
            video_url=video_url,
            video_path=video_path,
            video_from_task_id=video_from_task_id,
            image_url=image_url,
            image_path=image_path,
            image_last_url=image_last_url,
            reference_image_urls=reference_image_urls,
            reference_video_urls=reference_video_urls,
            reference_audio_urls=reference_audio_urls,
            content=content,
            keyframes=keyframes,
            duration=duration,
            resolution=resolution,
            aspect_ratio=aspect_ratio,
            target_aspect_ratio=target_aspect_ratio,
            public_figure_threshold=public_figure_threshold,
            generate_audio=generate_audio,
            seed=seed,
            source_url=source_url,
            target_url=target_url,
            source_path=source_path,
            target_path=target_path,
            use_gfpgan=use_gfpgan,
            title=title,
            callback_url=callback_url,
            allow_local_files=allow_local_files,
            wait=wait,
            wait_timeout_seconds=wait_timeout_seconds,
            poll_interval_seconds=poll_interval_seconds,
        )

    @mcp.tool(annotations=MUTATING_ANNOTATIONS)
    async def everypixel_lipsync(
        operation: Annotated[
            LipsyncOperation,
            Field(description="Lipsync operation: image_lipsync or video_lipsync."),
        ],
        audio_url: Annotated[
            str | None,
            Field(
                description=(
                    "Audio Data URI (data:audio/...;base64,...). "
                    "Plain HTTP URLs are rejected by upstream."
                )
            ),
        ] = None,
        audio_path: Annotated[
            str | None,
            Field(
                description=(
                    "Local audio file path under EVERYPIXEL_MEDIA_ROOTS (converted to Data URI)."
                )
            ),
        ] = None,
        image_url: Annotated[
            str | None,
            Field(description="Image Data URI for operation='image_lipsync'."),
        ] = None,
        image_path: Annotated[
            str | None,
            Field(
                description=(
                    "Local image file path under EVERYPIXEL_MEDIA_ROOTS "
                    "for operation='image_lipsync'."
                )
            ),
        ] = None,
        video_url: Annotated[
            str | None,
            Field(description="Video Data URI for operation='video_lipsync'."),
        ] = None,
        video_path: Annotated[
            str | None,
            Field(
                description=(
                    "Local video file path under EVERYPIXEL_MEDIA_ROOTS "
                    "for operation='video_lipsync'."
                )
            ),
        ] = None,
        model: Annotated[
            str | None,
            Field(
                description=(
                    "Model for image_lipsync (omnihuman15 or kling). Omit for video_lipsync."
                )
            ),
        ] = None,
        resolution: Annotated[
            str | None,
            Field(description="Output resolution: 720p or 1080p."),
        ] = None,
        callback_url: Annotated[
            str | None,
            Field(description="Optional webhook URL for async completion notification."),
        ] = None,
        allow_local_files: Annotated[
            bool,
            Field(
                description="Set true to permit reading local files under EVERYPIXEL_MEDIA_ROOTS."
            ),
        ] = False,
        wait: Annotated[
            bool,
            Field(description="Poll /v1/status until completion or wait_timeout_seconds."),
        ] = False,
        wait_timeout_seconds: Annotated[
            float,
            Field(description="Maximum seconds to poll when wait=true (1 to 180)."),
        ] = DEFAULT_WAIT_TIMEOUT_SECONDS,
        poll_interval_seconds: Annotated[
            float,
            Field(description="Seconds between status polls when wait=true (0.5 to 30)."),
        ] = DEFAULT_POLL_INTERVAL_SECONDS,
    ) -> ToolEnvelope:
        """Generate talking-head lip-sync videos from an image or video and an audio track."""
        return await invoke(
            get_client().lipsync,
            operation=operation,
            audio_url=audio_url,
            audio_path=audio_path,
            image_url=image_url,
            image_path=image_path,
            video_url=video_url,
            video_path=video_path,
            model=model,
            resolution=resolution,
            callback_url=callback_url,
            allow_local_files=allow_local_files,
            wait=wait,
            wait_timeout_seconds=wait_timeout_seconds,
            poll_interval_seconds=poll_interval_seconds,
        )

    @mcp.tool(annotations=DESTRUCTIVE_CAPABLE_ANNOTATIONS)
    async def everypixel_tts(
        operation: Annotated[
            TtsOperation,
            Field(
                description=(
                    "TTS operation: create, clone, design, save_voice, "
                    "list_voices, or delete_voice."
                )
            ),
        ],
        model: Annotated[
            str | None,
            Field(
                description="TTS model (qwen3, eleven_v3, eleven_multilingual_v2, eleven_ttv_v3)."
            ),
        ] = None,
        text: Annotated[
            str | None,
            Field(description="Text to synthesize for create, clone, or design."),
        ] = None,
        prompt: Annotated[
            str | None,
            Field(
                description=(
                    "Voice description or delivery instruction for create (qwen3) or design."
                )
            ),
        ] = None,
        speaker: Annotated[
            str | None,
            Field(description="Preset speaker name for qwen3 tts create."),
        ] = None,
        voice_id: Annotated[
            str | None,
            Field(description="Saved voice ID for create, clone, or delete_voice."),
        ] = None,
        character: Annotated[
            str | None,
            Field(description="Preset character archetype for qwen3 tts create."),
        ] = None,
        style: Annotated[
            str | None,
            Field(description="Preset vocal style for qwen3 tts create."),
        ] = None,
        language: Annotated[
            str | None,
            Field(description="Synthesis language for qwen3 tts create."),
        ] = None,
        seed: Annotated[
            int | None,
            Field(description="Optional seed for qwen3 tts create."),
        ] = None,
        audio_url: Annotated[
            str | None,
            Field(description="Reference audio URL or Data URI for operation='clone'."),
        ] = None,
        audio_path: Annotated[
            str | None,
            Field(description="Local reference audio path for operation='clone'."),
        ] = None,
        audio_urls: Annotated[
            list[str] | None,
            Field(description="Reference audio URLs/Data URIs for operation='save_voice'."),
        ] = None,
        audio_paths: Annotated[
            list[str] | None,
            Field(description="Local reference audio paths for operation='save_voice'."),
        ] = None,
        name: Annotated[
            str | None,
            Field(description="Voice name for operation='save_voice'."),
        ] = None,
        provider: Annotated[
            str | None,
            Field(
                description="Voice provider ('labs' or 'elevenlabs') for save_voice or list_voices."
            ),
        ] = None,
        preview_id: Annotated[
            str | None,
            Field(description="Preview ID from tts design to promote in save_voice."),
        ] = None,
        description: Annotated[
            str | None,
            Field(description="Optional voice description for save_voice."),
        ] = None,
        offset: Annotated[
            int | None,
            Field(description="Pagination offset for list_voices."),
        ] = None,
        limit: Annotated[
            int | None,
            Field(description="Pagination limit (1-100) for list_voices."),
        ] = None,
        callback_url: Annotated[
            str | None,
            Field(description="Optional webhook URL for async TTS operations."),
        ] = None,
        confirmed: Annotated[
            bool,
            Field(description="Must be true when operation='delete_voice'."),
        ] = False,
        allow_local_files: Annotated[
            bool,
            Field(
                description=(
                    "Set true to permit reading local audio paths under EVERYPIXEL_MEDIA_ROOTS."
                )
            ),
        ] = False,
        wait: Annotated[
            bool,
            Field(description="Poll /v1/status until completion for create, clone, or design."),
        ] = False,
        wait_timeout_seconds: Annotated[
            float,
            Field(description="Maximum seconds to poll when wait=true (1 to 180)."),
        ] = DEFAULT_WAIT_TIMEOUT_SECONDS,
        poll_interval_seconds: Annotated[
            float,
            Field(description="Seconds between status polls when wait=true (0.5 to 30)."),
        ] = DEFAULT_POLL_INTERVAL_SECONDS,
    ) -> ToolEnvelope:
        """Synthesize speech, clone or design voices, and manage saved voices."""
        return await invoke(
            get_client().tts,
            operation=operation,
            model=model,
            text=text,
            prompt=prompt,
            speaker=speaker,
            voice_id=voice_id,
            character=character,
            style=style,
            language=language,
            seed=seed,
            audio_url=audio_url,
            audio_path=audio_path,
            audio_urls=audio_urls,
            audio_paths=audio_paths,
            name=name,
            provider=provider,
            preview_id=preview_id,
            description=description,
            offset=offset,
            limit=limit,
            callback_url=callback_url,
            confirmed=confirmed,
            allow_local_files=allow_local_files,
            wait=wait,
            wait_timeout_seconds=wait_timeout_seconds,
            poll_interval_seconds=poll_interval_seconds,
        )

    @mcp.tool(annotations=MUTATING_ANNOTATIONS)
    async def everypixel_transcribe(
        audio_url: Annotated[
            str | None,
            Field(description="Audio HTTP(S) URL or Data URI to transcribe."),
        ] = None,
        audio_path: Annotated[
            str | None,
            Field(description="Local audio file path under EVERYPIXEL_MEDIA_ROOTS."),
        ] = None,
        language: Annotated[
            str,
            Field(description="Language code (e.g. 'auto', 'en', 'es', 'de', 'fr', 'ja', 'zh')."),
        ] = "auto",
        hints: Annotated[
            str | None,
            Field(description="Optional vocabulary hints or domain terms."),
        ] = None,
        denoise: Annotated[
            bool,
            Field(description="Enable background noise reduction before transcription."),
        ] = True,
        callback_url: Annotated[
            str | None,
            Field(description="Optional webhook URL for async completion notification."),
        ] = None,
        allow_local_files: Annotated[
            bool,
            Field(
                description="Set true to permit reading audio_path under EVERYPIXEL_MEDIA_ROOTS."
            ),
        ] = False,
        wait: Annotated[
            bool,
            Field(description="Poll /v1/status until completion or wait_timeout_seconds."),
        ] = False,
        wait_timeout_seconds: Annotated[
            float,
            Field(description="Maximum seconds to poll when wait=true (1 to 180)."),
        ] = DEFAULT_WAIT_TIMEOUT_SECONDS,
        poll_interval_seconds: Annotated[
            float,
            Field(description="Seconds between status polls when wait=true (0.5 to 30)."),
        ] = DEFAULT_POLL_INTERVAL_SECONDS,
    ) -> ToolEnvelope:
        """Transcribe speech from audio files into text and word-level timestamps."""
        return await invoke(
            get_client().transcribe,
            audio_url=audio_url,
            audio_path=audio_path,
            language=language,
            hints=hints,
            denoise=denoise,
            callback_url=callback_url,
            allow_local_files=allow_local_files,
            wait=wait,
            wait_timeout_seconds=wait_timeout_seconds,
            poll_interval_seconds=poll_interval_seconds,
        )

    @mcp.tool(annotations=READONLY_ANNOTATIONS)
    async def everypixel_chat(
        messages: Annotated[
            list[dict[str, Any]],
            Field(description="OpenAI-compatible chat messages array ({role, content})."),
        ],
        model: Annotated[
            str,
            Field(description="Chat model identifier (currently 'glm-5.3')."),
        ] = "glm-5.3",
        max_tokens: Annotated[
            int | None,
            Field(description="Maximum tokens to generate (1-131072)."),
        ] = None,
        max_completion_tokens: Annotated[
            int | None,
            Field(
                description=(
                    "Maximum completion tokens (1-131072, mutually exclusive with max_tokens)."
                )
            ),
        ] = None,
        temperature: Annotated[
            float | None,
            Field(description="Sampling temperature (0.0-2.0)."),
        ] = None,
        top_p: Annotated[
            float | None,
            Field(description="Nucleus sampling top_p (0.0 < top_p <= 1.0)."),
        ] = None,
        do_sample: Annotated[
            bool | None,
            Field(description="Enable sampling (true) or greedy decoding (false)."),
        ] = None,
        reasoning_effort: Annotated[
            str | None,
            Field(description="Reasoning effort: none, minimal, low, medium, high, or xhigh."),
        ] = None,
        thinking: Annotated[
            dict[str, Any] | None,
            Field(description="Thinking config object: {'type': 'enabled'|'disabled'}."),
        ] = None,
        tools: Annotated[
            list[dict[str, Any]] | None,
            Field(description="Optional function-calling tool definitions."),
        ] = None,
        tool_choice: Annotated[
            str | None,
            Field(description="Tool selection policy ('none' or 'auto')."),
        ] = None,
        stop: Annotated[
            str | list[str] | None,
            Field(description="Single stop sequence or list of stop sequences."),
        ] = None,
        response_format: Annotated[
            dict[str, Any] | None,
            Field(description="Output format: {'type': 'text'} or {'type': 'json_object'}."),
        ] = None,
        user: Annotated[
            str | None,
            Field(description="Optional end-user identifier."),
        ] = None,
    ) -> ToolEnvelope:
        """Run non-streaming chat completion with GLM-5.3 (/v1/chat/completions)."""
        return await invoke(
            get_client().chat,
            messages=messages,
            model=model,
            max_tokens=max_tokens,
            max_completion_tokens=max_completion_tokens,
            temperature=temperature,
            top_p=top_p,
            do_sample=do_sample,
            reasoning_effort=reasoning_effort,
            thinking=thinking,
            tools=tools,
            tool_choice=tool_choice,
            stop=stop,
            response_format=response_format,
            user=user,
        )

    @mcp.resource("everypixel://catalog/endpoints", mime_type="application/json")
    def endpoints_catalog() -> str:
        """Complete Everypixel Labs v1 endpoint catalog mapped by MCP tool; no API call."""
        return json.dumps(CATALOG["endpoints"])

    @mcp.resource("everypixel://catalog/models", mime_type="application/json")
    def models_catalog() -> str:
        """Supported Everypixel model identifiers, languages, and presets; no API call."""
        return json.dumps(CATALOG["models"])

    return mcp


def run_stdio(
    *,
    client: EverypixelClient | None = None,
    client_factory: Callable[[], EverypixelClient] | None = None,
) -> None:
    from pathlib import Path

    from .dotenv_util import load_credential_env

    source_root = Path(__file__).resolve().parents[1]
    project_root = source_root.parent if source_root.name == "src" else Path.cwd()
    load_credential_env(project_root=project_root)
    server = create_server(client=client, client_factory=client_factory)
    server.run(transport="stdio")
