import logging
from logging import StreamHandler
from logging.handlers import RotatingFileHandler
from typing import Optional
import threading
import asyncio
import json
import websockets
import time  # Add time module import

# Track when the application started
_start_time = time.time()

# ------------------------------------------------------------------------------
# --- Global state for the WebSocket server and connected clients -------------
# ------------------------------------------------------------------------------

# Set of currently connected WebSocket client objects
_ws_clients: set[websockets.WebSocketServerProtocol] = set()

# Will hold the asyncio event loop in which the WebSocket server runs
_ws_event_loop: asyncio.AbstractEventLoop | None = None

# Simple lock to ensure we only start the server once
_ws_start_lock = threading.Lock()
_ws_server_started = False

# Track the actual port the WebSocket server is running on
_ws_server_port = None
_ws_server_ready = threading.Event()

# Function to get logger names - will be set by LoggerWrapper
_get_logger_names = None

# Function to set log level - will be set by LoggerWrapper 
_set_logger_level = None

# ----------------------------------------------------------------------------
# --- WebSocket API Schemas and Commands ---------------------------------------
# ----------------------------------------------------------------------------
"""
WebSocket API for Logger System

Client -> Server Commands:
--------------------------
1. Get All Loggers:
   { "command": "get_loggers" }
   
   Response:
   { "type": "loggers_list", "loggers": ["logger1", "logger2", ...] }

2. Get Logger Info:
   { "command": "get_logger_info", "logger_name": "my_logger" }
   
   Response:
   { 
     "type": "logger_info", 
     "logger": "my_logger", 
     "level": "INFO",
     "handlers": ["console", "file", "websocket"] 
   }

3. Set Logger Level:
   { "command": "set_logger_level", "logger_name": "my_logger", "level": "DEBUG" }
   
   Response:
   { "type": "level_changed", "logger": "my_logger", "level": "DEBUG" }

4. Subscribe To Specific Loggers:
   { "command": "subscribe", "loggers": ["logger1", "logger2"] }
   
   Response:
   { "type": "subscription_changed", "subscribed": ["logger1", "logger2"] }

5. Ping/Health Check:
   { "command": "ping" }
   
   Response:
   { "type": "pong", "timestamp": "12:34:56", "active_connections": 3 }

Server -> Client Messages:
-------------------------
1. Log Message:
   {
     "type": "log",
     "timestamp": "00:12:34", 
     "logger_name": "my_logger",
     "level": "INFO",
     "message": "This is a log message"
   }

2. Error Response:
   {
     "type": "error",
     "error_code": "unknown_logger",
     "message": "Logger 'unknown' does not exist"
   }
"""

# ------------------------------------------------------------------------------
# --- WebSocket‐streaming Log Handler ------------------------------------------
# ------------------------------------------------------------------------------

# Global client subscriptions dictionary to be shared between functions
client_subscriptions = {}

class WebSocketLogHandler(logging.Handler):
    """
    A logging.Handler that serializes each LogRecord to JSON and pushes it
    to all currently connected WebSocket clients.
    """
    def __init__(self):
        super().__init__()
        # We'll use our own JSON formatting; no need for a Formatter here.

    def formatTime(self, record, datefmt=None):
        """Format the time using elapsed time since program start."""
        elapsed_seconds = record.created - _start_time
        hours, remainder = divmod(int(elapsed_seconds), 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02}:{minutes:02}:{seconds:02}"

    def emit(self, record: logging.LogRecord) -> None:
        try:
            # Build a dictionary containing all the context we want:
            payload = {
                "type": "log",
                "timestamp": self.formatTime(record),
                "logger_name": record.name,
                "level": record.levelname,
                "message": record.getMessage(),
                # Optional: include extra fields if present
                **(record.__dict__.get("extra", {})),  
            }
            text = json.dumps(payload)
        except Exception as e:
            # If formatting fails, log error and bail
            print(f"Error formatting log: {e}")
            return

        # Schedule sending to clients on the websocket event loop
        if _ws_event_loop and _ws_event_loop.is_running():
            asyncio.run_coroutine_threadsafe(self._broadcast(text, record.name), _ws_event_loop)

    async def _broadcast(self, text: str, logger_name: str) -> None:
        """
        Asynchronously send `text` to every connected WebSocket client
        that is subscribed to this logger.
        """
        global client_subscriptions
        
        to_remove = []
        for ws in _ws_clients:
            try:
                # Check if this client is subscribed to this logger
                subscribed_loggers = client_subscriptions.get(ws)
                # Send if subscribed to all (None) or specifically to this logger
                if subscribed_loggers is None or logger_name in subscribed_loggers:
                    await ws.send(text)
            except Exception as e:
                print(f"Error sending to client: {e}")
                # If sending fails, mark for removal
                to_remove.append(ws)

        # Clean up any dead connections
        for ws in to_remove:
            _ws_clients.discard(ws)
            if ws in client_subscriptions:
                del client_subscriptions[ws]


# ------------------------------------------------------------------------------
# --- Function to start the WebSocket server inside a daemon thread -----------
# ------------------------------------------------------------------------------

def _start_websocket_server(host: str = "0.0.0.0", port: int = 18765) -> None:
    """
    This function is intended to run in its own thread. It creates a new
    asyncio loop, starts a simple WebSocket server, and runs forever.
    """
    global _ws_event_loop, _ws_server_started, client_subscriptions
    
    try:
        # Create and set a fresh event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        _ws_event_loop = loop
    except Exception as e:
        print(f"[WebSocketLogHandler] Failed to create event loop: {e}")
        import traceback
        traceback.print_exc()
        _ws_server_ready.set()  # Signal that we're done (with error)
        return

    # Client subscriptions - maps websocket to list of loggers they're subscribed to
    # None means "all loggers" (default)
    global client_subscriptions
    client_subscriptions = {}

    async def ws_handler(ws: websockets.WebSocketServerProtocol):
        # When a client connects, add it to our set
        _ws_clients.add(ws)
        print(f"[WebSocketLogHandler] Client connected: {ws.remote_address}")
        client_subscriptions[ws] = None  # Subscribe to all loggers by default
        try:
            # Keep the connection open and handle messages
            async for message in ws:
                try:
                    data = json.loads(message)
                    command = data.get('command')
                    
                    if command == 'get_loggers' and _get_logger_names:
                        # Get the list of logger names
                        logger_names = _get_logger_names()
                        await ws.send(json.dumps({
                            'type': 'loggers_list',
                            'loggers': logger_names
                        }))
                        
                    elif command == 'get_logger_info' and _get_logger_names:
                        logger_name = data.get('logger_name')
                        if not logger_name or logger_name not in _get_logger_names():
                            await ws.send(json.dumps({
                                'type': 'error',
                                'error_code': 'unknown_logger',
                                'message': f"Logger '{logger_name}' does not exist"
                            }))
                        else:
                            # This would need logger_info functionality to be implemented
                            # For now, just return basic info we know
                            await ws.send(json.dumps({
                                'type': 'logger_info',
                                'logger': logger_name,
                                'level': 'INFO',  # Simplified - would need actual level
                                'handlers': ['console', 'websocket']  # Basic assumption
                            }))
                            
                    elif command == 'set_logger_level' and _set_logger_level:
                        logger_name = data.get('logger_name')
                        level = data.get('level')
                        try:
                            _set_logger_level(logger_name, level)
                            await ws.send(json.dumps({
                                'type': 'level_changed',
                                'logger': logger_name,
                                'level': level
                            }))
                        except Exception as e:
                            await ws.send(json.dumps({
                                'type': 'error',
                                'error_code': 'level_change_failed',
                                'message': str(e)
                            }))
                            
                    elif command == 'subscribe':
                        loggers = data.get('loggers')
                        if loggers is None:
                            client_subscriptions[ws] = None  # All loggers
                        else:
                            client_subscriptions[ws] = list(loggers)
                        await ws.send(json.dumps({
                            'type': 'subscription_changed',
                            'subscribed': loggers if loggers else "all"
                        }))
                        
                    elif command == 'ping':
                        elapsed = time.time() - _start_time
                        hours, remainder = divmod(int(elapsed), 3600)
                        minutes, seconds = divmod(remainder, 60)
                        timestamp = f"{hours:02}:{minutes:02}:{seconds:02}"
                        await ws.send(json.dumps({
                            'type': 'pong',
                            'timestamp': timestamp,
                            'active_connections': len(_ws_clients)
                        }))
                        
                    else:
                        await ws.send(json.dumps({
                            'type': 'error',
                            'error_code': 'unknown_command',
                            'message': f"Unknown command: {command}"
                        }))
                        
                except json.JSONDecodeError:
                    await ws.send(json.dumps({
                        'type': 'error',
                        'error_code': 'invalid_json',
                        'message': "Invalid JSON message"
                    }))
                except Exception as e:
                    print(f"Error handling WebSocket message: {e}")
                    await ws.send(json.dumps({
                        'type': 'error',
                        'error_code': 'server_error',
                        'message': str(e)
                    }))
        finally:
            _ws_clients.discard(ws)
            if ws in client_subscriptions:
                del client_subscriptions[ws]

    # Define the WebSocket server startup in an async function
    async def start_server():
        global _ws_server_port
        # Try multiple ports if the default is in use
        ports_to_try = [port, port + 1, port + 2, port + 3, port + 4]
        for try_port in ports_to_try:
            try:
                server = await websockets.serve(ws_handler, host, try_port)
                _ws_server_port = try_port  # Store the actual port being used
                print(f"[WebSocketLogHandler] Running on ws://{host}:{try_port}/")
                _ws_server_ready.set()  # Signal that the server is ready
                return server
            except OSError as e:
                if "Only one usage of each socket address" in str(e) or "10048" in str(e):
                    continue
                else:
                    raise e
        raise OSError(f"Could not bind to any port in range {ports_to_try}")

    # Start the WebSocket server
    try:
        server = loop.run_until_complete(start_server())
    except Exception as e:
        print(f"[WebSocketLogHandler] Failed to start server: {e}")
        _ws_server_ready.set()  # Signal that we're done (with error)
        return

    try:
        loop.run_forever()
    except Exception as e:
        print(f"[WebSocketLogHandler] Event loop error: {e}")
    finally:
        # Clean up if the loop ever stops
        try:
            server.close()
            loop.run_until_complete(server.wait_closed())
            loop.close()
        except Exception as e:
            print(f"[WebSocketLogHandler] Cleanup error: {e}")


def _ensure_ws_thread_started():
    """
    Guarantee that the WebSocket server thread is up and running.
    Only starts one server instance across all logger instances.
    """
    global _ws_server_started
    with _ws_start_lock:
        if not _ws_server_started:
            _ws_server_started = True
            
            # Wrap the target function to catch any exceptions
            def safe_start():
                try:
                    _start_websocket_server()
                except Exception as e:
                    print(f"[WebSocketLogHandler] Thread exception: {e}")
                    import traceback
                    traceback.print_exc()
                    _ws_server_ready.set()  # Signal that we're done (with error)
            
            t = threading.Thread(target=safe_start, daemon=True)
            t.start()

def get_websocket_port() -> Optional[int]:
    """
    Get the port the WebSocket log server is running on.
    Returns None if the server hasn't started yet.
    """
    global _ws_server_port
    return _ws_server_port

def ensure_websocket_server_started() -> None:
    """
    Ensure the WebSocket server is started.
    Can be called multiple times safely.
    """
    _ensure_ws_thread_started()
    # Wait up to 5 seconds for the server to be ready
    if not _ws_server_ready.wait(timeout=5.0):
        print("[WebSocketLogHandler] Warning: Server didn't start within 5 seconds")


# ------------------------------------------------------------------------------
# --- Custom elapsed time formatter --------------------------------------------
# ------------------------------------------------------------------------------

class ElapsedTimeFormatter(logging.Formatter):
    """
    A formatter that shows time elapsed since program start in format hh:mm:ss
    """
    def formatTime(self, record, datefmt=None):
        elapsed_seconds = record.created - _start_time
        hours, remainder = divmod(int(elapsed_seconds), 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02}:{minutes:02}:{seconds:02}"


# ------------------------------------------------------------------------------
# --- LoggerWrapper (with WebSocket integration) -------------------------------
# ------------------------------------------------------------------------------

default_log_level = logging.DEBUG  # Default log level if not specified

class LoggerWrapper:
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LoggerWrapper, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        # Only initialize once
        if LoggerWrapper._initialized:
            return
        LoggerWrapper._initialized = True
        
        self._loggers: dict[str, logging.Logger] = {}
        # Set the global functions to access logger data
        global _get_logger_names, _set_logger_level
        _get_logger_names = self.get_logger_names
        _set_logger_level = self.set_logger_level
        # Kick off the WebSocket server thread on first use:
        _ensure_ws_thread_started()
        # Configure root logger to WARNING to reduce noise from external libraries
        logging.basicConfig(level=logging.WARNING)  # Changed from DEBUG to WARNING
    
    def get_logger_names(self) -> list[str]:
        """
        Returns a list of all logger names currently managed by this wrapper.
        """
        return list(self._loggers.keys())

    def get_logger(
        self,
        name: str,
        log_to_file: Optional[str] = None,
        level: int = logging.INFO
    ) -> logging.Logger:
        # If we’ve already created this logger, just return it
        if name in self._loggers:
            return self._loggers[name]

        # Otherwise, set up a fresh logger
        logger = logging.getLogger(name)
        logger.setLevel(level)
        logger.propagate = False  # Prevent messages from going to the root logger twice

        # 1) Console handler
        console_handler = StreamHandler()
        console_handler.setFormatter(self._get_default_formatter())
        logger.addHandler(console_handler)

        # 2) Optional file handler
        if log_to_file:
            file_handler = RotatingFileHandler(
                log_to_file,
                maxBytes=5 * 1024 * 1024,
                backupCount=3
            )
            file_handler.setFormatter(self._get_default_formatter())
            logger.addHandler(file_handler)

        # 3) WebSocket handler
        ws_handler = WebSocketLogHandler()
        # Make sure it listens at the same level (or more permissive) than the logger
        ws_handler.setLevel(level)
        logger.addHandler(ws_handler)

        self._loggers[name] = logger
        return logger

    @staticmethod
    def _get_default_formatter() -> logging.Formatter:
        return ElapsedTimeFormatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

    def set_logger_level(self, logger_name: str, level: str) -> None:
        """
        Set the logging level for a specific logger.
        
        Args:
            logger_name: The name of the logger to modify
            level: Level name ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
        
        Raises:
            ValueError: If logger_name doesn't exist or level is invalid
        """
        if logger_name not in self._loggers:
            raise ValueError(f"Logger '{logger_name}' does not exist")
            
        level_map = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }
        
        if level not in level_map:
            raise ValueError(f"Invalid log level: {level}")
            
        self._loggers[logger_name].setLevel(level_map[level])

    def set_all_loggers_level(self, level: str) -> None:
        """
        Set the logging level for all loggers at once.
        
        Args:
            level: Level name ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
        
        Raises:
            ValueError: If level is invalid
        """
        level_map = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }
        
        if level not in level_map:
            raise ValueError(f"Invalid log level: {level}")
            
        for logger_name, logger in self._loggers.items():
            logger.setLevel(level_map[level])
            # Also update all handlers
            for handler in logger.handlers:
                handler.setLevel(level_map[level])
            print(f"Set {logger_name} to {level}")


# Singleton instance of LoggerWrapper
_logger_wrapper = LoggerWrapper()

def get_logger(
    name: str,
    log_to_file: Optional[str] = None,
    level: int = default_log_level
) -> logging.Logger:
    return _logger_wrapper.get_logger(name, log_to_file, level)

# Add these utility functions
def set_all_loggers_level(level: str) -> None:
    """Set all loggers to the specified level."""
    _logger_wrapper.set_all_loggers_level(level)

def set_debug() -> None:
    """Convenience function to set all loggers to DEBUG level."""
    set_all_loggers_level('DEBUG')

def set_info() -> None:
    """Convenience function to set all loggers to INFO level."""
    set_all_loggers_level('INFO')
