"""Bot management API router – /api/bots and /api/bot/{bot_id}/*."""

from typing import Any, Dict
from fastapi import APIRouter, HTTPException

from ui_v2.backend.models.bot import (
    BotControlRequest,
    BotStartRequest,
    BotStatusResponse,
    SuccessResponse,
)
from ui_v2.backend.services.bot_manager import BotManagerService

router = APIRouter(prefix="/api", tags=["bots"])

def _mgr() -> BotManagerService:
    return BotManagerService()


@router.get("/bots")
def list_bots() -> Dict[str, Any]:
    mgr = _mgr()
    out: Dict[str, Any] = {}
    for bot_id, bot_info in mgr.bot_registry.items():
        out[bot_id] = {
            "id": bot_info.id,
            "name": bot_info.name,
            "description": bot_info.description,
            "instructions": bot_info.instructions,
            "tier": bot_info.tier,
            "file_path": bot_info.file_path,
            "module_name": bot_info.module_name,
            "config_params": bot_info.config_params,
            "default_config": bot_info.default_config,
        }
    return out


@router.get("/bots/status")
def all_bot_statuses() -> Dict[str, Any]:
    """Return status for every registered bot in a single call."""
    mgr = _mgr()
    return {
        bot_id: mgr.get_bot_status(bot_id)
        for bot_id in mgr.bot_registry
    }


@router.get("/bot/{bot_id}/status")
def bot_status(bot_id: str) -> Dict[str, Any]:
    return _mgr().get_bot_status(bot_id)


@router.post("/bot/{bot_id}/start")
def start_bot(bot_id: str, body: BotStartRequest) -> SuccessResponse:
    ok = _mgr().start_bot(bot_id, body.config, body.username)
    return SuccessResponse(success=ok)


@router.post("/bot/{bot_id}/stop")
def stop_bot(bot_id: str) -> SuccessResponse:
    ok = _mgr().stop_bot(bot_id)
    return SuccessResponse(success=ok)


@router.post("/bot/{bot_id}/control")
def control_bot(bot_id: str, body: BotControlRequest) -> SuccessResponse:
    ok = _mgr().control_bot(bot_id, body.action, body.value)
    return SuccessResponse(success=ok)


@router.get("/bot/{bot_id}/config")
def get_config(bot_id: str) -> Dict[str, Any]:
    mgr = _mgr()
    bot = mgr.bot_registry.get(bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    return bot.config_params


@router.post("/bot/{bot_id}/config")
def save_config(bot_id: str, config_data: Dict[str, Any]) -> SuccessResponse:
    mgr = _mgr()
    bot = mgr.bot_registry.get(bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")

    current = bot.config_params
    for key, value in config_data.items():
        if key in current:
            cur = current[key]
            if isinstance(cur, dict) and "type" in cur and "value" in cur:
                if isinstance(value, dict) and "type" in value and "value" in value:
                    cur["value"] = value["value"]
                else:
                    cur["value"] = value
            else:
                current[key] = value

    if mgr.save_config(bot_id, current):
        return SuccessResponse(success=True)
    raise HTTPException(status_code=500, detail="Failed to save configuration to disk")


@router.post("/bot/{bot_id}/reset")
def reset_config(bot_id: str) -> SuccessResponse:
    mgr = _mgr()
    bot = mgr.bot_registry.get(bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")

    default_params = mgr._extract_config_params(bot.config_class)
    bot.config_params = default_params

    if mgr.save_config(bot_id, default_params):
        return SuccessResponse(success=True)
    raise HTTPException(status_code=500, detail="Failed to save reset configuration to disk")
