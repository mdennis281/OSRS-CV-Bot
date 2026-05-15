# Copilot / Claude Onboarding

Short pointer file. The actual instructions live alongside this one.

## What this repo is

`auto_rs` is an OSRS (Old School RuneScape) computer-vision bot framework. Python 3.10+ on Windows. RuneLite client wrapper + CV/OCR + a web UI (FastAPI + React, served on `:8010`). Bots live in `bots/` and inherit `core.bot.Bot`.

## Start here when building or modifying a bot

1. **[instructions/bot-building.md](./instructions/bot-building.md)** — operating procedure: the 10 hard rules, the canonical skeleton, the workflow, when to ask the user for screenshots.
2. **[instructions/framework-api.md](./instructions/framework-api.md)** — full API reference for `core/` (client, control, bank, movement, items, CV, OCR, logging) and `bots/core/` (config types).
3. **[instructions/debugging.md](./instructions/debugging.md)** — what to do when a bot misbehaves. Read order: logs → CV debug at `:5555` → REPL → offline reproduction.
4. **[prompts/new-bot.md](./prompts/new-bot.md)** — use this prompt to open a fresh bot-building conversation. Encodes the question discipline and screenshot workflow.

## Quick start

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
# → web UI on http://localhost:8010
# → CV debug on http://127.0.0.1:5555
# → log WS on ws://localhost:18765
# → bot API on http://localhost:5432
```

## Existing reference bots

- **Tier-S template (simplest):** [bots/dart_fletcher.py](../bots/dart_fletcher.py)
- **State machine template:** [bots/motherload_miner.py](../bots/motherload_miner.py)
- **Counted loop:** [bots/high_alch.py](../bots/high_alch.py)
- **Minigame:** [bots/master_mixer.py](../bots/master_mixer.py)
- **Bank-heavy:** [bots/cooking.py](../bots/cooking.py)

## The 10 hard rules (TL;DR — see `bot-building.md` for the long version)

1. Inherit `Bot`. Never instantiate `RuneLiteClient` directly.
2. Use `self.log`. Never `print()`.
3. Promote all magic numbers to `BotConfig` fields with type annotations.
4. Honor `ScriptControl` — `@self.control.guard` on actions; catch `ScriptTerminationException` in `start()`.
5. No custom `keyboard.add_hotkey('esc', ...)` threads. `ScriptControl` owns PageUp/PageDown.
6. No bare `except Exception:` that drops tracebacks. Use `exc_info=True`.
7. Every loop calls `self.control.propose_break()` at least once per iteration.
8. Declare `name`, `description`, `tier`, `instructions` class attributes on `BotExecutor`.
9. Type-annotate every `BotConfig` field. No annotation → no UI form field.
10. Wrap `start()` in `try / except ScriptTerminationException`.

## When in doubt, ask the user

This codebase explicitly endorses asking the user for **screenshots** and **timing answers** during a bot build. Use the directory `data/screenshots/<bot_name>/` and the protocol described in [bot-building.md](./instructions/bot-building.md#screenshot-workflow). Don't guess CV regions, tile colors, or plugin assumptions.

## Legacy code

Scripts at the repo root (`agility.py`, `mining.py`, etc.) are **legacy** — they predate the `Bot` framework. Don't copy their structure for new bots. They are useful as references for clever CV/OCR techniques only. See [.tmp_investigation/03_legacy_and_standalone.md](../.tmp_investigation/03_legacy_and_standalone.md) if it's still on disk, otherwise read the legacy files individually.

## Hotkeys (runtime)

- **Page Up** — terminate the bot
- **Page Down** — pause / resume

## CI / lint

```bash
pip install ruff black pytest
ruff check .
black --check .
pytest -q
```

There is no integration test harness for live game behavior. Test bots manually for 10+ iterations before declaring done.
