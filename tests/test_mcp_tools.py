from __future__ import annotations

import json
from typing import Any

import pytest
from mcp import Client

from everypixel_mcp.client import EverypixelClient
from everypixel_mcp.errors import error
from everypixel_mcp.mcp_server import create_server


class FakeHttpResponse:
    def __init__(
        self,
        status_code: int = 200,
        body: dict[str, Any] | str | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        if body is None:
            self.content = b"{}"
        elif isinstance(body, str):
            self.content = body.encode("utf-8")
        else:
            self.content = json.dumps(body).encode("utf-8")
        self.headers = headers or {"X-Request-ID": "req-test-123"}


class FakeAsyncHttp:
    def __init__(self, handler: Any) -> None:
        self.handler = handler
        self.calls: list[dict[str, Any]] = []

    async def request(self, method: str, url: str, **kwargs: Any) -> FakeHttpResponse:
        record = {"method": method, "url": url, **kwargs}
        self.calls.append(record)
        return await self.handler(record)

    async def aclose(self) -> None:
        return None


def _unwrap(payload: Any) -> dict[str, Any]:
    value = getattr(payload, "structured_content", None)
    if isinstance(value, dict) and set(value) == {"result"}:
        value = value["result"]
    if isinstance(value, str):
        value = json.loads(value)
    if isinstance(value, dict):
        return value
    if isinstance(payload, dict):
        return payload
    content = getattr(payload, "content", None)
    if content:
        for item in content:
            text = getattr(item, "text", None)
            if text:
                parsed = json.loads(text)
                if isinstance(parsed, dict) and set(parsed) == {"result"}:
                    parsed = parsed["result"]
                assert isinstance(parsed, dict)
                return parsed
    raise AssertionError(f"unexpected tool payload: {payload!r}")


@pytest.mark.asyncio
async def test_mcp_lists_8_tools_and_2_resources():
    client = EverypixelClient(client_id="cid", client_secret="csec")
    server = create_server(client=client)
    async with Client(server) as mcp_client:
        tools = await mcp_client.list_tools()
        resources = await mcp_client.list_resources()
        tool_names = {tool.name for tool in tools.tools}
        resource_uris = {str(res.uri) for res in resources.resources}
        assert tool_names == {
            "everypixel_status",
            "everypixel_analyze",
            "everypixel_image",
            "everypixel_video",
            "everypixel_lipsync",
            "everypixel_tts",
            "everypixel_transcribe",
            "everypixel_chat",
        }
        assert resource_uris == {
            "everypixel://catalog/endpoints",
            "everypixel://catalog/models",
        }


@pytest.mark.asyncio
async def test_catalog_resources_return_json():
    client = EverypixelClient(client_id="cid", client_secret="csec")
    server = create_server(client=client)
    async with Client(server) as mcp_client:
        ep_res = await mcp_client.read_resource("everypixel://catalog/endpoints")
        models_res = await mcp_client.read_resource("everypixel://catalog/models")
        ep_data = json.loads(ep_res.contents[0].text)
        models_data = json.loads(models_res.contents[0].text)
        assert "everypixel_image" in ep_data["tools"]
        assert "zimage" in models_data["image_generate"]
        assert "glm-5.3" in models_data["chat"]


@pytest.mark.asyncio
async def test_status_is_public_and_does_not_require_credentials(monkeypatch):
    monkeypatch.delenv("EVERYPIXEL_CLIENT_ID", raising=False)
    monkeypatch.delenv("EVERYPIXEL_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("EVERYPIXEL_ACCESS_TOKEN", raising=False)

    seen_calls: list[dict[str, Any]] = []

    async def handler(req: dict[str, Any]) -> FakeHttpResponse:
        seen_calls.append(req)
        return FakeHttpResponse(
            200,
            {
                "status": "SUCCESS",
                "task_id": "t-123",
                "result": {"url": "https://cdn.example/out.png"},
            },
        )

    http = FakeAsyncHttp(handler)
    client = EverypixelClient(async_http_factory=lambda **kw: http)
    async with Client(create_server(client=client)) as mcp_client:
        raw = await mcp_client.call_tool("everypixel_status", {"task_id": "t-123"})
        payload = _unwrap(raw)
        assert payload["ok"] is True
        assert payload["result"]["status"] == "SUCCESS"
        assert payload["result"]["request_id"] == "req-test-123"
        assert "auth" not in seen_calls[0]
        assert "Authorization" not in seen_calls[0].get("headers", {})


@pytest.mark.asyncio
async def test_status_polling_until_success():
    responses = [
        {"status": "PENDING", "task_id": "t-poll"},
        {"status": "RUNNING", "task_id": "t-poll"},
        {"status": "SUCCESS", "task_id": "t-poll", "output": "https://cdn.example/video.mp4"},
    ]

    async def handler(req: dict[str, Any]) -> FakeHttpResponse:
        return FakeHttpResponse(200, responses.pop(0))

    http = FakeAsyncHttp(handler)
    client = EverypixelClient(async_http_factory=lambda **kw: http)
    async with Client(create_server(client=client)) as mcp_client:
        raw = await mcp_client.call_tool(
            "everypixel_status",
            {
                "task_id": "t-poll",
                "wait": True,
                "wait_timeout_seconds": 5.0,
                "poll_interval_seconds": 0.5,
            },
        )
        payload = _unwrap(raw)
        assert payload["ok"] is True
        assert payload["result"]["status"] == "SUCCESS"
        assert len(http.calls) == 3


@pytest.mark.asyncio
async def test_status_polling_failure_returns_task_failed():
    async def handler(req: dict[str, Any]) -> FakeHttpResponse:
        return FakeHttpResponse(
            200, {"status": "FAILURE", "task_id": "t-fail", "error": "NSFW content blocked"}
        )

    http = FakeAsyncHttp(handler)
    client = EverypixelClient(async_http_factory=lambda **kw: http)
    async with Client(create_server(client=client)) as mcp_client:
        raw = await mcp_client.call_tool(
            "everypixel_status",
            {
                "task_id": "t-fail",
                "wait": True,
                "wait_timeout_seconds": 5.0,
                "poll_interval_seconds": 0.5,
            },
        )
        payload = _unwrap(raw)
        assert payload["ok"] is False
        assert payload["error"]["code"] == "task_failed"
        assert payload["error"]["details"]["task_id"] == "t-fail"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "tool, arguments",
    [
        ("everypixel_analyze", {"operation": "keywords", "url": "https://example.com/a.jpg"}),
        ("everypixel_image", {"operation": "generate", "prompt": "a cat"}),
        ("everypixel_video", {"operation": "generate", "model": "wan2.7", "prompt": "a dog"}),
        (
            "everypixel_lipsync",
            {
                "operation": "image_lipsync",
                "audio_url": "data:audio/mp3;base64,QUJD",
                "image_url": "data:image/png;base64,QUJD",
            },
        ),
        ("everypixel_tts", {"operation": "list_voices"}),
        ("everypixel_transcribe", {"audio_url": "https://example.com/a.mp3"}),
        ("everypixel_chat", {"messages": [{"role": "user", "content": "hi"}]}),
    ],
)
async def test_missing_credential_is_structured_at_tool_boundary(monkeypatch, tool, arguments):
    monkeypatch.delenv("EVERYPIXEL_CLIENT_ID", raising=False)
    monkeypatch.delenv("EVERYPIXEL_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("EVERYPIXEL_ACCESS_TOKEN", raising=False)
    async with Client(create_server()) as mcp_client:
        payload = _unwrap(await mcp_client.call_tool(tool, arguments))
    assert payload["ok"] is False
    assert payload["error"]["code"] == "missing_credential"


@pytest.mark.asyncio
async def test_internal_errors_are_redacted(monkeypatch):
    client = EverypixelClient(client_id="cid", client_secret="csec")

    async def boom(**kwargs: Any) -> Any:
        raise RuntimeError("SECRET-INTERNAL-CRASH")

    monkeypatch.setattr(client, "analyze", boom)
    async with Client(create_server(client=client)) as mcp_client:
        payload = _unwrap(
            await mcp_client.call_tool(
                "everypixel_analyze",
                {"operation": "keywords", "url": "https://example.com/img.jpg"},
            )
        )
    assert payload["ok"] is False
    assert payload["error"]["code"] == "internal_error"
    assert "SECRET" not in str(payload)


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", [False, True])
async def test_response_limit_covers_success_and_error(monkeypatch, failure):
    client = EverypixelClient(client_id="cid", client_secret="csec")

    async def large_result(**kwargs: Any) -> Any:
        if failure:
            raise error("invalid_input", "x" * 2048)
        return {"text": "x" * 2048}

    monkeypatch.setattr(client, "analyze", large_result)
    server = create_server(client=client, max_response_bytes=512)
    async with Client(server) as mcp_client:
        payload = _unwrap(
            await mcp_client.call_tool(
                "everypixel_analyze",
                {"operation": "keywords", "url": "https://example.com/img.jpg"},
            )
        )
    assert payload["ok"] is False
    assert payload["error"]["code"] == "response_too_large"
