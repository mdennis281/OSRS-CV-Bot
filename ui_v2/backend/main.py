"""
FastAPI application – ui-v2 backend.

Serves the API, WebSocket bridge, and (in production mode) the built
React SPA from ui_v2/frontend/dist/.
"""

import atexit
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from core import cv_debug as _cv_debug

from ui_v2.backend.routers import bots, items, logging as logging_router, cv_debug
from ui_v2.backend.ws.log_bridge import router as ws_router
from ui_v2.backend.services.bot_manager import BotManagerService


# ---------------------------------------------------------------------------
# Lifespan – initialise on startup, clean up on shutdown
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start the cv_debug Flask server on port 5055 (gated by --cv-debug on
    # main.py, propagated as AUTO_RS_CV_DEBUG=1) so the /api/cv-debug/*
    # proxy routes have an upstream to talk to. Idempotent.
    if os.environ.get("AUTO_RS_CV_DEBUG") == "1":
        _cv_debug.enable(port=5055)

    mgr = BotManagerService()
    mgr.initialize()

    def _cleanup():
        if mgr.current_bot:
            mgr.stop_bot(mgr.current_bot.bot_id)

    atexit.register(_cleanup)
    yield
    _cleanup()


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="OSRS Bot UI",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers (API + WS)
app.include_router(bots.router)
app.include_router(items.router)
app.include_router(logging_router.router)
app.include_router(cv_debug.router)
app.include_router(ws_router)

# ---------------------------------------------------------------------------
# Static files – serve built React SPA with proper client-side routing
# ---------------------------------------------------------------------------

_frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"

if _frontend_dist.exists():
    # Mount /assets so hashed JS/CSS bundles are served directly
    _assets_dir = _frontend_dist / "assets"
    if _assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(_assets_dir)), name="assets")

    # SPA catch-all: any non-API, non-WS GET returns index.html so
    # React Router can handle client-side routes like /bot/123, /running, etc.
    _index_html = _frontend_dist / "index.html"

    @app.get("/{full_path:path}", include_in_schema=False)
    async def _spa_fallback(request: Request, full_path: str):
        # If it's a real file in dist/ (e.g. favicon, manifest), serve it
        file = _frontend_dist / full_path
        if full_path and file.exists() and file.is_file():
            return FileResponse(str(file))
        # Otherwise serve index.html for client-side routing
        return FileResponse(str(_index_html))
