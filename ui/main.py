#!/usr/bin/env python3
"""
OSRS Bot Management UI

A Flask web application for managing and controlling OSRS bots.
Features:
- Discover and list available bots
- Configure bot parameters through web interface
- Start/stop/pause bots
- Monitor bot status and runtime
- Import/export bot configurations
"""

import os
import sys
import json
import time
import threading
import importlib.util
import inspect
import textwrap
from pathlib import Path
from typing import Dict, List, Optional, Type, Any
import subprocess
import requests
import asyncio
import websockets
from datetime import datetime
from dataclasses import dataclass, field, asdict
from core import tools


from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_cors import CORS

# Add the project root to Python path so we can import our modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.item_db import ItemLookup
from bots.core.config import BotConfigMixin
from bots.core.cfg_types import TYPES as CFG_TYPES
from core.logger import get_logger
from core.control import ScriptControl
app = Flask(__name__)
app.secret_key = 'osrs-bot-ui-secret-key-change-in-production'
CORS(app)

log = get_logger("BotUI")

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
    start_time: float
    
    
    def get_elapsed_time(self) -> float:
        return time.time() - self.start_time
    
    def get_elapsed_time_hms(self) -> str:
        elapsed = self.get_elapsed_time()
        return tools.seconds_to_hms(elapsed)
    

# Global bot registry and running bot processes
bot_registry: Dict[str, BotMetadata] = {}
current_bot: Optional[BotInstance] = None
monitoring_thread: Optional[threading.Thread] = None
monitoring_active = False

class BotDiscovery:
    """Discovers and registers available bots from the bots directory"""
    
    @staticmethod
    def discover_bots() -> Dict[str, BotMetadata]:
        """Scan bots directory and return information about available bots"""
        bots_dir = project_root / "bots"
        discovered_bots = {}
        
        if not bots_dir.exists():
            log.error(f"Bots directory not found: {bots_dir}")
            return discovered_bots
        
        # Scan all Python files in bots directory (excluding core subdir)
        for bot_file in bots_dir.glob("*.py"):
            if bot_file.name.startswith("_"):
                continue
                
            try:
                bot_info = BotDiscovery._analyze_bot_file(bot_file)
                if bot_info:
                    discovered_bots[bot_info.id] = bot_info
            except Exception as e:
                log.warning(f"Failed to analyze bot file {bot_file}: {e}")
        
        return discovered_bots
    
    @staticmethod
    def _analyze_bot_file(bot_file: Path) -> Optional[BotMetadata]:
        """Analyze a single bot file to extract configuration and metadata"""
        try:
            spec = importlib.util.spec_from_file_location(bot_file.stem, bot_file)
            if not spec or not spec.loader:
                return None
                
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Look for BotConfig and BotExecutor classes
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
            
            # Extract configuration parameters
            config_params = BotDiscovery._extract_config_params(bot_config_class)
            
            # Get bot metadata
            bot_name = getattr(bot_executor_class, 'name', bot_file.stem.replace('_', ' ').title())
            bot_description = getattr(bot_executor_class, 'description', f'A bot from {bot_file.name}')
            bot_instructions = textwrap.dedent(getattr(bot_executor_class, 'instructions', "")).strip()
            bot_tier = getattr(bot_executor_class, 'tier', '?')
            
            return BotMetadata(
                id=bot_file.stem,
                name=bot_name,
                description=bot_description,
                instructions=bot_instructions,
                tier=bot_tier,
                file_path=str(bot_file),
                module_name=f'bots.{bot_file.stem}',
                config_class=bot_config_class,
                executor_class=bot_executor_class,
                config_params=config_params,
                default_config=BotDiscovery._get_default_config(bot_config_class)
            )
            
        except Exception as e:
            log.error(f"Error analyzing bot file {bot_file}: {e}")
            return None
    
    @staticmethod
    def _extract_config_params(config_class: Type[BotConfigMixin]) -> Dict[str, Dict[str, Any]]:
        """Extract configuration parameters from a BotConfig class"""
        params = {}
        
        # Get class annotations to find typed parameters
        annotations = getattr(config_class, '__annotations__', {})
        
        for param_name, param_type in annotations.items():
            if param_name.startswith('_'):
                continue
                
            # Get the actual parameter instance
            param_instance = getattr(config_class, param_name, None)
            if param_instance is None:
                continue
            
            # Check if it's one of our custom parameter types
            param_type_name = None
            for cfg_type in CFG_TYPES:
                if isinstance(param_instance, cfg_type):
                    param_type_name = cfg_type.type()
                    break
            
            # If it's a custom parameter type, extract its info
            if param_type_name:
                # Special handling for ItemParam
                if param_type_name == "Item":
                    item_data = None
                    if hasattr(param_instance, 'item') and param_instance.item:
                        item_data = {
                            'id': param_instance.item.id,
                            'name': param_instance.item.name,
                            'icon_b64': param_instance.item.icon_b64,
                            'stackable': param_instance.item.stackable,
                            'equipable': param_instance.item.equipable,
                            'tradeable_on_ge': param_instance.item.tradeable_on_ge,
                            'members': param_instance.item.members,
                            'cost': param_instance.item.cost,
                            'highalch': param_instance.item.highalch,
                            'lowalch': param_instance.item.lowalch
                        }
                    
                    params[param_name] = {
                        'type': param_type_name,
                        'value': item_data,
                        'description': f'{param_name.replace("_", " ").title()}'
                    }
                else:
                    # Handle other parameter types
                    param_value = getattr(param_instance, 'value', param_instance)
                    # Ensure the value is JSON serializable
                    try:
                        import json
                        json.dumps(param_value)
                        serializable_value = param_value
                    except (TypeError, ValueError):
                        # If not serializable, convert to string representation
                        serializable_value = str(param_value)
                    
                    params[param_name] = {
                        'type': param_type_name,
                        'value': serializable_value,
                        'description': f'{param_name.replace("_", " ").title()}'
                    }
            else:
                # Handle basic Python types
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
                    else:
                        python_type_name = "List"
                
                if python_type_name:
                    # Ensure the value is JSON serializable
                    try:
                        import json
                        json.dumps(param_instance)
                        serializable_value = param_instance
                    except (TypeError, ValueError):
                        # If not serializable, convert to string representation
                        serializable_value = str(param_instance)
                    
                    params[param_name] = {
                        'type': python_type_name,
                        'value': serializable_value,
                        'description': f'{param_name.replace("_", " ").title()}'
                    }
        
        return params
    
    @staticmethod 
    def _get_default_config(config_class: Type[BotConfigMixin]) -> Dict[str, Any]:
        """Get default configuration values for a bot"""
        try:
            config_instance = config_class()
            return config_instance.export_config()
        except Exception as e:
            log.error(f"Failed to get default config: {e}")
            return {}

def send_websocket_notification(message: str, message_type: str = "info"):
    """Send a notification via WebSocket to connected clients"""
    try:
        from core.logger import get_websocket_port
        port = get_websocket_port()
        if port:
            # Send notification asynchronously
            def send_async():
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(_send_websocket_message(port, message, message_type))
                    loop.close()
                except Exception as e:
                    log.debug(f"Failed to send WebSocket notification: {e}")
            threading.Thread(target=send_async, daemon=True).start()
    except Exception as e:
        log.debug(f"Failed to get WebSocket port for notification: {e}")

async def _send_websocket_message(port: int, message: str, message_type: str):
    """Internal async function to send WebSocket message"""
    try:
        uri = f"ws://127.0.0.1:{port}"
        async with websockets.connect(uri) as websocket:
            await websocket.send(json.dumps({
                "type": "notification",
                "message": message,
                "level": message_type,
                "timestamp": datetime.now().isoformat()
            }))
    except Exception as e:
        log.debug(f"WebSocket send failed: {e}")

def bot_monitoring_thread():
    """Background thread that monitors running bots for termination"""
    global monitoring_active, current_bot

    log.info("Bot monitoring thread started")
    while monitoring_active:
        try:
            if current_bot:
                bot_instance = current_bot
                thread = bot_instance.thread
                bot_id = bot_instance.bot_id                
                # Check if the bot thread has terminated
                if not thread.is_alive():
                    log.info(f"Bot {bot_id} thread has terminated")
                    log.info(f"Bot {bot_id} ran for {bot_instance.get_elapsed_time_hms()}")
                    
                    
                    # Send notification to UI
                    send_websocket_notification(f"Bot '{bot_id}' has terminated", "warning")
                    
                    # Clear the current bot
                    current_bot = None
                    
                    log.info(f"Cleaned up terminated bot {bot_id}")
            
            # Check every 2 seconds
            time.sleep(2)
            
        except Exception as e:
            log.error(f"Error in bot monitoring thread: {e}")
            time.sleep(5)  # Wait longer if there's an error
    
    log.info("Bot monitoring thread stopped")

def start_monitoring():
    """Start the bot monitoring thread"""
    global monitoring_thread, monitoring_active
    
    if not monitoring_active:
        monitoring_active = True
        monitoring_thread = threading.Thread(target=bot_monitoring_thread, daemon=True)
        monitoring_thread.start()
        log.info("Started bot monitoring")

def stop_monitoring():
    """Stop the bot monitoring thread"""
    global monitoring_active
    monitoring_active = False
    log.info("Stopped bot monitoring")

class BotManager:
    """Manages running bot instances"""
    
    @staticmethod
    def start_bot(bot_id: str, config: Dict[str, Any], username: str = '') -> bool:
        """Start a bot with the given configuration"""
        global current_bot
        
        log.info(f"start_bot() called for bot_id: {bot_id}")
        
        try:
            # Stop any currently running bot first
            if current_bot:
                log.info(f"Stopping currently running bot: {current_bot.bot_id}")
                BotManager.stop_bot(current_bot.bot_id)
                
            if current_bot and current_bot.bot_id == bot_id:
                log.warning(f"Bot {bot_id} is already running")
                return False
            
            bot_metadata = bot_registry.get(bot_id)
            if not bot_metadata:
                log.error(f"Bot {bot_id} not found in registry")
                return False
            
            # Import and configure the bot directly
            config_class = bot_metadata.config_class
            executor_class = bot_metadata.executor_class
            
            # Create config instance and apply custom configuration
            bot_config = config_class()
            bot_config.import_config(config)
            
            # Create bot executor instance
            bot_executor = executor_class(bot_config, user=username)
            
            # Start the bot in a separate thread
            bot_thread = threading.Thread(target=bot_executor.start, daemon=True)
            bot_thread.start()
            
            current_bot = BotInstance(
                bot_id=bot_id,
                executor=bot_executor,
                thread=bot_thread,
                config=config,
                username=username,
                start_time=time.time(),
                api_port=5432,
                status='running'
            )
            
            # Start monitoring for bot termination
            start_monitoring()
            
            log.info(f"Started bot {bot_id} successfully")
            return True
            
        except Exception as e:
            log.error(f"Failed to start bot {bot_id}: {e}")
            if current_bot and current_bot.bot_id == bot_id:
                current_bot = None
            return False
    
    @staticmethod
    def stop_bot(bot_id: str) -> bool:
        """Stop a running bot"""
        global current_bot
        
        if not current_bot or current_bot.bot_id != bot_id:
            return False
        
        try:
            bot_instance = current_bot
            executor = bot_instance.executor
            
            # Stop the bot executor gracefully
            if hasattr(executor, 'stop'):
                executor.stop()
            elif hasattr(executor.control, 'terminate'):
                executor.control.terminate = True
            
            current_bot = None
            log.info(f"Stopped bot {bot_id}")
            log.info(f"Bot {bot_id} ran for {bot_instance.get_elapsed_time_hms()}")
            return True
            
        except Exception as e:
            log.error(f"Failed to stop bot {bot_id}: {e}")
            current_bot = None  # Clear it anyway
            return False
    
    @staticmethod
    def get_bot_status(bot_id: str) -> Dict[str, Any]:
        """Get status of a running bot"""
        if not current_bot or current_bot.bot_id != bot_id:
            return {'status': 'not_running'}
        
        bot_instance = current_bot
        thread = bot_instance.thread
        executor = bot_instance.executor
        
        # Check if thread is still alive
        if not thread.is_alive():
            # Thread has ended
            BotManager.stop_bot(bot_id)
            return {'status': 'terminated'}
        
        # Try to get status from executor's control system
        try:
            if hasattr(executor, 'control'):
                control = executor.control
                is_paused = getattr(control, 'pause', False)  # Use 'pause' not 'paused'
                is_terminated = getattr(control, 'terminate', False)

                if is_terminated:
                    return {'status': 'terminated'}
                elif is_paused:
                    return {
                        'status': 'paused',
                        'paused': True,
                        'runtime': time.time() - bot_instance.start_time,
                        'start_time': bot_instance.start_time
                    }
                else:
                    return {
                        'status': 'running',
                        'paused': False,
                        'runtime': time.time() - bot_instance.start_time,
                        'start_time': bot_instance.start_time
                    }
        except Exception as e:
            log.error(f"Error getting bot status for {bot_id}: {e}")
            pass
        
        # Fallback status
        return {
            'status': 'running',
            'runtime': time.time() - bot_instance.start_time,
            'start_time': bot_instance.start_time
        }
    
    @staticmethod
    def control_bot(bot_id: str, action: str, value: Any = None) -> bool:
        """Send control commands to a running bot"""
        if not current_bot or current_bot.bot_id != bot_id:
            return False
        
        try:
            executor = current_bot.executor
            
            if hasattr(executor, 'control'):
                control = executor.control
                
                if action == 'pause':
                    control.pause = value if value is not None else True
                    log.info(f"Bot {bot_id} pause control set to: {control.pause}")
                    # Verify the state was set correctly
                    actual_state = getattr(control, 'pause', None)
                    log.info(f"Bot {bot_id} actual pause state after setting: {actual_state}")
                    return True
                elif action == 'resume':
                    control.pause = False
                    log.info(f"Bot {bot_id} pause control set to: {control.pause}")
                    # Verify the state was set correctly
                    actual_state = getattr(control, 'pause', None)
                    log.info(f"Bot {bot_id} actual pause state after setting: {actual_state}")
                    return True 
                elif action == 'terminate':
                    control.terminate = True
                    log.info(f"Bot {bot_id} termination requested")
                    return True
                    
        except Exception as e:
            log.error(f"Failed to control bot {bot_id}: {e}")
            return False
        
        return False
    


# Flask Routes

@app.route('/')
def index():
    """Main dashboard showing available bots and running bots"""
    return render_template('index.html', 
                         bots=bot_registry,
                         current_bot=get_current_bot_status())

@app.route('/bot/<bot_id>')
def bot_detail(bot_id: str):
    """Bot configuration and control page"""
    bot_info = bot_registry.get(bot_id)
    if not bot_info:
        flash(f"Bot '{bot_id}' not found", 'error')
        return redirect(url_for('index'))
    
    running_status = BotManager.get_bot_status(bot_id)
    
    return render_template('bot_detail.html',
                         bot=bot_info,
                         bots=bot_registry,  # Include bots for sidebar
                         status=running_status,
                         is_running=current_bot and current_bot.bot_id == bot_id)

@app.route('/running')
def running_bot():
    """Running bot monitoring page with logs and CV debug"""
    return render_template('running_bot.html',
                         bots=bot_registry,
                         current_bot=get_current_bot_status())

@app.route('/logs')
def log_viewer():
    """Standalone log viewer page"""
    return render_template('log_viewer.html')

@app.route('/api/bots')
def api_bots():
    """API endpoint to get all available bots"""
    # Filter out non-serializable objects (classes) for JSON response
    serializable_registry = {}
    for bot_id, bot_info in bot_registry.items():
        serializable_registry[bot_id] = {
            'id': bot_info.id,
            'name': bot_info.name, 
            'description': bot_info.description,
            'file_path': bot_info.file_path,
            'module_name': bot_info.module_name,
            'config_params': bot_info.config_params,
            'default_config': bot_info.default_config
            # Exclude 'config_class' and 'executor_class' as they're not JSON serializable
        }
    return jsonify(serializable_registry)

@app.route('/api/bot/<bot_id>/status')
def api_bot_status(bot_id: str):
    """API endpoint to get bot status"""
    return jsonify(BotManager.get_bot_status(bot_id))

@app.route('/api/bot/<bot_id>/start', methods=['POST'])
def api_start_bot(bot_id: str):
    """API endpoint to start a bot"""
    data = request.get_json() or {}
    config = data.get('config', {})
    username = data.get('username', '')
    
    success = BotManager.start_bot(bot_id, config, username)
    return jsonify({'success': success})

@app.route('/api/bot/<bot_id>/stop', methods=['POST'])
def api_stop_bot(bot_id: str):
    """API endpoint to stop a bot"""
    success = BotManager.stop_bot(bot_id)
    return jsonify({'success': success})

@app.route('/api/bot/<bot_id>/control', methods=['POST'])
def api_control_bot(bot_id: str):
    """API endpoint to control a running bot (pause/resume)"""
    data = request.get_json() or {}
    action = data.get('action')
    value = data.get('value')
    
    success = BotManager.control_bot(bot_id, action, value)
    return jsonify({'success': success})

@app.route('/api/bot/<bot_id>/config', methods=['GET'])
def api_get_bot_config(bot_id: str):
    """API endpoint to get bot configuration"""
    bot_info = bot_registry.get(bot_id)
    if not bot_info:
        return jsonify({'error': 'Bot not found'}), 404
    
    # Return the current configuration parameters, not default_config
    # config_params holds the current state including loaded values
    return jsonify(bot_info.config_params)

CONFIG_DIR = project_root / "data" / "configs"

def _save_bot_config_to_disk(bot_id: str, config_data: Dict[str, Any]) -> bool:
    """Save bot configuration to disk"""
    try:
        if not CONFIG_DIR.exists():
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            
        config_file = CONFIG_DIR / f"{bot_id}.json"
        with open(config_file, 'w') as f:
            json.dump(config_data, f, indent=2)
        return True
    except Exception as e:
        log.error(f"Failed to save config for bot {bot_id}: {e}")
        return False

def _load_bot_config_from_disk(bot_id: str) -> Optional[Dict[str, Any]]:
    """Load bot configuration from disk"""
    try:
        config_file = CONFIG_DIR / f"{bot_id}.json"
        if not config_file.exists():
            return None
            
        with open(config_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        log.error(f"Failed to load config for bot {bot_id}: {e}")
        return None

@app.route('/api/bot/<bot_id>/config', methods=['POST'])
def api_save_bot_config(bot_id: str):
    """API endpoint to save bot configuration"""
    bot_info = bot_registry.get(bot_id)
    if not bot_info:
        return jsonify({'error': 'Bot not found'}), 404
    
    config_data = request.get_json()
    if not config_data:
        return jsonify({'error': 'No configuration provided'}), 400
    
    # Validate against known params
    current_params = bot_info.config_params
    
    # Update in-memory registry
    for key, value in config_data.items():
        if key in current_params:
            # Handle structured vs raw values
            current_param = current_params[key]
            
            # Check if we're dealing with our standard parameter structure
            if isinstance(current_param, dict) and 'type' in current_param and 'value' in current_param:
                # If incoming value is also structured (like Item, BreakCfg, Range), extract the value
                if isinstance(value, dict) and 'type' in value and 'value' in value:
                    current_param['value'] = value['value']
                else:
                    # Incoming value is raw (Int, String, Bool), just update the value field
                    current_param['value'] = value
            else:
                # Fallback for unstructured parameters (shouldn't happen with current system)
                current_params[key] = value
            
    # Save to disk
    if _save_bot_config_to_disk(bot_id, current_params):
        log.info(f"Configuration saved for bot {bot_id}")
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'Failed to save configuration to disk'}), 500

@app.route('/api/bot/<bot_id>/reset', methods=['POST'])
def api_reset_bot_config(bot_id: str):
    """API endpoint to reset bot configuration to defaults"""
    bot_info = bot_registry.get(bot_id)
    if not bot_info:
        return jsonify({'error': 'Bot not found'}), 404
    
    try:
        # Get the config class
        config_class = bot_info.config_class
        if not config_class:
            return jsonify({'error': 'Config class not found'}), 500
            
        # Re-extract parameters from the class (this gets the defaults from code)
        default_params = BotDiscovery._extract_config_params(config_class)
        
        # Update registry
        bot_info.config_params = default_params
        
        # Save to disk to persist the reset
        if _save_bot_config_to_disk(bot_id, default_params):
            log.info(f"Configuration reset to defaults for bot {bot_id}")
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Failed to save reset configuration to disk'}), 500
            
    except Exception as e:
        log.error(f"Error resetting config for bot {bot_id}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/logging/port')
def api_logging_port():
    """API endpoint to get the WebSocket logging server port"""
    from core.logger import get_websocket_port
    port = get_websocket_port()
    return jsonify({'port': port})

# Item Database Routes
@app.route('/items')
def items():
    """Item database browser page"""
    return render_template('items.html', title='Item Database')

@app.route('/test')
def test_page():
    """Test page for API debugging"""
    import os
    test_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'test_page.html')
    with open(test_file, 'r', encoding='utf-8') as f:
        return f.read()

@app.route('/js-debug')
def js_debug_page():
    """JavaScript debug test page"""
    import os
    debug_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'js_debug_test.html')
    with open(debug_file, 'r', encoding='utf-8') as f:
        return f.read()

@app.route('/api/items/search')
def api_items_search():
    """API endpoint for searching items"""
    try:
        from core.item_db import ItemLookup
    except Exception as e:
        log.error(f"Failed to import ItemLookup: {e}")
        return jsonify({
            'success': False,
            'error': f'Import error: {str(e)}'
        }), 500
    
    query = request.args.get('q', '').strip()
    limit = int(request.args.get('limit', 50))
    
    # Parse filters
    filters = {}
    if request.args.get('tradeable') == 'true':
        filters['tradeable_on_ge'] = True
    if request.args.get('members') == 'true':
        filters['members'] = True
    if request.args.get('stackable') == 'true':
        filters['stackable'] = True
    if request.args.get('equipable') == 'true':
        filters['equipable'] = True
    
    try:
        item_lookup = ItemLookup()
        if filters:
            items = item_lookup.search_items_advanced(query, filters, limit)
            results = [
                {
                    'id': item.id,
                    'name': item.name,
                    'tradeable_on_ge': item.tradeable_on_ge,
                    'members': item.members,
                    'noted': item.noted,
                    'noteable': item.noteable,
                    'stackable': item.stackable,
                    'equipable': item.equipable,
                    'cost': item.cost,
                    'lowalch': item.lowalch,
                    'highalch': item.highalch,
                    'icon_b64': item.icon_b64
                }
                for item in items
            ]
        else:
            items_dict = item_lookup.search_items(query, limit)
            results = [
                {
                    'id': item.id,
                    'name': item.name,
                    'tradeable_on_ge': item.tradeable_on_ge,
                    'members': item.members,
                    'noted': item.noted,
                    'noteable': item.noteable,
                    'stackable': item.stackable,
                    'equipable': item.equipable,
                    'cost': item.cost,
                    'lowalch': item.lowalch,
                    'highalch': item.highalch,
                    'icon_b64': item.icon_b64
                }
                for item in items_dict.values()
            ]
        
        return jsonify({
            'success': True,
            'results': results,
            'count': len(results)
        })
    except Exception as e:
        log.error(f"Error searching items: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/items/<int:item_id>')
def api_item_detail(item_id):
    """API endpoint for getting detailed item information"""
    
    try:
        item_lookup = ItemLookup()
        item = item_lookup.get_item_by_id(item_id)
        if not item:
            return jsonify({
                'success': False,
                'error': f'Item with ID {item_id} not found'
            }), 404
        return jsonify({
            'success': True,
            'item': {
                'id': item.id,
                'name': item.name,
                'tradeable_on_ge': item.tradeable_on_ge,
                'members': item.members,
                'noted': item.noted,
                'noteable': item.noteable,
                'placeholder': item.placeholder,
                'stackable': item.stackable,
                'equipable': item.equipable,
                'cost': item.cost,
                'lowalch': item.lowalch,
                'highalch': item.highalch,
                'icon_b64': item.icon_b64
            }
        })
    except Exception as e:
        log.error(f"Error getting item detail: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def get_current_bot_status():
    """Get status of the currently running bot"""
    if not current_bot:
        return None
    return {
        'bot_id': current_bot.bot_id,
        'status': BotManager.get_bot_status(current_bot.bot_id),
        'api_port': current_bot.api_port
    }

@app.context_processor
def inject_global_vars():
    """Inject global variables into all templates"""
    return {
        'current_bot': get_current_bot_status(),
        'bots': bot_registry
    }

def initialize_app():
    """Initialize the application by discovering bots"""
    global bot_registry
    
    log.info("Discovering available bots...")
    bot_registry = BotDiscovery.discover_bots()
    log.info(f"Discovered {len(bot_registry)} bots: {list(bot_registry.keys())}")
    
    # Load saved configurations
    log.info("Loading saved configurations...")
    for bot_id, bot_info in bot_registry.items():
        saved_config = _load_bot_config_from_disk(bot_id)
        if saved_config:
            # Merge saved config into current params
            current_params = bot_info.config_params
            for key, value in saved_config.items():
                if key in current_params:
                    # Self-healing: Re-hydrate Item parameters to ensure icons/names are present
                    # This fixes issues where saved config might only have IDs or stale metadata
                    if isinstance(value, dict) and value.get('type') == 'Item':
                        item_data = value.get('value', {})
                        if isinstance(item_data, dict) and 'id' in item_data:
                            try:
                                from core.item_db import ItemLookup
                                # Singleton lookup is fast
                                item = ItemLookup().get_item_by_id(item_data['id'])
                                if item:
                                    # Fully refresh the item metadata
                                    value['value'] = {
                                        'id': item.id,
                                        'name': item.name,
                                        'icon_b64': item.icon_b64,
                                        'stackable': item.stackable,
                                        'equipable': item.equipable,
                                        'tradeable_on_ge': item.tradeable_on_ge,
                                        'members': item.members,
                                        'cost': item.cost,
                                        'highalch': item.highalch,
                                        'lowalch': item.lowalch
                                    }
                            except Exception as e:
                                log.warning(f"Failed to re-hydrate item {key} for bot {bot_id}: {e}")

                    current_params[key] = value
            log.info(f"Loaded config for {bot_id}")

    # Start the WebSocket logging server
    log.info("Starting WebSocket logging server...")
    from core.logger import ensure_websocket_server_started
    ensure_websocket_server_started()
    log.info("WebSocket logging server ready")
    
    # Register cleanup function
    import atexit
    atexit.register(cleanup_on_exit)

def cleanup_on_exit():
    """Clean up running bot when the application exits"""
    log.info("Cleaning up running bot...")
    if current_bot:
        BotManager.stop_bot(current_bot.bot_id)

@app.after_request
def add_cache_headers(response):
    """Add caching headers for static resources to improve performance"""
    if request.endpoint == 'static':
        # Cache static files for 1 hour
        response.cache_control.max_age = 3600
        response.cache_control.public = True
    elif request.path.startswith('/api/'):
        # Don't cache API responses
        response.cache_control.no_cache = True
        response.cache_control.no_store = True
        response.cache_control.must_revalidate = True
    else:
        # Cache HTML pages for 5 minutes
        response.cache_control.max_age = 300
    return response

if __name__ == '__main__':
    initialize_app()
