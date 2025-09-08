import threading
import time
import json
import base64
import io
from typing import Optional, Dict, Any, Tuple
from collections import deque
from queue import Queue, Full, Empty

from PIL import Image

from core.region_match import MatchResult

# Runtime state
_enabled = False
_started = False
_lock = threading.Lock()

# Ring buffer of last N items
_MAX_ITEMS = 20
_items: deque[Dict[str, Any]] = deque(maxlen=_MAX_ITEMS)

# Task queue for the worker thread (drop if full to avoid slowing main)
_tasks: Queue[Tuple[Image.Image, Image.Image, MatchResult]] = Queue(maxsize=200)

# SSE publisher for connected clients
class _Publisher:
    def __init__(self):
        self._clients: set[Queue[str]] = set()
        self._lock = threading.Lock()

    def register(self) -> Queue[str]:
        q: Queue[str] = Queue()
        with self._lock:
            self._clients.add(q)
        return q

    def unregister(self, q: Queue[str]) -> None:
        with self._lock:
            self._clients.discard(q)

    def publish(self, payload: Dict[str, Any]) -> None:
        data = json.dumps(payload)
        with self._lock:
            clients = list(self._clients)
        for q in clients:
            try:
                q.put_nowait(data)
            except Full:
                # If a client is slow, skip to keep system responsive
                pass

_publisher = _Publisher()

def _b64_png(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")

def _fmt_ts(secs: float) -> str:
    total = int(secs)
    h, r = divmod(total, 3600)
    m, s = divmod(r, 60)
    return f"{h:02}:{m:02}:{s:02}"

def _worker_loop():
    start_t = time.time()
    while True:
        try:
            parent, template, match = _tasks.get()
        except Exception:
            continue

        if parent is None and template is None and match is None:
            # Shutdown signal
            break

        try:
            # Render debug draw on a copy to avoid mutating originals
            annotated = parent.copy()
            try:
                match.debug_draw(annotated, color="lime")
            except Exception:
                # Fallback: simply draw a rectangle if needed (best effort)
                from PIL import ImageDraw
                d = ImageDraw.Draw(annotated)
                sx, sy, ex, ey = match.bounding_box
                d.rectangle([sx, sy, ex, ey], outline="lime", width=2)

            # Encode images
            tpl_b64 = _b64_png(template)
            ann_b64 = _b64_png(annotated)

            item = {
                "id": int(time.time() * 1000),
                "timestamp": _fmt_ts(time.time() - start_t),
                "confidence": round(float(match.confidence), 6),
                "scale": float(getattr(match, "scale", 1.0)),
                "bbox": list(match.bounding_box),
                "images": {
                    "template": tpl_b64,
                    "parent_annotated": ann_b64,
                },
            }

            with _lock:
                _items.appendleft(item)

            _publisher.publish({"type": "match", "item": item})
        except Exception:
            # Swallow worker errors to avoid killing the loop
            continue

# Flask app (import lazily to keep overhead off until enabled)
_app = None
_app_thread: Optional[threading.Thread] = None
_worker_thread: Optional[threading.Thread] = None

def _create_app():
    from flask import Flask, jsonify, Response

    app = Flask(__name__)

    @app.get("/")
    def index():
        # Minimal HTML with SSE auto-update and initial fetch
        return f"""
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>CV Debug - Last {_MAX_ITEMS} Matches</title>
<style>
  body {{ font-family: sans-serif; margin: 0; padding: 0; background: #111; color: #eee; }}
  header {{ padding: 12px 16px; background: #222; position: sticky; top: 0; z-index: 10; }}
  .wrap {{ padding: 12px 16px; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fill,minmax(520px,1fr)); gap: 16px; }}
  .card {{ background: #1a1a1a; border: 1px solid #333; border-radius: 8px; overflow: hidden; }}
  .meta {{ font-size: 12px; color: #aaa; padding: 8px 12px; border-bottom: 1px solid #333; display: flex; gap: 12px; }}
  .imgs {{ display: grid; grid-template-columns: 1fr 1fr; gap: 0; }}
  .imgs > div {{ border-right: 1px solid #222; background: #000; }}
  .imgs > div:last-child {{ border-right: none; }}
  img {{ display: block; width: 100%; height: auto; image-rendering: pixelated; }}
  .tag {{ padding: 0 6px; border-radius: 4px; background: #333; color: #ddd; }}
</style>
</head>
<body>
<header>
  <strong>CV Debug</strong> – showing most recent {_MAX_ITEMS} matches (auto-updating)
</header>
<div class="wrap">
  <div id="grid" class="grid"></div>
</div>
<script>
const grid = document.getElementById('grid');
let items = [];

function render() {{
  grid.innerHTML = items.map(it => `
    <div class="card">
      <div class="meta">
        <span class="tag">t=${{it.timestamp}}</span>
        <span class="tag">conf=${{it.confidence}}</span>
        <span class="tag">scale=${{it.scale}}</span>
        <span class="tag">bbox=[${{it.bbox.join(', ')}}]</span>
      </div>
      <div class="imgs">
        <div><img src="${{it.images.template}}" alt="template"></div>
        <div><img src="${{it.images.parent_annotated}}" alt="annotated parent"></div>
      </div>
    </div>
  `).join('');
}}

fetch('/api/recent').then(r => r.json()).then(d => {{
  items = d.items || [];
  render();
}});

const es = new EventSource('/stream');
es.onmessage = (ev) => {{
  try {{
    const data = JSON.parse(ev.data);
    if (data.type === 'match' && data.item) {{
      items.unshift(data.item);
      items = items.slice(0, { _MAX_ITEMS });
      render();
    }}
  }} catch(e) {{}}
}};
es.onerror = () => {{
  // SSE will retry automatically; nothing to do
}};
</script>
</body>
</html>
        """

    @app.get("/api/recent")
    def api_recent():
        with _lock:
            return jsonify({"items": list(_items)})

    @app.get("/stream")
    def stream():
        q = _publisher.register()

        def gen():
            # Initial keepalive comment
            yield ": connected\n\n"
            try:
                while True:
                    try:
                        msg = q.get(timeout=15)
                        yield f"data: {msg}\n\n"
                    except Empty:
                        # heartbeat
                        yield ": keepalive\n\n"
            finally:
                _publisher.unregister(q)

        return Response(gen(), mimetype="text/event-stream")

    return app

def enable(host: str = "127.0.0.1", port: int = 5055) -> None:
    """
    Enable the CV debug server and worker thread.
    Open http://{host}:{port} to view the UI.
    """
    global _enabled, _started, _app, _app_thread, _worker_thread
    with _lock:
        if _started:
            _enabled = True
            return
        _enabled = True
        _started = True

    # Start worker thread
    _worker_thread = threading.Thread(target=_worker_loop, name="cvdebug-worker", daemon=True)
    _worker_thread.start()

    # Lazy import Flask and start server thread
    def _run_app():
        global _app
        _app = _create_app()
        # Run without reloader; threaded to handle SSE + API
        _app.run(host=host, port=port, debug=False, use_reloader=False, threaded=True)

    _app_thread = threading.Thread(target=_run_app, name="cvdebug-http", daemon=True)
    _app_thread.start()

def enqueue_match(parent: Image.Image, template: Image.Image, match: MatchResult) -> None:
    """
    Non-blocking enqueue. No-ops if not enabled.
    Copies are done inside to avoid main-thread cost if disabled.
    """
    if not _enabled:
        return
    try:
        # Cheap shallow copies to decouple from caller
        p = parent.copy()
        t = template.copy()
        m = match.copy() if hasattr(match, "copy") else match
        _tasks.put_nowait((p, t, m))
    except Full:
        # Drop silently to avoid slowing the main path
        pass

def disable() -> None:
    """Optional: stop accepting new items; existing threads remain daemonized."""
    global _enabled
    _enabled = False
