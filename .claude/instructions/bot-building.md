# Bot Building — Professional Standard

You are building an OSRS computer-vision bot inside this framework. This file is the **operating procedure**. Read it before writing a single line of bot code. The deeper API reference lives in [framework-api.md](./framework-api.md); the debugging procedure lives in [debugging.md](./debugging.md); the prompt for an interactive build session is in [../prompts/new-bot.md](../prompts/new-bot.md).

---

## What "professional" means here

A professional bot in this codebase:

1. **Inherits `Bot`** — never instantiates `RuneLiteClient` directly.
2. **Has a typed `BotConfig`** — every tunable surfaces in the UI.
3. **Honors `ScriptControl`** — PageUp terminates, PageDown pauses, breaks are scheduled, not faked.
4. **Logs state transitions** — `self.log.info("STATE x → y because z")`. A new dev should be able to read the log and tell you what happened.
5. **Has bounded retries** — every `while` has an exit. Every retry has a max count and backoff. No `while True:` without `break`.
6. **Verifies before it clicks** — checks hover text or template matches *before* committing. Cheap to verify; expensive to misclick.
7. **Captures evidence on failure** — saves an annotated screenshot when it bails, so 3am-you can see what the bot saw.
8. **Asks the user for clarification, and asks for screenshots** when CV regions, tile colors, or timing windows are ambiguous. See the [Screenshot Workflow](#screenshot-workflow) section.

If you cut any of these, justify it in writing. Skipping #1 or #3 is a hard no.

---

## Hard rules

These are not negotiable. The framework will not protect you if you break them; bots will silently misbehave instead.

| # | Rule | Why |
|---|------|-----|
| R1 | **No infinite loops without a checkpoint.** Use `@self.control.guard` on inner methods, or check `self.terminate` / `self.control.pause` in your loop body. | A bot ignoring PageUp is a dead bot you can't kill without `Stop-Process`. |
| R2 | **No `print()`.** Use `self.log`. | The web UI streams `self.log`. `print` goes to a terminal nobody is watching. |
| R3 | **No hardcoded item ids, tile colors, sleep ranges, or coordinates** that the user might reasonably want to change. Promote them to `BotConfig`. | Bots are run by other humans. The UI is the contract. |
| R4 | **No `RuneLiteClient('')` outside `Bot.__init__`.** Always go through `Bot`. | You'll get an isolated singleton-confused control plane and no API server. |
| R5 | **No custom `keyboard.add_hotkey('esc', ...)` threads.** | Collides with `ScriptControl`. |
| R6 | **No bare `except Exception:`** that drops the traceback. Log `exc_info=True` or re-raise. | Silent failure is the framework's worst failure mode. |
| R7 | **Every loop body must call `self.control.propose_break()`** at least once if `break_cfg` is configured. | Anti-detection rest is the user's expectation. |
| R8 | **Every bot must declare `name`, `description`, `tier`, `instructions`** as class attributes on `BotExecutor`. | UI discovery uses them. |
| R9 | **`BotConfig` fields must have type annotations.** `field: ItemParam = ItemParam("X")` — the `: ItemParam` part is what the UI reads. | No annotation, no form field, invisible parameter. |
| R10 | **Wrap `start()` body in `try / except ScriptTerminationException`** so PageUp produces a clean log line, not a traceback. | UX. |

---

## Canonical bot skeleton

Copy this. Fill it in. Do not deviate without reason.

```python
# bots/your_bot.py
from bots.core import BotConfigMixin
from bots.core.cfg_types import (
    RangeParam, BreakCfgParam, ItemParam, RGBParam, BooleanParam,
)
from core.bot import Bot
from core.osrs_client import ToolplaneTab
from core.control import ScriptTerminationException

import random
import time


class BotConfig(BotConfigMixin):
    # --- inputs the user picks ---
    target_item: ItemParam = ItemParam("Coal")              # noqa: E501
    target_tile: RGBParam = RGBParam.from_tuple((255, 0, 50))

    # --- timing knobs ---
    action_delay: RangeParam = RangeParam(0.6, 1.2)
    settle_delay: RangeParam = RangeParam(0.2, 0.5)

    # --- safety knobs ---
    max_retries: int = 5
    retry_backoff: RangeParam = RangeParam(1.0, 2.5)

    # --- breaks ---
    break_cfg: BreakCfgParam = BreakCfgParam(
        RangeParam(30, 90),   # break length (seconds)
        0.02,                 # chance per loop iteration
    )


class BotExecutor(Bot):
    name:         str = "Your Bot Name"
    description:  str = "One-sentence summary the UI shows."
    tier:         str = "B"          # S/A/B/C — self-assessed quality
    instructions: str = """
    What the user needs to set up before running:
    - Be at <location>.
    - Have <items> in inventory.
    - Have <tiles> marked with color <X>.
    - This bot does NOT bank. Stops when out of materials.
    """

    def __init__(self, config: BotConfig, user: str = ""):
        super().__init__(user, break_cfg=config.break_cfg)
        self.cfg: BotConfig = config
        self.fail_count = 0
        self.iterations = 0

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        self.log.info(f"Starting {self.name}")
        self.log.debug(f"Config: {self.cfg.export_config()}")

        try:
            self._preflight()
            self._loop()
        except ScriptTerminationException:
            self.log.info("Terminated by user")
        except Exception:
            # Last-ditch: log full traceback. Do NOT swallow.
            self.log.error("Bot crashed", exc_info=True)
            raise
        finally:
            self.log.info(f"Stopped after {self.iterations} iterations")

    # ------------------------------------------------------------------
    # Setup / preflight
    # ------------------------------------------------------------------

    def _preflight(self) -> None:
        """Verify the world is in a state we can work with. Raise if not."""
        count = self.client.get_item_cnt(self.cfg.target_item.id, min_confidence=0.9)
        if count <= 0:
            raise RuntimeError(
                f"Preflight failed: no {self.cfg.target_item.name} in inventory"
            )
        self.log.info(f"Preflight OK — {count}× {self.cfg.target_item.name}")

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def _loop(self) -> None:
        while not self.terminate and self.fail_count < self.cfg.max_retries:
            self.iterations += 1
            self.log.debug(f"Iteration {self.iterations}")

            if self._do_action():
                self.fail_count = 0
            else:
                self.fail_count += 1
                backoff = self.cfg.retry_backoff.choose()
                self.log.warning(
                    f"Action failed ({self.fail_count}/{self.cfg.max_retries}); "
                    f"backing off {backoff:.2f}s"
                )
                time.sleep(backoff)

            self.control.propose_break()

        if self.fail_count >= self.cfg.max_retries:
            self.log.error("Exceeded max retries; stopping")

    def _do_action(self) -> bool:
        """One unit of work. Return True on success, False to retry."""
        try:
            self.client.smart_click_tile(
                self.cfg.target_tile,
                ["mine", "ore"],
                retry_hover=3,
                retry_match=2,
            )
            time.sleep(self.cfg.action_delay.choose())
            return True
        except Exception as e:
            self.log.debug(f"action failed: {e}")
            return False
```

Read [bots/dart_fletcher.py](../../bots/dart_fletcher.py) for the canonical Tier-S example. Read [bots/motherload_miner.py](../../bots/motherload_miner.py) for the canonical state machine example.

---

## Building a new bot — workflow

Treat this as a checklist. **Don't skip steps.** Most bot failures are because somebody guessed at step 2 instead of asking.

### Step 1 — Spec the gameplay

Before writing code, answer these in writing (in the PR description, in a planning doc, or in conversation):

1. What does the player physically do in this skill / activity, second by second?
2. What is the **success signal**? (Inventory fills, animation stops, chat message appears, XP drop, item appears.)
3. What is the **failure signal**? (Wrong tile clicked, "you can't reach that", death, idle timeout.)
4. What is the **reset signal**? (Bank full, out of materials, world hop, runtime over.)
5. What does the player need set up before pressing start? (Items, location, prayers, marked tiles, plugins enabled.)
6. Are there RuneLite plugins this depends on? (Tile markers, action hover, ground markers, player position overlay.)

If you can't answer one of these, **ask the user**. Don't guess.

### Step 2 — Identify CV anchors

For each thing the bot needs to see:

| Thing | How you'll detect it | Confidence to demand | Fallback |
|---|---|---|---|
| Inventory item | `client.find_item(id, min_confidence=0.97)` | 0.95–0.99 | hover-verify if 0.92+ |
| World tile | `client.smart_click_tile(color, [verbs])` | tol=40 with widen on retry | another marked color |
| UI button | `client.find_in_window(template_png, min_scale=1, max_scale=1)` | 0.9+ | OCR text via `find_chat_text` |
| Player state | `client.is_mining` etc. | — | timing window |
| Chat line | `client.is_text_in_chat("...", confidence=0.7)` | 0.7 | poll inventory delta |

If you're not sure what a region looks like or what color the user has marked, **ask for a screenshot**. See the [Screenshot Workflow](#screenshot-workflow).

### Step 3 — Choose a loop pattern

| Pattern | When to use | Examples |
|---|---|---|
| **Counted loop** | Known iterations (e.g. 28 alchs, N darts). | `high_alch.py`, `dart_fletcher.py` |
| **Drain-until-empty** | Stop when materials gone. | `dart_fletcher.py` |
| **State machine** | Multiple locations / phases (mine ↔ bank). | `motherload_miner.py`, `nmz.py` |
| **Event-driven** | React to chat or animation. | `mining.py` (legacy reference) |

A counted loop is the simplest thing that works. Don't reach for a state machine until you have at least two distinct phases.

### Step 4 — Wire the config

Every magic number goes into `BotConfig` with an annotation and a default. Three categories:

- **Inputs** (`ItemParam`, `RGBParam`, `WaypointParam`) — what the user picks.
- **Timing** (`RangeParam`) — every `time.sleep` should source from a `RangeParam.choose()` if the user might want to tune it.
- **Safety** (`int` retries, `BreakCfgParam`) — caps on bad behavior.

### Step 5 — Instrument first, optimize never

Before you flip the bot on:

```python
self.log.info(f"STATE {old} → {new}")     # at every state change
self.log.debug(f"hover: {self.client.get_hover_texts()}")  # at every smart_click attempt
self.log.warning(f"retry {n}/{max} — {reason}")  # at every retry
self.log.error("aborting", exc_info=True)  # at every bail
```

Run it once. Read the log. The story should be readable.

### Step 6 — Test against the live game

There is no integration test harness for live game behavior. Test plan:

1. Run with `set_debug()` so all loggers go to DEBUG.
2. Watch the web UI log stream during the first run.
3. Open `http://127.0.0.1:5555` for the CV debug grid — visually verify match confidence on each template.
4. Run for **10 iterations** before walking away. Most bugs surface in the first 3.
5. PageDown to pause, walk through inventory manually, PageDown to resume — verify the bot recovers.

---

## Screenshot Workflow

CV is the hard part. The user's RuneLite plugins, screen resolution, and what's marked on their tiles all matter. When you don't know, ask — and ask for a screenshot.

### When to request a screenshot

- You need to confirm what a UI element looks like (bank, deposit box, minigame interface).
- You need to know the exact pixel color the user has marked a tile with.
- You need to verify a region's position on screen.
- The user is reporting a bug and the symptom is visual.
- You're choosing between two template images and don't know which RL version they're on.

### How to request a screenshot

Be specific. Bad: "send a screenshot." Good:

> Can you take a screenshot of the bank interface with the search box open, and save it to `data/screenshots/<bot_name>/bank_search_open.png`? I need to confirm the search box anchor coordinates against what's in `data/ui/bank-search.png`.

The directory layout for screenshots (see `data/screenshots/_template/` for a worked example):

```
data/screenshots/<bot_name>/
  README.md           # what you're capturing and why (one paragraph)
  bank_open.png       # the screenshot
  bank_open.json      # optional sidecar: { "notes": "...", "rl_version": "1.10.x" }
  ...
```

The sidecar JSON is optional but useful: record RuneLite version, what plugins were on, what the user was doing.

### When the user sends a screenshot

1. Read it with `Read` (this tool supports PNG/JPG).
2. Identify the regions you care about. Use pixel coordinates relative to the screenshot, then explain them to the user (e.g. "the bank deposit button is roughly at (720, 460) here").
3. If you're going to use it as a template, save the cropped template image to `data/ui/` (anchor) or `data/<bot_name>/` (bot-specific).
4. Update the bot to reference the new template by path.

### Timing questions

You also need to ask the user about timing windows that aren't visible in a screenshot:

- "How long does the crafting animation take on your machine?"
- "Does the action complete before or after the chat message appears?"
- "Roughly how often does the wrong-tile false-positive happen?"

Convert their answers into `RangeParam` config fields with conservative defaults (lower bound of "fast", upper bound of 1.5× their "slow" estimate).

---

## What to call when (decision tree)

### "I need to click something in the world"

- It has a colored tile marker → `client.smart_click_tile(color, [verbs])`.
- It has a known sprite/template → `client.find_in_window(template_img)` then `client.click(match)`.
- It's an NPC with a known name → `client.smart_click_tile(npc_color, [npc_name, action_verb])`, marker first.

### "I need to click something in inventory"

- Known item, one of it → `client.click_item(id_or_name)`.
- Want to verify it's the right item first → `client.find_item(...)` then `smart_click_match(match, [verb])`.
- Multiple of the same item → `client.get_inv_items([name])` returns list, then click each.
- Need to count stack size → `client.get_item_cnt(id)`.

### "I need to walk somewhere"

- Short hop, known direction → click a minimap sector directly: `self.mover.north`, `.east`, etc. — they are `MatchResult`s.
- Defined route → `RouteParam` of `WaypointParam`s, `self.mover.execute_route(route)`.
- Single waypoint → `self.mover.go_to_waypoint(TileValue(wp, color))`.

### "I need to bank"

- Already at bank booth, want to open → click banker tile / chest with `smart_click_tile`.
- Once open → `self.bank.is_open`, `self.bank.search(item_name)`, `self.bank.withdraw(id, amount)`, `self.bank.deposit_inv()`, `self.bank.close()`.

### "I need to wait until X"

- Animation done → `while self.client.is_mining: time.sleep(...)` (or `is_fishing` etc.) — bounded by a max wait.
- Stopped moving → `while self.client.is_moving(): time.sleep(0.1)` — bounded.
- Chat message → poll `client.is_text_in_chat("text")` with a deadline.
- Item count changed → snapshot `get_item_cnt`, poll until different.

Never `while True: time.sleep(...)` without a deadline.

### "I need a humanized delay"

- `RangeParam.choose()` — uniform.
- `random.normalvariate(mean, sigma)` — for "usually fast, occasionally slow".
- `random.random() < p` — for probabilistic side effects (re-aim, camera jiggle).

Don't mix these inline. Promote the parameters to `BotConfig` so users can tune them.

---

## Common pitfalls — observed in real bots

- **Forgetting `verify_tab=True` defaults.** `client.get_inv_items` switches to the inventory tab for you. `get_item_cnt` does too. `find_item` does too. If you've manually switched tabs, pass `verify_tab=False` to avoid the round-trip.
- **`min_confidence` too high.** OSRS sprites compress poorly. 0.97 works for `find_item`; 0.7 is the floor for OCR similarity in chat. Use the CV debug UI (port 5555) to tune.
- **Color tolerance too tight in `smart_click_tile`.** Default `tol=40` is intentional. Tiles look different under different lighting/cape effects. The function widens automatically on retry, but only if you give it `retry_match >= 2`.
- **Calling `bring_to_focus()` in a loop.** Window focus is asserted in `click`, `move_to`, and `get_screenshot` for you. Don't double-call — Alt+Tab fights will lock up the system.
- **Reading hover text before the cursor has moved.** Sleep 100–250ms between `move_to` and `get_hover_texts`. Mouse rendering and tooltip rendering are async.
- **Storing screenshots inline in the bot.** Use the `cv_debug` ring buffer (`enqueue_match`) for ephemeral evidence; only save to disk if it's an asset the bot needs at startup.

---

## When you're unsure — ask

The user has signed up for a build conversation. They expect to answer questions. The wrong move is to guess at:

- **Item names vs item IDs** (noted vs unnoted, members vs F2P variants).
- **Tile colors** the user has marked. The convention varies per user.
- **What plugins are enabled** in their RuneLite (this directly affects what overlays we can match).
- **What the failure mode looks like** — let them describe the chat message, the animation, the icon flash.
- **Timing windows** — animations vary by game tick / device / lag.

Prefix questions with a one-line summary so they can answer fast:

> **CV question — what color is your bank booth tile?** I see RGB(255,0,50) in your motherload_miner config but the new bot needs its own marker so we don't collide.

> **Timing question — how long does one karambwan cook?** I'll set `RangeParam(low, high)` with low = your fastest and high = 1.5× your slowest.

> **Screenshot needed — bank with custom quantity prompt open.** Save to `data/screenshots/<bot_name>/bank_x_prompt.png`. I'll measure the OK button offset.
