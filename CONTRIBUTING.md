# Contributing

## Prerequisites

| Tool | Required for | Install |
|---|---|---|
| Python >= 3.10 | Everything | [python.org](https://www.python.org/downloads/) |
| Node.js >= 18 | Frontend development only | [nodejs.org](https://nodejs.org/) |

## Setup

```bash
git clone https://github.com/mdennis281/OSRS-CV-Bot.git
cd OSRS-CV-Bot

# Python environment
python -m venv .venv
.venv\Scripts\Activate.ps1          # PowerShell
pip install -r requirements.txt
```

If you plan to modify the frontend:

```bash
cd ui_v2/frontend
npm install
cd ../..
```

## Running in Development

Use the `--reloader` flag to get hot-reload on both backend and frontend:

```bash
python main.py --reloader
```

This starts two processes:

| Process | URL | What it does |
|---|---|---|
| **Backend** (uvicorn) | `http://localhost:8010` | FastAPI API with auto-reload on Python changes |
| **Frontend** (vite) | `http://localhost:8011` | React dev server with HMR |

Open the **frontend** URL (`http://localhost:8011`) during development — it proxies API and WebSocket requests to the backend automatically.

Press `Ctrl+C` to stop both processes.

### Custom ports

```bash
python main.py --reloader --port 9000
# Backend on :9000, frontend on :9001
```

## Project Layout

```
main.py                     Tiny CLI entry point
ui_v2/
  server.py                 Orchestrates production & dev modes
  backend/
    main.py                 FastAPI app (routes, lifespan, SPA serving)
    routers/                API route modules (bots, items, cv_debug, logging)
    services/               Bot manager, item service
    models/                 Pydantic request/response models
    ws/                     WebSocket log bridge
  frontend/
    src/                    React + TypeScript source
      components/           Reusable UI components
      pages/                Route-level page components
      hooks/                Custom React hooks
      api/                  API client functions
      types/                TypeScript type definitions
      styles/               CSS
    dist/                   Pre-built static files (committed to repo)
    package.json            Node dependencies
    vite.config.ts          Vite config (dev proxy, build output)
core/                       Bot framework (client, movement, banking, CV, etc.)
bots/                       Bot implementations
data/                       Item DB, configs, fonts, UI assets
```

## Building the Frontend

After making frontend changes, rebuild the dist so production mode picks them up:

```bash
cd ui_v2/frontend
npm run build
```

This outputs to `ui_v2/frontend/dist/` which is committed to the repo. Users who only run `python main.py` (production mode) get the pre-built version without needing Node.

## Writing a New Bot

1. Create `bots/your_bot.py`
2. Define a `BotConfig` class extending `BotConfigMixin`
3. Define a `BotExecutor` class with a `start()` method
4. The UI auto-discovers it on startup

Key rules:
- **No infinite loops.** Use bounded retries with backoff.
- **Respect `ScriptControl`** for pause/resume/terminate signals.
- **Use framework services** (`MovementOrchestrator`, `BankInterface`, `ItemLookup`, `RuneLiteClient`) — don't duplicate functionality.
- **Log state transitions** and retry reasons.

## Linting

```bash
pip install ruff black
ruff check .
black --check .
```

## Tests

```bash
pip install pytest
pytest -q
```
