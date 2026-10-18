from __future__ import annotations

import json
from typing import Any

import pytest

from everypixel_mcp.client import EverypixelClient, resolve_credentials
from everypixel_mcp.errors import EverypixelMcpError


class FakeResponse:
    def __init__(self, status_code: int = 200, payload: dict[str, Any] | None = None) -> None:
        self.status_code = status_code
        self.content = json.dumps(payload or {"status": "ok"}).encode("utf-8")
        self.headers = {"X-Request-ID": "req-1"}


class RecordingHttp:
    def __init__(self, status_code: int = 200, payload: dict[str, Any] | None = None) -> None:
        self.status_code = status_code
        self.payload = payload or {"status": "ok", "task_id": "t-1"}
        self.last_request: dict[str, Any] | None = None

    async def request(self, method: str, url: str, **kwargs: Any) -> FakeResponse:
        self.last_request = {"method": method, "url": url, **kwargs}
        return FakeResponse(self.status_code, self.payload)

    async def aclose(self) -> None:
        return None


def _make_client(http: RecordingHttp | None = None) -> tuple[EverypixelClient, RecordingHttp]:
    rec = http or RecordingHttp()
    client = EverypixelClient(
        client_id="cid",
        client_secret="csec",
        async_http_factory=lambda **kw: rec,
    )
    return client, rec


def test_resolve_credentials_rejects_client_secret_as_access_token():
    with pytest.raises(EverypixelMcpError) as exc:
        resolve_credentials(
            {
                "EVERYPIXEL_CLIENT_ID": "id1",
                "EVERYPIXEL_CLIENT_SECRET": "same-secret",
                "EVERYPIXEL_ACCESS_TOKEN": "same-secret",
            }
        )
    assert exc.value.code == "invalid_input"


def test_resolve_credentials_requires_both_basic_fields():
    with pytest.raises(EverypixelMcpError) as exc:
        resolve_credentials({"EVERYPIXEL_CLIENT_ID": "only-id"})
    assert exc.value.code == "missing_credential"


@pytest.mark.asyncio
async def test_analyze_keywords_and_parameter_guards():
    client, rec = _make_client()
    res = await client.analyze(
        operation="keywords",
        url="https://example.com/photo.jpg",
        num_keywords=15,
        threshold=0.4,
        lang="en",
        colors=True,
        num_colors=5,
    )
    assert res["status"] == "ok"
    assert rec.last_request is not None
    assert rec.last_request["method"] == "GET"
    assert rec.last_request["url"].endswith("/v1/keywords")
    assert rec.last_request["params"]["num_keywords"] == 15

    # Reject colors on quality operation
    with pytest.raises(EverypixelMcpError) as exc:
        await client.analyze(
            operation="quality",
            url="https://example.com/photo.jpg",
            colors=True,
        )
    assert exc.value.code == "invalid_input"

    # Reject caption_len on faces operation
    with pytest.raises(EverypixelMcpError) as exc2:
        await client.analyze(
            operation="faces",
            url="https://example.com/photo.jpg",
            caption_len="short",
        )
    assert exc2.value.code == "invalid_input"


@pytest.mark.asyncio
async def test_image_operations_and_validation():
    client, rec = _make_client()

    # generate
    await client.image(
        operation="generate",
        prompt="a futuristic skyline",
        model="zimage",
        image_size="landscape_16_9",
    )
    assert rec.last_request is not None
    assert rec.last_request["url"].endswith("/v1/image_generate")
    assert rec.last_request["json"]["model"] == "zimage"

    # style='transfer' requires image_url or image_path
    with pytest.raises(EverypixelMcpError) as exc:
        await client.image(
            operation="generate",
            prompt="transfer style",
            model="zimage",
            style="transfer",
        )
    assert exc.value.code == "invalid_input"

    # remove_background rejects model
    with pytest.raises(EverypixelMcpError) as exc2:
        await client.image(
            operation="remove_background",
            image_url="https://example.com/a.png",
            model="zimage",
        )
    assert exc2.value.code == "invalid_input"

    # upscale with image_from_task_id
    await client.image(
        operation="upscale",
        image_from_task_id="task-prev-1",
        model="flux2",
    )
    assert rec.last_request["url"].endswith("/v1/image_upscale")
    assert rec.last_request["json"] == {"model": "flux2", "image_from_task_id": "task-prev-1"}

    # face_swap GET via URLs uses callback param
    await client.image(
        operation="face_swap",
        source_url="https://example.com/src.jpg",
        target_url="https://example.com/dst.jpg",
        use_gfpgan=True,
        callback_url="https://example.com/hook",
    )
    assert rec.last_request["method"] == "GET"
    assert rec.last_request["url"].endswith("/v1/imageswap/create")
    assert rec.last_request["params"]["callback"] == "https://example.com/hook"


@pytest.mark.asyncio
async def test_video_operations_and_model_constraints():
    client, rec = _make_client()

    # grok15 requires first frame image
    with pytest.raises(EverypixelMcpError) as exc:
        await client.video(
            operation="generate",
            model="grok15",
            prompt="a rocket launch",
        )
    assert exc.value.code == "invalid_input"

    # gemini-omni-1.1-flash edit requires video_from_task_id and rejects video_url
    with pytest.raises(EverypixelMcpError) as exc2:
        await client.video(
            operation="edit",
            model="gemini-omni-1.1-flash",
            prompt="make it winter",
            video_url="https://example.com/v.mp4",
        )
    assert exc2.value.code == "invalid_input"

    await client.video(
        operation="edit",
        model="gemini-omni-1.1-flash",
        prompt="make it winter",
        video_from_task_id="task-vid-1",
    )
    assert rec.last_request is not None
    assert rec.last_request["url"].endswith("/v1/video_edit")
    assert rec.last_request["json"]["video_from_task_id"] == "task-vid-1"

    # seedvr2 upscale rejects 4k
    with pytest.raises(EverypixelMcpError) as exc3:
        await client.video(
            operation="upscale",
            model="seedvr2",
            video_url="https://example.com/v.mp4",
            resolution="4k",
        )
    assert exc3.value.code == "invalid_input"


@pytest.mark.asyncio
async def test_lipsync_requires_data_uris_and_rejects_model_on_video_lipsync():
    client, rec = _make_client()

    # Plain HTTP URL rejected on lipsync
    with pytest.raises(EverypixelMcpError) as exc:
        await client.lipsync(
            operation="image_lipsync",
            audio_url="https://example.com/a.mp3",
            image_url="data:image/png;base64,QUJD",
        )
    assert exc.value.code == "invalid_input"

    # video_lipsync rejects model parameter
    with pytest.raises(EverypixelMcpError) as exc2:
        await client.lipsync(
            operation="video_lipsync",
            audio_url="data:audio/mp3;base64,QUJD",
            video_url="data:video/mp4;base64,QUJD",
            model="kling",
        )
    assert exc2.value.code == "invalid_input"

    await client.lipsync(
        operation="video_lipsync",
        audio_url="data:audio/mp3;base64,QUJD",
        video_url="data:video/mp4;base64,QUJD",
        resolution="720p",
    )
    assert rec.last_request is not None
    assert rec.last_request["url"].endswith("/v1/video_lipsync")


@pytest.mark.asyncio
async def test_tts_operations_and_delete_voice_confirmation():
    client, rec = _make_client()

    # ElevenLabs create requires voice_id and rejects speaker/style
    with pytest.raises(EverypixelMcpError) as exc:
        await client.tts(
            operation="create",
            model="eleven_v3",
            text="Hello world",
            speaker="Mia",
            voice_id="v-1",
        )
    assert exc.value.code == "invalid_input"

    # delete_voice requires confirmed=True
    with pytest.raises(EverypixelMcpError) as exc2:
        await client.tts(operation="delete_voice", voice_id="v-123", confirmed=False)
    assert exc2.value.code == "confirmation_required"

    await client.tts(operation="delete_voice", voice_id="v-123", confirmed=True)
    assert rec.last_request is not None
    assert rec.last_request["method"] == "DELETE"
    assert rec.last_request["params"] == {"voice_id": "v-123"}


@pytest.mark.asyncio
async def test_chat_validation():
    client, rec = _make_client(
        RecordingHttp(
            200,
            {
                "id": "chatcmpl-1",
                "choices": [{"message": {"role": "assistant", "content": "Hello!"}}],
            },
        )
    )
    res = await client.chat(
        messages=[{"role": "user", "content": "Hi"}],
        reasoning_effort="low",
    )
    assert res["id"] == "chatcmpl-1"
    assert rec.last_request is not None
    assert rec.last_request["json"]["stream"] is False

    # Mutually exclusive max_tokens and max_completion_tokens
    with pytest.raises(EverypixelMcpError) as exc:
        await client.chat(
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=100,
            max_completion_tokens=100,
        )
    assert exc.value.code == "invalid_input"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status_code, expected_code, expected_retryable",
    [
        (400, "invalid_request", False),
        (401, "authentication_failed", False),
        (429, "rate_or_quota_exceeded", True),
        (503, "upstream_unavailable", True),
    ],
)
async def test_http_error_mapping(status_code, expected_code, expected_retryable):
    client, _ = _make_client(RecordingHttp(status_code, {"message": "upstream err"}))
    with pytest.raises(EverypixelMcpError) as exc:
        await client.tts(operation="list_voices")
    assert exc.value.code == expected_code
    assert exc.value.retryable is expected_retryable
