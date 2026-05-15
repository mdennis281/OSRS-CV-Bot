"""
Server orchestration for the OSRS Bot UI.

Production mode (default):
    Runs a single uvicorn process that serves the FastAPI backend
    AND the pre-built React SPA from ui_v2/frontend/dist/.
    No Node.js required.

Reloader / dev mode (--reloader):
    Spawns two child processes in daemon threads:
      1. uvicorn with --reload for the FastAPI backend
      2. vite dev server for the React frontend with HMR
    Both are killed when the main thread exits (Ctrl-C, SIGTERM, etc.).
"""

import atexit
import os
import signal
import subprocess
import sys
import threading
from pathlib import Path

from core.logger import get_logger

log = get_logger("Server")

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_FRONTEND_DIR = Path(__file__).resolve().parent / "frontend"
_DIST_DIR = _FRONTEND_DIR / "dist"

# Global registry of child processes to kill on exit
_CHILD_PROCS: list["_ManagedProcess"] = []


def _cleanup_all_children():
    """Final safety net: kill all registered child processes."""
    if not _CHILD_PROCS:
        return
    log.info("Cleanup: killing all child processes...")
    for p in _CHILD_PROCS:
        p.kill()


atexit.register(_cleanup_all_children)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _ManagedProcess:
    """Wraps a subprocess so it can be started in a daemon thread and
    forcibly killed from any thread."""

    def __init__(self, label: str, cmd: list[str], cwd: str | Path, env: dict | None = None):
        self.label = label
        self.cmd = cmd
        self.cwd = str(cwd)
        self.env = env
        self._proc: subprocess.Popen | None = None
        self._thread: threading.Thread | None = None
        # Register in global list for atexit cleanup
        _CHILD_PROCS.append(self)

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, name=self.label, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        merged_env = {**os.environ, **(self.env or {})}
        try:
            self._proc = subprocess.Popen(
                self.cmd,
                cwd=self.cwd,
                env=merged_env,
                # On Windows, CREATE_NEW_PROCESS_GROUP lets us kill the tree.
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
            )
            self._proc.wait()
        except Exception as exc:
            log.error(f"[{self.label}] process error: {exc}")

    def kill(self) -> None:
        p = self._proc
        if p is None or p.poll() is not None:
            return
        log.info(f"[{self.label}] killing process (pid={p.pid})")
        try:
            if sys.platform == "win32":
                # taskkill /T kills the entire process tree
                subprocess.call(
                    ["taskkill", "/F", "/T", "/PID", str(p.pid)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            else:
                os.killpg(os.getpgid(p.pid), signal.SIGTERM)
        except Exception:
            try:
                p.kill()
            except Exception:
                pass


def _check_dist_exists() -> bool:
    index = _DIST_DIR / "index.html"
    if not index.exists():
        log.error(
            f"Frontend build not found at {_DIST_DIR}. "
            "Run 'npm run build' inside ui_v2/frontend/ first, "
            "or use --reloader for development mode."
        )
        return False
    return True


# ---------------------------------------------------------------------------
# Production mode
# ---------------------------------------------------------------------------

def _run_production(host: str, port: int) -> int:
    if not _check_dist_exists():
        return 1

    import uvicorn

    log.info(f"Starting production server on http://{host}:{port}")
    print("=" * 58)
    print("  OSRS Bot Management System")
    print("=" * 58)
    print(f"  Web UI:  http://localhost:{port}")
    print(f"  Press Ctrl+C to stop")
    print("=" * 58)

    try:
        uvicorn.run(
            "ui_v2.backend.main:app",
            host=host,
            port=port,
            log_level="warning",
        )
    except (KeyboardInterrupt, SystemExit):
        log.info("Shutting down...")
    
    return 0


# ---------------------------------------------------------------------------
# Reloader / dev mode
# ---------------------------------------------------------------------------

def _run_reloader(host: str, port: int) -> int:
    vite_port = port + 1  # frontend dev server one port above backend

    procs: list[_ManagedProcess] = []

    # 1. Backend: uvicorn with --reload
    backend = _ManagedProcess(
        label="backend",
        cmd=[
            sys.executable, "-m", "uvicorn",
            "ui_v2.backend.main:app",
            "--host", host,
            "--port", str(port),
            "--reload",
            "--reload-dir", str(_PROJECT_ROOT / "ui_v2" / "backend"),
            "--reload-dir", str(_PROJECT_ROOT / "core"),
            "--reload-dir", str(_PROJECT_ROOT / "bots"),
        ],
        cwd=_PROJECT_ROOT,
    )
    procs.append(backend)

    # 2. Frontend: vite dev
    npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
    frontend = _ManagedProcess(
        label="frontend",
        cmd=[npm_cmd, "run", "dev", "--", "--port", str(vite_port)],
        cwd=_FRONTEND_DIR,
        env={"VITE_API_URL": f"http://127.0.0.1:{port}"},
    )
    procs.append(frontend)

    # Graceful shutdown handler
    shutdown_event = threading.Event()
    shutdown_lock = threading.Lock()

    def _shutdown(*_args):
        with shutdown_lock:
            if shutdown_event.is_set():
                return
            shutdown_event.set()
            log.info("Shutting down child processes...")
            for p in procs:
                p.kill()

    # Register signal handlers
    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)
    if sys.platform == "win32":
        signal.signal(signal.SIGBREAK, _shutdown)

    # Start everything
    for p in procs:
        p.start()

    print("=" * 58)
    print("  OSRS Bot Management System  [DEV / RELOADER]")
    print("=" * 58)
    print(f"  Backend API :  http://localhost:{port}")
    print(f"  Frontend UI :  http://localhost:{vite_port}")
    print(f"  Press Ctrl+C to stop")
    print("=" * 58)

    try:
        # Block until shutdown signal or KeyboardInterrupt
        while not shutdown_event.is_set():
            shutdown_event.wait(timeout=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        # Ensure shutdown always runs
        _shutdown()

    return 0


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run(*, host: str, port: int, reloader: bool) -> int:
    if reloader:
        return _run_reloader(host, port)
    return _run_production(host, port)
