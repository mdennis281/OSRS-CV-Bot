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


# ------------------------------------------------------------------------------
# --- WebSocket‐streaming Log Handler ------------------------------------------
# ------------------------------------------------------------------------------

class WebSocketLogHandler(logging.Handler):
    """
    A logging.Handler that serializes each LogRecord to JSON and pushes it
    to all currently connected WebSocket clients.
    """
    def __init__(self):
        super().__init__()
        # We’ll use our own JSON formatting; no need for a Formatter here.

    def emit(self, record: logging.LogRecord) -> None:
        try:
            # Build a dictionary containing all the context we want:
            payload = {
                "timestamp": self.formatTime(record, datefmt="%Y-%m-%d %H:%M:%S"),
                "logger_name": record.name,
                "level": record.levelname,
                "message": record.getMessage(),
                # Optional: include extra fields if present
                **(record.__dict__.get("extra", {})),  
            }
            text = json.dumps(payload)
        except Exception:
            # If formatting fails, bail silently (we don’t want logging to crash)
            return

        # Schedule sending to clients on the websocket event loop
        if _ws_event_loop and _ws_event_loop.is_running():
            asyncio.run_coroutine_threadsafe(self._broadcast(text), _ws_event_loop)

    async def _broadcast(self, text: str) -> None:
        """
        Asynchronously send `text` to every connected WebSocket client.
        If a send fails, remove that client from the set.
        """
        to_remove = []
        for ws in _ws_clients:
            try:
                await ws.send(text)
            except Exception:
                # If sending fails, mark for removal
                to_remove.append(ws)

        # Clean up any dead connections
        for ws in to_remove:
            _ws_clients.discard(ws)


# ------------------------------------------------------------------------------
# --- Function to start the WebSocket server inside a daemon thread -----------
# ------------------------------------------------------------------------------

def _start_websocket_server(host: str = "localhost", port: int = 8765) -> None:
    """
    This function is intended to run in its own thread. It creates a new
    asyncio loop, starts a simple WebSocket server, and runs forever.
    """
    global _ws_event_loop, _ws_server_started
    with _ws_start_lock:
        if _ws_server_started:
            return  # already running
        _ws_server_started = True

    # Create and set a fresh event loop for this thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    _ws_event_loop = loop

    async def ws_handler(ws: websockets.WebSocketServerProtocol, path: str):
        # When a client connects, add it to our set
        _ws_clients.add(ws)
        try:
            # Keep the connection open until client disconnects
            await ws.wait_closed()
        finally:
            _ws_clients.discard(ws)

    # Start the WebSocket server
    server_coro = websockets.serve(ws_handler, host, port)
    server = loop.run_until_complete(server_coro)

    print(f"[WebSocketLogHandler] Running on ws://{host}:{port}/")

    try:
        loop.run_forever()
    finally:
        # Clean up if the loop ever stops
        server.close()
        loop.run_until_complete(server.wait_closed())
        loop.close()


def _ensure_ws_thread_started():
    """
    Guarantee that the WebSocket server thread is up and running.
    """
    global _ws_server_started
    if not _ws_server_started:
        t = threading.Thread(target=_start_websocket_server, daemon=True)
        t.start()


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

default_log_level = logging.INFO  # Default log level if not specified

class LoggerWrapper:
    def __init__(self):
        self._loggers: dict[str, logging.Logger] = {}
        # Kick off the WebSocket server thread on first use:
        _ensure_ws_thread_started()

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


# Singleton instance of LoggerWrapper
_logger_wrapper = LoggerWrapper()

def get_logger(
    name: str,
    log_to_file: Optional[str] = None,
    level: int = default_log_level
) -> logging.Logger:
    return _logger_wrapper.get_logger(name, log_to_file, level)
