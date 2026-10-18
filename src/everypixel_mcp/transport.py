"""Bound HTTP response reads using httpx2 client extension points."""

from __future__ import annotations

from typing import Any

import anyio
import httpx2

from .errors import error
from .limits import MAX_RESPONSE_BYTES


def _append(chunks: list[bytes], chunk: bytes, size: int, limit: int) -> int:
    size += len(chunk)
    if size > limit:
        raise error(
            "response_too_large",
            "Provider response exceeds the byte budget.",
            next_steps=["Narrow request parameters or reduce output size."],
        )
    chunks.append(chunk)
    return size


def _materialize(response: httpx2.Response, chunks: list[bytes]) -> httpx2.Response:
    headers = response.headers.copy()
    headers.pop("content-encoding", None)
    headers.pop("content-length", None)
    return httpx2.Response(
        response.status_code,
        headers=headers,
        content=b"".join(chunks),
        request=response.request,
        extensions=response.extensions,
    )


class BoundedClient(httpx2.Client):
    def __init__(self, *, max_response_bytes: int = MAX_RESPONSE_BYTES, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.max_response_bytes = max_response_bytes

    def send(self, request: httpx2.Request, **kwargs: Any) -> httpx2.Response:
        kwargs["stream"] = True
        response = super().send(request, **kwargs)
        chunks: list[bytes] = []
        size = 0
        try:
            for chunk in response.iter_bytes():
                size = _append(chunks, chunk, size, self.max_response_bytes)
            return _materialize(response, chunks)
        finally:
            response.close()


class BoundedAsyncClient(httpx2.AsyncClient):
    def __init__(self, *, max_response_bytes: int = MAX_RESPONSE_BYTES, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.max_response_bytes = max_response_bytes

    async def send(self, request: httpx2.Request, **kwargs: Any) -> httpx2.Response:
        kwargs["stream"] = True
        response = await super().send(request, **kwargs)
        chunks: list[bytes] = []
        size = 0
        try:
            async for chunk in response.aiter_bytes():
                size = _append(chunks, chunk, size, self.max_response_bytes)
            return _materialize(response, chunks)
        finally:
            with anyio.CancelScope(shield=True):
                await response.aclose()
