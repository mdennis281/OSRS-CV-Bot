"""
Bot discovery, lifecycle, and configuration persistence service.

Ports the BotDiscovery, BotManager, and config persistence logic from ui/main.py.
"""

import importlib.util
import inspect
import json
import textwrap
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Type
from dataclasses import dataclass

from core.item_db import ItemLookup
from core.logger import get_logger
from core.control import ScriptControl
from core import tools
from bots.core.config import BotConfigMixin
from bots.core.cfg_types import TYPES as CFG_TYPES

log = get_logger("BotManager")

project_root = Path(__file__).parent.parent.parent.parent  # ui_v2/backend/services/ -> repo root
CONFIG_DIR = project_root / "data" / "configs"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class BotMetadata:
    id: str
    name: str
    description: str
    instructions: str
    tier: str
    file_path: str
    module_name: str
    config_class: Type[BotConfigMixin]
    executor_class: Type[Any]
    config_params: Dict[str, Any]
    default_config: Dict[str, Any]


@dataclass
class BotInstance:
    bot_id: str
    executor: Any
    thread: threading.Thread
    config: Dict[str, Any]
    username: str
    start_time: float
    api_port: int
    status: str

    def get_elapsed_time(self) -> float:
        return time.time() - self.start_time

    def get_elapsed_time_hms(self) -> str:
        return tools.seconds_to_hms(self.get_elapsed_time())


# ---------------------------------------------------------------------------
# Singleton service
# ---------------------------------------------------------------------------

class BotManagerService:
    """Singleton that manages bot registry, running instance, monitoring."""

    _instance: Optional["BotManagerService"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized"):
            return
        self._initialized = True
        self.bot_registry: Dict[str, BotMetadata] = {}
        self.current_bot: Optional[BotInstance] = None
        self._monitoring_active = False
        self._monitoring_thread: Optional[threading.Thread] = None

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def discover_bots(self) -> Dict[str, BotMetadata]:
        bots_dir = project_root / "bots"
        discovered: Dict[str, BotMetadata] = {}

        if not bots_dir.exists():
            log.error(f"Bots directory not found: {bots_dir}")
            return discovered

        for bot_file in bots_dir.glob("*.py"):
            if bot_file.name.startswith("_"):
                continue
            try:
                info = self._analyze_bot_file(bot_file)
                if info:
                    discovered[info.id] = info
            except Exception as e:
                log.warning(f"Failed to analyze bot file {bot_file}: {e}")

        return discovered

    def _analyze_bot_file(self, bot_file: Path) -> Optional[BotMetadata]:
        try:
            spec = importlib.util.spec_from_file_location(bot_file.stem, bot_file)
            if not spec or not spec.loader:
                return None

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            bot_config_class = None
            bot_executor_class = None

            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and name == "BotConfig":
                    if issubclass(obj, BotConfigMixin):
                        bot_config_class = obj
                elif inspect.isclass(obj) and name == "BotExecutor":
                    bot_executor_class = obj

            if not bot_config_class or not bot_executor_class:
                return None

            config_params = self._extract_config_params(bot_config_class)

            return BotMetadata(
                id=bot_file.stem,
                name=getattr(bot_executor_class, "name", bot_file.stem.replace("_", " ").title()),
                description=getattr(bot_executor_class, "description", f"A bot from {bot_file.name}"),
                instructions=textwrap.dedent(getattr(bot_executor_class, "instructions", "")).strip(),
                tier=getattr(bot_executor_class, "tier", "?"),
                file_path=str(bot_file),
                module_name=f"bots.{bot_file.stem}",
                config_class=bot_config_class,
                executor_class=bot_executor_class,
                config_params=config_params,
                default_config=self._get_default_config(bot_config_class),
            )
        except Exception as e:
            log.error(f"Error analyzing bot file {bot_file}: {e}")
            return None

    @staticmethod
    def _extract_config_params(config_class: Type[BotConfigMixin]) -> Dict[str, Dict[str, Any]]:
        params: Dict[str, Dict[str, Any]] = {}
        annotations = getattr(config_class, "__annotations__", {})

        for param_name, _ in annotations.items():
            if param_name.startswith("_"):
                continue

            param_instance = getattr(config_class, param_name, None)
            if param_instance is None:
                continue

            param_type_name = None
            for cfg_type in CFG_TYPES:
                if isinstance(param_instance, cfg_type):
                    param_type_name = cfg_type.type()
                    break

            if param_type_name:
                if param_type_name == "Item":
                    item_data = None
                    if hasattr(param_instance, "item") and param_instance.item:
                        item_data = {
                            "id": param_instance.item.id,
                            "name": param_instance.item.name,
                            "icon_b64": param_instance.item.icon_b64,
                            "stackable": param_instance.item.stackable,
                            "equipable": param_instance.item.equipable,
                            "tradeable_on_ge": param_instance.item.tradeable_on_ge,
                            "members": param_instance.item.members,
                            "cost": param_instance.item.cost,
                            "highalch": param_instance.item.highalch,
                            "lowalch": param_instance.item.lowalch,
                        }
                    params[param_name] = {
                        "type": param_type_name,
                        "value": item_data,
                        "description": param_name.replace("_", " ").title(),
                    }
                elif param_type_name == "ItemList":
                    items_data = []
                    for item_param in param_instance:
                        if hasattr(item_param, "item") and item_param.item:
                            items_data.append({
                                "type": "Item",
                                "value": {
                                    "id": item_param.item.id,
                                    "name": item_param.item.name,
                                    "icon_b64": item_param.item.icon_b64,
                                    "stackable": item_param.item.stackable,
                                    "equipable": item_param.item.equipable,
                                    "tradeable_on_ge": item_param.item.tradeable_on_ge,
                                    "members": item_param.item.members,
                                    "cost": item_param.item.cost,
                                    "highalch": item_param.item.highalch,
                                    "lowalch": item_param.item.lowalch,
                                }
                            })
                    params[param_name] = {
                        "type": param_type_name,
                        "value": items_data,
                        "description": param_name.replace("_", " ").title(),
                    }
                else:
                    # Use to_json() when available for structured output
                    if hasattr(param_instance, "to_json"):
                        json_repr = param_instance.to_json()
                        params[param_name] = {
                            "type": param_type_name,
                            "value": json_repr.get("value", json_repr),
                            "description": param_name.replace("_", " ").title(),
                        }
                    else:
                        param_value = getattr(param_instance, "value", param_instance)
                        try:
                            json.dumps(param_value)
                            serializable_value = param_value
                        except (TypeError, ValueError):
                            serializable_value = str(param_value)

                        params[param_name] = {
                            "type": param_type_name,
                            "value": serializable_value,
                            "description": param_name.replace("_", " ").title(),
                        }
            else:
                python_type_name = None
                if isinstance(param_instance, bool):
                    python_type_name = "Boolean"
                elif isinstance(param_instance, int):
                    python_type_name = "Int"
                elif isinstance(param_instance, float):
                    python_type_name = "Float"
                elif isinstance(param_instance, str):
                    python_type_name = "String"
                elif isinstance(param_instance, list):
                    if all(isinstance(item, str) for item in param_instance):
                        python_type_name = "StringList"
                    elif param_instance and all(
                        hasattr(item, "type") and callable(item.type) and item.type() == "Item"
                        for item in param_instance
                    ):
                        # bare list[ItemParam] → treat as ItemList
                        python_type_name = "ItemList"
                        items_data = []
                        for item_param in param_instance:
                            if hasattr(item_param, "item") and item_param.item:
                                items_data.append({
                                    "type": "Item",
                                    "value": {
                                        "id": item_param.item.id,
                                        "name": item_param.item.name,
                                        "icon_b64": item_param.item.icon_b64,
                                        "stackable": item_param.item.stackable,
                                        "equipable": item_param.item.equipable,
                                        "tradeable_on_ge": item_param.item.tradeable_on_ge,
                                        "members": item_param.item.members,
                                        "cost": item_param.item.cost,
                                        "highalch": item_param.item.highalch,
                                        "lowalch": item_param.item.lowalch,
                                    }
                                })
                        params[param_name] = {
                            "type": python_type_name,
                            "value": items_data,
                            "description": param_name.replace("_", " ").title(),
                        }
                        continue
                    elif param_instance and all(
                        hasattr(item, "type") and callable(item.type) and item.type() == "RGB"
                        for item in param_instance
                    ):
                        # bare list[RGBParam] → treat as RGBList
                        python_type_name = "RGBList"
                        params[param_name] = {
                            "type": python_type_name,
                            "value": [rgb.to_json() for rgb in param_instance],
                            "description": param_name.replace("_", " ").title(),
                        }
                        continue
                    else:
                        python_type_name = "List"

                if python_type_name:
                    try:
                        json.dumps(param_instance)
                        serializable_value = param_instance
                    except (TypeError, ValueError):
                        serializable_value = str(param_instance)

                    params[param_name] = {
                        "type": python_type_name,
                        "value": serializable_value,
                        "description": param_name.replace("_", " ").title(),
                    }

        return params

    @staticmethod
    def _get_default_config(config_class: Type[BotConfigMixin]) -> Dict[str, Any]:
        try:
            return config_class().export_config()
        except Exception as e:
            log.error(f"Failed to get default config: {e}")
            return {}

    # ------------------------------------------------------------------
    # Config persistence
    # ------------------------------------------------------------------

    def save_config(self, bot_id: str, config_data: Dict[str, Any]) -> bool:
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            config_file = CONFIG_DIR / f"{bot_id}.json"
            with open(config_file, "w") as f:
                json.dump(config_data, f, indent=2)
            return True
        except Exception as e:
            log.error(f"Failed to save config for bot {bot_id}: {e}")
            return False

    def load_config(self, bot_id: str) -> Optional[Dict[str, Any]]:
        try:
            config_file = CONFIG_DIR / f"{bot_id}.json"
            if not config_file.exists():
                return None
            with open(config_file, "r") as f:
                return json.load(f)
        except Exception as e:
            log.error(f"Failed to load config for bot {bot_id}: {e}")
            return None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start_bot(self, bot_id: str, config: Dict[str, Any], username: str = "") -> bool:
        log.info(f"start_bot() called for bot_id: {bot_id}")
        try:
            if self.current_bot:
                log.info(f"Stopping currently running bot: {self.current_bot.bot_id}")
                self.stop_bot(self.current_bot.bot_id)

            bot_metadata = self.bot_registry.get(bot_id)
            if not bot_metadata:
                log.error(f"Bot {bot_id} not found in registry")
                return False

            config_class = bot_metadata.config_class
            executor_class = bot_metadata.executor_class

            bot_config = config_class()
            bot_config.import_config(config)

            bot_executor = executor_class(bot_config, user=username)

            def _run_bot(executor=bot_executor, bid=bot_id):
                try:
                    executor.start()
                except Exception:
                    import traceback
                    log.error(f"Bot {bid} raised an unhandled exception:\n{traceback.format_exc()}")

            bot_thread = threading.Thread(target=_run_bot, daemon=True)
            bot_thread.start()

            self.current_bot = BotInstance(
                bot_id=bot_id,
                executor=bot_executor,
                thread=bot_thread,
                config=config,
                username=username,
                start_time=time.time(),
                api_port=5432,
                status="running",
            )

            self._start_monitoring()
            log.info(f"Started bot {bot_id} successfully")
            return True
        except Exception as e:
            log.error(f"Failed to start bot {bot_id}: {e}")
            if self.current_bot and self.current_bot.bot_id == bot_id:
                self.current_bot = None
            return False

    def stop_bot(self, bot_id: str) -> bool:
        if not self.current_bot or self.current_bot.bot_id != bot_id:
            return False
        try:
            executor = self.current_bot.executor
            if hasattr(executor, "stop"):
                executor.stop()
            elif hasattr(executor, "control") and hasattr(executor.control, "terminate"):
                executor.control.terminate = True

            elapsed = self.current_bot.get_elapsed_time_hms()
            self.current_bot = None
            log.info(f"Stopped bot {bot_id} (ran {elapsed})")
            return True
        except Exception as e:
            log.error(f"Failed to stop bot {bot_id}: {e}")
            self.current_bot = None
            return False

    def get_bot_status(self, bot_id: str) -> Dict[str, Any]:
        if not self.current_bot or self.current_bot.bot_id != bot_id:
            return {"status": "not_running"}

        if not self.current_bot.thread.is_alive():
            self.stop_bot(bot_id)
            return {"status": "terminated"}

        try:
            if hasattr(self.current_bot.executor, "control"):
                control = self.current_bot.executor.control
                is_paused = getattr(control, "pause", False)
                is_terminated = getattr(control, "terminate", False)
                runtime = time.time() - self.current_bot.start_time

                if is_terminated:
                    return {"status": "terminated"}

                return {
                    "status": "paused" if is_paused else "running",
                    "paused": is_paused,
                    "runtime": runtime,
                    "runtime_formatted": tools.seconds_to_hms(runtime),
                    "start_time": self.current_bot.start_time,
                }
        except Exception as e:
            log.error(f"Error getting bot status for {bot_id}: {e}")

        return {
            "status": "running",
            "runtime": time.time() - self.current_bot.start_time,
            "start_time": self.current_bot.start_time,
        }

    def control_bot(self, bot_id: str, action: str, value: Any = None) -> bool:
        if not self.current_bot or self.current_bot.bot_id != bot_id:
            return False
        try:
            executor = self.current_bot.executor
            if hasattr(executor, "control"):
                control = executor.control
                if action == "pause":
                    control.pause = value if value is not None else True
                    return True
                elif action == "resume":
                    control.pause = False
                    return True
                elif action == "terminate":
                    control.terminate = True
                    return True
        except Exception as e:
            log.error(f"Failed to control bot {bot_id}: {e}")
        return False

    def get_current_bot_status(self) -> Optional[Dict[str, Any]]:
        if not self.current_bot:
            return None
        return {
            "bot_id": self.current_bot.bot_id,
            "status": self.get_bot_status(self.current_bot.bot_id),
            "api_port": self.current_bot.api_port,
        }

    # ------------------------------------------------------------------
    # Monitoring
    # ------------------------------------------------------------------

    def _start_monitoring(self):
        if not self._monitoring_active:
            self._monitoring_active = True
            self._monitoring_thread = threading.Thread(
                target=self._monitoring_loop, daemon=True
            )
            self._monitoring_thread.start()

    def _monitoring_loop(self):
        log.info("Bot monitoring thread started")
        while self._monitoring_active:
            try:
                if self.current_bot:
                    if not self.current_bot.thread.is_alive():
                        bot_id = self.current_bot.bot_id
                        elapsed = self.current_bot.get_elapsed_time_hms()
                        log.info(f"Bot {bot_id} thread terminated ({elapsed})")
                        self._send_notification(f"Bot '{bot_id}' has terminated", "warning")
                        self.current_bot = None
                time.sleep(2)
            except Exception as e:
                log.error(f"Error in monitoring thread: {e}")
                time.sleep(5)

    @staticmethod
    def _send_notification(message: str, level: str = "info"):
        """Best-effort WebSocket notification."""
        try:
            import asyncio
            import websockets as _ws
            from core.logger import get_websocket_port

            port = get_websocket_port()
            if not port:
                return

            async def _send():
                uri = f"ws://127.0.0.1:{port}"
                async with _ws.connect(uri) as ws:
                    await ws.send(json.dumps({
                        "type": "notification",
                        "message": message,
                        "level": level,
                    }))

            def _run():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(_send())
                except Exception:
                    pass
                finally:
                    loop.close()

            threading.Thread(target=_run, daemon=True).start()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def initialize(self):
        """Discover bots, load saved configs, start WS logging server."""
        log.info("Discovering available bots...")
        self.bot_registry = self.discover_bots()
        log.info(f"Discovered {len(self.bot_registry)} bots: {list(self.bot_registry.keys())}")

        log.info("Loading saved configurations...")
        for bot_id, bot_info in self.bot_registry.items():
            saved = self.load_config(bot_id)
            if saved:
                current = bot_info.config_params
                for key, value in saved.items():
                    if key not in current:
                        continue

                    # Self-healing item re-hydration
                    if isinstance(value, dict) and value.get("type") == "Item":
                        item_data = value.get("value", {})
                        if isinstance(item_data, dict) and "id" in item_data:
                            try:
                                item = ItemLookup().get_item_by_id(item_data["id"])
                                if item:
                                    value["value"] = {
                                        "id": item.id,
                                        "name": item.name,
                                        "icon_b64": item.icon_b64,
                                        "stackable": item.stackable,
                                        "equipable": item.equipable,
                                        "tradeable_on_ge": item.tradeable_on_ge,
                                        "members": item.members,
                                        "cost": item.cost,
                                        "highalch": item.highalch,
                                        "lowalch": item.lowalch,
                                    }
                            except Exception as e:
                                log.warning(f"Failed to re-hydrate item {key} for bot {bot_id}: {e}")

                    # Merge: keep the authoritative type from discovery,
                    # only overlay the saved value.
                    fresh = current[key]
                    if (
                        isinstance(fresh, dict) and "type" in fresh
                        and isinstance(value, dict) and "value" in value
                    ):
                        fresh["value"] = value["value"]
                    else:
                        current[key] = value

                log.info(f"Loaded config for {bot_id}")

        log.info("Starting WebSocket logging server...")
        from core.logger import ensure_websocket_server_started
        ensure_websocket_server_started()
        log.info("WebSocket logging server ready")
