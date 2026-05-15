#!/usr/bin/env python3
"""
OSRS Bot Management System – entry point.

Usage:
    python main.py              Serve the production UI (no Node required)
    python main.py --reloader   Run with hot-reload for frontend & backend dev
    python main.py --port 8010  Override the default port
    python main.py --cv-debug   Start the cv_debug Flask server on port 5055
"""

import argparse
import os
import sys
from pathlib import Path

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).parent))


def main() -> int:
    parser = argparse.ArgumentParser(description="OSRS Bot Management System")
    parser.add_argument(
        "--reloader",
        action="store_true",
        help="Run with hot-reload (requires Node.js for frontend dev server)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8010,
        help="Port for the backend server (default: 8010)",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--cv-debug",
        action="store_true",
        help="Start the cv_debug Flask server on port 5055 (powers /api/cv-debug/* proxy)",
    )
    args = parser.parse_args()

    # Propagate to the FastAPI lifespan (also survives uvicorn's reload subprocess fork).
    if args.cv_debug:
        os.environ["AUTO_RS_CV_DEBUG"] = "1"

    from ui_v2.server import run

    return run(host=args.host, port=args.port, reloader=args.reloader)


if __name__ == "__main__":
    sys.exit(main())