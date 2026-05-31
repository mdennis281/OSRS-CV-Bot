# Old-school RuneScape Computer Vision Bot

A vibe-coding experiment that has grown into a pretty impressive botting framework.

I wouldn't recommend using this if you aren't willing to get your hands dirty writing some Python.

**Windows only.** macOS / Linux backends exist in `core/input/` but aren't actively tested.

### Recent

- **Bank interface rewritten** for the Jagex bank redesign — bank-heavy bots work again.
- **Item database refreshed** including sailing items. Shoutout to [DayV-git/osrsreboxed-db](https://github.com/DayV-git/osrsreboxed-db/tree/master).
- **New web UI (`ui_v2`)** — React + FastAPI, served by a single Python process. No Node.js needed to run it.

## Quick Start

**Prerequisites (Windows):**

| What | Why | Where |
|---|---|---|
| Python >= 3.10 | Runs everything | [python.org](https://www.python.org/downloads/) |
| RuneLite | The game client the bots see and click | [runelite.net](https://runelite.net/) |
| Tesseract OCR | Reads chat, item counts, hover text | [UB Mannheim installer](https://github.com/UB-Mannheim/tesseract/wiki) — install to the default `C:\Program Files\Tesseract-OCR\` |

You do **not** need Node.js. The frontend is pre-built and committed to the repo; the Python server serves it directly.

```powershell
git clone https://github.com/mdennis281/OSRS-CV-Bot.git
cd OSRS-CV-Bot

python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

python main.py
```

Open **http://localhost:8010**, pick a bot, configure, run. Use **Page Up** to terminate and **Page Down** to pause/resume any running bot.

### CLI Options

| Flag | Description |
|---|---|
| `--port PORT` | Override the server port (default: 8010) |
| `--host HOST` | Bind address (default: 0.0.0.0) |
| `--cv-debug` | Also start the CV debug server on port 5055 (powers the in-UI CV debug viewer) |
| `--reloader` | Dev mode with hot-reload — requires Node.js, see [CONTRIBUTING.md](CONTRIBUTING.md) |

## Demos

### Item Combiner - [item_combiner.py](./bots/item_combiner.py)

https://github.com/user-attachments/assets/8d7b6eb6-8b16-466c-b32c-9fde9a23fa37

### Rooftop Agility - [agility.py](./bots/agility.py)

https://github.com/user-attachments/assets/226daf47-361a-433d-89e3-dad1afb1c87a

### Web UI

![Available Bots](./data/demos/available-bots.png)
![Config UI](./data/demos/config.png)
![Item Database](./data/demos/item-database.png)

### Computer Vision Debugger

![CV Debug](https://github.com/user-attachments/assets/c22cecd6-4a13-41e0-af44-196d6348a6df)

## Running Bots Directly

For bots with complex params (e.g. item lists), you can bypass the UI:

```python
from bots.master_mixer import BotConfig, BotExecutor

config = BotConfig()
bot = BotExecutor(config)
bot.start()
```

## Project Structure

```
main.py                 Entry point
core/                   Framework & services (client, movement, banking, etc.)
bots/                   Bot implementations
ui_v2/
  server.py             Server orchestration (production & dev modes)
  backend/              FastAPI API, WebSocket bridge, services
  frontend/             React + TypeScript SPA (Vite)
    dist/               Pre-built static files (committed)
    src/                Source (only needed for frontend development)
data/                   Item databases, configs, fonts, UI assets
```

### Bot Hotkeys

- **Page Up**: Terminate the bot immediately
- **Page Down**: Pause/Resume the bot

## Writing Your Own Bot

Every bot in [bots/](bots/) inherits [`core.bot.Bot`](core/bot.py), which gives you `self.client` (CV + clicks), `self.control` (pause/terminate/breaks), `self.bank`, `self.mover`, `self.itemdb`, and `self.log` — all wired up. A `BotConfig` class with typed fields (`ItemParam`, `RangeParam`, `RGBParam`, `BreakCfgParam`, etc.) drives the auto-generated UI form, so every tunable surfaces in the web UI for free.

Copy one of these as a starting point — they cover most loop patterns you'll need:

| Bot | Pattern | Good for |
|---|---|---|
| [dart_fletcher.py](./bots/dart_fletcher.py) | Drain-until-empty | Simple inventory-driven loops |
| [high_alch.py](./bots/high_alch.py) | Counted loop | Fixed iteration count |
| [motherload_miner.py](./bots/motherload_miner.py) | State machine | Multi-phase (mine ↔ bank) bots |
| [master_mixer.py](./bots/master_mixer.py) | Minigame | Reactive event handling |
| [cooking.py](./bots/cooking.py) | Bank-heavy | Withdraw → use → deposit cycles |
| [nmz.py](./bots/nmz.py) | Long idle | Prayer-flick + absorption sips |

Legacy scripts at the repo root (`agility.py`, `mining.py`, etc.) predate the `Bot` framework — they're kept around for clever CV/OCR tricks but don't copy their structure for new bots.

The full operating procedure (hard rules, screenshot workflow, debugging playbook) lives under [.claude/instructions/](.claude/instructions/) and is also mirrored to [.github/](.github/) so Copilot/Cursor pick it up.
