"""Logging API router + WebSocket bridge to core logger."""

from typing import Any, Dict
from fastapi import APIRouter

router = APIRouter(tags=["logging"])


@router.get("/api/logging/port")
def get_logging_port() -> Dict[str, Any]:
    from core.logger import get_websocket_port
    port = get_websocket_port()
    return {"port": port}
