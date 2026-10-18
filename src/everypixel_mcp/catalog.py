"""Static catalog of Everypixel Labs API endpoints, models, and constraints."""

from __future__ import annotations

from typing import Any

IMAGE_GENERATE_MODELS = (
    "zimage",
    "flux",
    "flux2",
    "flux3",
    "grok-imagine",
    "grok-imagine-2",
    "grok-imagine-2-low",
    "gemini-3.1-flash",
    "gemini-nano-banana-2.1",
    "gemini-3.1-flash-lite",
    "gemini-3-pro",
    "seedream-5-pro",
    "seedream-5-flash",
    "seedream-5",
    "gpt-image-2",
    "gpt-image-2.5-sunburst",
    "wan2.7",
    "wan2.7-pro",
    "recraftv4_1_vector",
    "recraftv4_1_pro_vector",
)

IMAGE_EDIT_MODELS = (
    "flux2",
    "flux3",
    "qwen",
    "grok",
    "grok-imagine",
    "grok-imagine-2",
    "grok-imagine-2-low",
    "gemini-3.1-flash",
    "gemini-nano-banana-2.1",
    "gemini-3.1-flash-lite",
    "gemini-3-pro",
    "seedream-5-pro",
    "seedream-5-flash",
    "seedream-5",
    "gpt-image-2",
    "gpt-image-2.5-sunburst",
    "wan2.7",
    "wan2.7-pro",
)

IMAGE_UPSCALE_MODELS = ("seedvr2", "flux2")

IMAGE_SIZES = (
    "square",
    "portrait_3_2",
    "portrait_4_3",
    "portrait_16_9",
    "landscape_3_2",
    "landscape_4_3",
    "landscape_16_9",
)

VIDEO_GENERATE_MODELS = (
    "minimax-h3-turbo",
    "minimax-h3",
    "ltx23",
    "flux3",
    "grok",
    "grok15",
    "grok-imagine",
    "grok-imagine-1.5",
    "gemini-omni-1.1-flash",
    "seedance2",
    "seedance2-mini",
    "seedance2.5",
    "kling-2.6",
    "kling-3",
    "kling-3-turbo",
    "kling-3-omni",
    "wan2.7",
    "wan3.0",
)

VIDEO_EDIT_MODELS = (
    "aleph2",
    "wan2.7",
    "flux3",
    "gemini-omni-1.1-flash",
    "seedance2",
    "seedance2-mini",
    "seedance2.5",
    "kling-3-omni",
)

VIDEO_UPSCALE_MODELS = (
    "seedvr2",
    "topaz-prob-4",
    "topaz-slp-2.5",
    "topaz-ast-2",
)

IMAGE_LIPSYNC_MODELS = ("inftalk", "ltx23")
LIPSYNC_RESOLUTIONS = ("360p", "480p", "720p")

TTS_CREATE_MODELS = (
    "qwen3",
    "eleven_v4",
    "eleven_v4_turbo",
    "eleven_v3",
    "eleven_v3_conversational",
    "eleven_multilingual_v2",
    "eleven_flash_v2_5",
)

TTS_DESIGN_MODELS = (
    "qwen3",
    "eleven_multilingual_ttv_v2",
    "eleven_ttv_v3",
)

KEYWORD_LANGUAGES = ("en", "ru", "es", "fr", "de", "pt", "it")
CAPTION_LENGTHS = ("short", "normal", "long")

TRANSCRIBE_LANGUAGES = (
    "auto",
    "English",
    "Russian",
    "Chinese",
    "Cantonese",
    "Arabic",
    "German",
    "French",
    "Spanish",
    "Portuguese",
    "Indonesian",
    "Italian",
    "Korean",
    "Thai",
    "Vietnamese",
    "Japanese",
    "Turkish",
    "Hindi",
    "Malay",
    "Dutch",
    "Swedish",
    "Danish",
    "Finnish",
    "Polish",
    "Czech",
    "Filipino",
    "Persian",
    "Greek",
    "Hungarian",
    "Macedonian",
    "Romanian",
)

CHAT_MODELS = ("glm-5.3",)

CATALOG: dict[str, dict[str, Any]] = {
    "endpoints": {
        "base_url": "https://api.everypixel.com/v1",
        "authentication": {
            "basic": "HTTP Basic with EVERYPIXEL_CLIENT_ID and EVERYPIXEL_CLIENT_SECRET",
            "bearer": (
                "Authorization: Bearer <EVERYPIXEL_ACCESS_TOKEN> (OAuth token, never Client Secret)"
            ),
            "public": "GET /v1/status requires no authentication",
        },
        "tools": {
            "everypixel_status": {
                "endpoint": "GET /v1/status",
                "mode": "sync_or_wait_loop",
                "auth_required": False,
                "description": "Check or poll an asynchronous task by task_id.",
            },
            "everypixel_analyze": {
                "operations": {
                    "keywords": {
                        "endpoint": "GET|POST /v1/keywords",
                        "mode": "sync",
                        "rps_limit": 30,
                    },
                    "video_keywords": {
                        "endpoint": "GET|POST /v1/video_keywords",
                        "mode": "sync",
                        "rps_limit": 1,
                    },
                    "caption": {
                        "endpoint": "GET|POST /v1/image_captioning",
                        "mode": "sync",
                        "rps_limit": 1,
                    },
                    "faces": {"endpoint": "GET|POST /v1/faces", "mode": "sync", "rps_limit": 10},
                    "quality": {
                        "endpoint": "GET|POST /v1/quality",
                        "mode": "sync",
                        "rps_limit": 30,
                    },
                    "quality_ugc": {
                        "endpoint": "GET|POST /v1/quality_ugc",
                        "mode": "sync",
                        "rps_limit": 30,
                    },
                },
            },
            "everypixel_image": {
                "operations": {
                    "generate": {"endpoint": "POST /v1/image_generate", "mode": "async"},
                    "edit": {"endpoint": "POST /v1/image_edit", "mode": "async"},
                    "remove_background": {
                        "endpoint": "POST /v1/image_remove_background",
                        "mode": "async",
                    },
                    "vectorize": {"endpoint": "POST /v1/image_vectorize", "mode": "async"},
                    "upscale": {"endpoint": "POST /v1/image_upscale", "mode": "async"},
                    "face_swap": {"endpoint": "GET|POST /v1/imageswap/create", "mode": "async"},
                },
            },
            "everypixel_video": {
                "operations": {
                    "generate": {"endpoint": "POST /v1/video_generate", "mode": "async"},
                    "edit": {"endpoint": "POST /v1/video_edit", "mode": "async", "trial": False},
                    "upscale": {"endpoint": "POST /v1/video_upscale", "mode": "async"},
                    "matting": {"endpoint": "POST /v1/video_matting", "mode": "async"},
                    "soundtrack": {"endpoint": "POST /v1/video_soundtrack", "mode": "async"},
                    "face_swap": {"endpoint": "GET|POST /v1/videoswap/create", "mode": "async"},
                },
            },
            "everypixel_lipsync": {
                "operations": {
                    "image_lipsync": {"endpoint": "POST /v1/image_lipsync", "mode": "async"},
                    "video_lipsync": {"endpoint": "POST /v1/video_lipsync", "mode": "async"},
                },
            },
            "everypixel_tts": {
                "operations": {
                    "create": {"endpoint": "POST /v1/tts_create", "mode": "async"},
                    "clone": {"endpoint": "POST /v1/tts_clone", "mode": "async"},
                    "design": {"endpoint": "POST /v1/tts_design", "mode": "async"},
                    "save_voice": {"endpoint": "POST /v1/tts_voice", "mode": "sync"},
                    "list_voices": {"endpoint": "GET /v1/tts_voices", "mode": "sync"},
                    "delete_voice": {
                        "endpoint": "DELETE /v1/tts_voice",
                        "mode": "sync",
                        "destructive": True,
                    },
                },
            },
            "everypixel_transcribe": {
                "endpoint": "POST /v1/transcribe",
                "mode": "async",
            },
            "everypixel_chat": {
                "endpoint": "POST /v1/chat/completions",
                "mode": "sync",
                "trial": False,
            },
        },
    },
    "models": {
        "image_generate": list(IMAGE_GENERATE_MODELS),
        "image_edit": list(IMAGE_EDIT_MODELS),
        "image_upscale": list(IMAGE_UPSCALE_MODELS),
        "image_sizes": list(IMAGE_SIZES),
        "video_generate": list(VIDEO_GENERATE_MODELS),
        "video_edit": list(VIDEO_EDIT_MODELS),
        "video_upscale": list(VIDEO_UPSCALE_MODELS),
        "image_lipsync": list(IMAGE_LIPSYNC_MODELS),
        "lipsync_resolutions": list(LIPSYNC_RESOLUTIONS),
        "tts_create": list(TTS_CREATE_MODELS),
        "tts_design": list(TTS_DESIGN_MODELS),
        "chat": list(CHAT_MODELS),
        "keyword_languages": list(KEYWORD_LANGUAGES),
        "caption_lengths": list(CAPTION_LENGTHS),
        "transcribe_languages": list(TRANSCRIBE_LANGUAGES),
    },
}
