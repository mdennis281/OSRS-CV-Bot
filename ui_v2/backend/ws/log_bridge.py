"""WebSocket bridge: FastAPI WS ↔ core logger WebSocket server."""

import asyncio
import json

import websockets
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from core.logger import get_websocket_port, get_logger

router = APIRouter(tags=["ws"])
log = get_logger("WSBridge")


@router.websocket("/ws/logs")
async def ws_log_bridge(ws: WebSocket):
    """
    Accept a browser WebSocket, open a connection to the core logger WS,
    and forward messages bidirectionally.
    """
    await ws.accept()

    port = get_websocket_port()
    if not port:
        await ws.send_json({"type": "error", "message": "Logger WS not available"})
        await ws.close()
        return

    uri = f"ws://127.0.0.1:{port}"

    try:
        async with websockets.connect(uri) as upstream:

            async def client_to_upstream():
                """Forward messages from browser → core logger."""
                try:
                    while True:
                        data = await ws.receive_text()
                        await upstream.send(data)
                except WebSocketDisconnect:
                    pass

            async def upstream_to_client():
                """Forward messages from core logger → browser."""
                try:
                    async for msg in upstream:
                        await ws.send_text(msg)
                except Exception:
                    pass

            # Run both directions concurrently; when one ends, cancel the other.
            done, pending = await asyncio.wait(
                [
                    asyncio.create_task(client_to_upstream()),
                    asyncio.create_task(upstream_to_client()),
                ],
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in pending:
                task.cancel()

    except Exception as exc:
        log.debug(f"WS bridge error: {exc}")
        try:
            await ws.send_json({"type": "error", "message": str(exc)})
        except Exception:
            pass
    finally:
        try:
            await ws.close()
        except Exception:
            pass
