"""Pydantic models for bot metadata, status, and config."""

from typing import Any, Dict, Optional
from pydantic import BaseModel


class BotInfo(BaseModel):
    id: str
    name: str
    description: str
    instructions: str = ""
    tier: str = "?"
    file_path: str
    module_name: str
    config_params: Dict[str, Any] = {}
    default_config: Dict[str, Any] = {}


class BotStatusResponse(BaseModel):
    status: str  # running | paused | terminated | not_running
    paused: Optional[bool] = None
    runtime: Optional[float] = None
    runtime_formatted: Optional[str] = None
    start_time: Optional[float] = None


class BotStartRequest(BaseModel):
    config: Dict[str, Any] = {}
    username: str = ""


class BotControlRequest(BaseModel):
    action: str  # pause | resume | terminate
    value: Optional[Any] = None


class SuccessResponse(BaseModel):
    success: bool
    error: Optional[str] = None
