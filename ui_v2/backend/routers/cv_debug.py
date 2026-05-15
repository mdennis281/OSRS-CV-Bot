"""CV Debug proxy router – proxies requests to the cv_debug Flask server (port 5055)."""

import asyncio
from typing import Any, Dict, Optional

import httpx
from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

router = APIRouter(prefix="/api/cv-debug", tags=["cv-debug"])

CV_DEBUG_BASE = "http://127.0.0.1:5055"


@router.get("/recent")
async def proxy_recent() -> Dict[str, Any]:
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(f"{CV_DEBUG_BASE}/api/recent", timeout=5)
            return r.json()
        except Exception:
            return {"items": []}


@router.get("/recent_ids")
async def proxy_recent_ids() -> Dict[str, Any]:
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(f"{CV_DEBUG_BASE}/api/recent_ids", timeout=5)
            return r.json()
        except Exception:
            return {"ids": []}


@router.get("/items")
async def proxy_items(ids: str = Query("")) -> Dict[str, Any]:
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(
                f"{CV_DEBUG_BASE}/api/items",
                params={"ids": ids},
                timeout=5,
            )
            return r.json()
        except Exception:
            return {"items": []}


@router.get("/stream")
async def proxy_stream():
    """SSE passthrough from the cv_debug Flask server.

    Retries connecting to upstream with backoff, sending keepalive
    comments while waiting so the EventSource stays open.
    """

    async def event_generator():
        retries = 0
        max_retries = 60  # ~5 min of keepalives then give up
        while retries < max_retries:
            async with httpx.AsyncClient() as client:
                try:
                    async with client.stream(
                        "GET", f"{CV_DEBUG_BASE}/stream", timeout=None
                    ) as resp:
                        retries = 0  # reset on successful connect
                        async for raw in resp.aiter_bytes():
                            yield raw
                        # Stream ended cleanly
                        return
                except Exception:
                    retries += 1
                    yield b": waiting for cv-debug server\n\n"
                    await asyncio.sleep(min(3, 1 + retries * 0.5))
        yield b": upstream unavailable, giving up\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


class ToggleBody(BaseModel):
    enabled: bool = True


@router.get("/status")
async def cv_debug_status() -> Dict[str, Any]:
    """Return whether CV debug is currently enabled."""
    from core import cv_debug as _cv
    return {"enabled": _cv._enabled}


@router.post("/toggle")
async def toggle_cv_debug(body: ToggleBody) -> Dict[str, Any]:
    """Toggle CV debug on/off. Off by default to avoid performance impact."""
    from core import cv_debug
    if body.enabled:
        cv_debug.enable()
    else:
        cv_debug.disable()
    return {"enabled": body.enabled}
