# Framework API Reference

This is a focused reference for `core/` and `bots/core/`. For workflow and rules, see [bot-building.md](./bot-building.md). For debugging, see [debugging.md](./debugging.md).

---

## Entry: `core.bot.Bot`

```python
from core.bot import Bot

class BotExecutor(Bot):
    name: str = "..."
    description: str = "..."
    tier: str = "B"
    instructions: str = """..."""

    def __init__(self, config: BotConfig, user: str = ""):
        super().__init__(user, break_cfg=config.break_cfg)
        self.cfg = config
```

After `super().__init__(...)` you have:

| Attribute | Type | Provides |
|---|---|---|
| `self.client` | `RuneLiteClient` | screenshots, CV, OCR, clicks, hover, chat, minimap |
| `self.control` | `ScriptControl` (singleton) | pause/terminate/break |
| `self.bank` | `BankInterface` | banking primitives |
| `self.mover` | `MovementOrchestrator` | minimap-based pathing |
| `self.itemdb` | `ItemLookup` (singleton) | item db (~43k items) |
| `self.api` | `BotAPI` | Flask `:5432` control endpoints |
| `self.log` | `logging.Logger` | name = `self.name` if set, else `'Bot'` |
| `self.terminate` | property→bool | mirror of `self.control.terminate` |

Side effects of `super().__init__`:
- `ScriptControl().reset()` — clears terminate/pause/break, restarts keyboard listener.
- `cv_debug.enable(port=5555)` if not already running.
- `BotAPI.start(port=5432)`.
- Window discovery + UI sector detection + resize watcher started.

---

## Lifecycle: `core.control.ScriptControl`

Singleton. Constructed for you by `Bot.__init__`.

```python
self.control.terminate          # bool, read/write. PageUp → True.
self.control.pause              # bool. PageDown toggles. 0.4s debounce.
self.control.break_until        # float, time.time() when break ends.
self.control.break_config       # BreakCfgParam | None

self.control.reset()            # clear all flags, restart listener
self.control.initialize_break(seconds)  # schedule a break, non-blocking
self.control.propose_break()    # roll the dice per break_config

@self.control.guard             # decorator: blocks on pause/break, raises on terminate
def my_action(self): ...
```

`@control.guard` raises `core.control.ScriptTerminationException`. Catch this exception in `start()` to log a clean shutdown.

### Idiomatic checkpoints

```python
# At the top of each loop iteration:
self.control.propose_break()
if self.terminate:
    break
```

Or use `@self.control.guard` on inner methods. Mix-and-match per your loop pattern.

---

## Config: `bots.core.cfg_types`

All param types implement `.value`, `.type()`, `.load(...)`, `.from_json(...)`, `.to_json()`.

```python
from bots.core.cfg_types import (
    RGBParam, RangeParam, BreakCfgParam,
    WaypointParam, RouteParam,
    ItemParam, ItemListParam,
    BooleanParam, StringParam, IntParam, FloatParam,
    StringListParam, RGBListParam,
)
```

### RGBParam
```python
RGBParam(r, g, b)              # 0-255 each
RGBParam.from_tuple((r, g, b))
RGBParam.from_hex("#FF0064")
p.r; p.g; p.b; p.value; p.to_hex(); list(p)  # iterable
```

### RangeParam
```python
RangeParam(0.6, 1.2)
p.choose()                     # random.uniform(min, max)
p.value                        # (min, max)
```

### BreakCfgParam
```python
BreakCfgParam(RangeParam(30, 90), 0.02)   # duration_range, chance_per_check
p.should_break() -> bool
p.break_duration: RangeParam
p.break_chance: float
```

### WaypointParam / RouteParam
```python
WaypointParam(x, y, z, chunk, tolerance=5)
RouteParam([wp1, wp2, ...])
p.reverse() -> RouteParam
```

`x/y/z/chunk` come from the RuneLite tile-marker plugin's JSON export (`regionX`, `regionY`, `z`, `regionId`).

### ItemParam
```python
ItemParam("Coal")              # name lookup, case-insensitive
ItemParam(453)                 # id lookup
p.id; p.name; p.stackable; p.equipable
```

⚠️ Constructor **raises `ValueError`** at import time if the item is missing from `ItemLookup`. Don't put speculative item names in defaults.

### ItemListParam
```python
ItemListParam([ItemParam("Coal"), ItemParam("Iron ore")])
p.append(ItemParam("...")); p.remove(idx); iter(p)
```

You can also declare `list[ItemParam]` directly — the UI handles it.

### Scalar / list wrappers
- `BooleanParam(False)` — `bool(p)` works.
- `StringParam("text")`.
- `IntParam(0)` — `int(p)` works.
- `FloatParam(0.0)` — `float(p)` works.
- `StringListParam([...])`, `RGBListParam([...])`.

For very simple params, you can use raw Python types (`bool`, `int`, `float`, `str`, `list[str]`) — the UI infers a matching widget.

### Mixin
`bots.core.config.BotConfigMixin` provides:
- `import_config(dict)`, `export_config() -> dict`
- `import_config_json(str)`, `export_config_json(indent=2) -> str`

Inherit it on your `BotConfig`.

---

## Screen capture & CV: `core.osrs_client.RuneLiteClient`

### Screenshots
```python
client.get_screenshot(maximize=True) -> PIL.Image
client.save_screenshot(filename) -> str | None
client.bring_to_focus()
client.move_off_window(offset=None)   # avoid hover tooltips in next shot
client.get_filtered_screenshot(...)   # UI-stripped (for tile color detection)
```

### Template matching
```python
client.find_in_window(
    img: PIL.Image,
    screenshot: PIL.Image = None,
    min_scale: float = 0.9,
    max_scale: float = 1.1,
    min_confidence: float = 0.7,
    sub_match: MatchResult = None,         # constrain search to region
) -> MatchResult                            # raises if below confidence

client.find_img_in_window(img, sub_match=None, confidence=.95) -> MatchResult
```

### Inventory & items
```python
client.find_item(
    item_identifier: str | int,
    tab: ToolplaneTab = ToolplaneTab.INVENTORY,
    min_confidence: float = 0.97,
    screenshot: PIL.Image = None,
    crop: tuple[int,int,int,int] = None,
) -> MatchResult

client.smart_find_item(
    item_identifier=None, item=None, parent_match=None,
    ignore_count=False, hover_verify=False, hover_verify_retry=3,
    min_confidence=.95, raise_on_missing=False,
) -> MatchResult | None

client.get_item_cnt(identifier, tab=INVENTORY, min_confidence=0.97) -> int
client.get_inv_items(
    items: list[str|int], min_confidence=0.97,
    x_sort=None, y_sort=None,            # None → randomized for anti-pattern
    do_sort=True, verify_tab=True,
) -> list[MatchResult]
client.click_item(identifier, tab=INVENTORY, click_cnt=1, ...)
```

### Tabs / minimap
```python
from core.osrs_client import ToolplaneTab, MinimapElement

client.click_toolplane(ToolplaneTab.INVENTORY)
client.toolplane.get_active_tab(client.get_screenshot()) -> ToolplaneTab

client.click_minimap(MinimapElement.RUN)
client.get_minimap_stat(MinimapElement.HEALTH) -> int     # OCRs the number

# ToolplaneTab: COMBAT SKILLS PROGRESS INVENTORY EQUIPMENT PRAYER SPELLS
#               GROUPS ACCOUNT LOGOUT SETTINGS EMOTES MUSIC
# MinimapElement: HEALTH PRAYER RUN SPEC
```

### Clicks
```python
client.move_to(
    match: MatchResult | tuple[int, int],
    rand_move_chance: float | None = None,    # None uses InteractionRandomness default
    translated: bool = False,                  # True if coords already in screen space
    parent_sectors: list[MatchResult] = [],    # offset chain
)

client.click(
    match: MatchResult | tuple,
    click_cnt: int = 1,
    min_click_interval: float = 0.3,
    click_type: ClickType = ClickType.LEFT,    # LEFT / RIGHT / MIDDLE
    parent_sectors: list = [],
    rand_move_chance: float | None = None,
    after_click_settle_chance: float | None = None,
)
```

### Smart clicks (with hover-text verification)
```python
client.smart_click_tile(
    tile_color: RGBParam | tuple[int,int,int],
    hover_text: str | list[str],     # e.g. ['mine', 'ore', 'vein']
    retry_hover: int = 3,
    retry_match: int = 3,            # widens color tol by 10 per retry
    filter_ui: bool = False,
    filter_out: list[MatchResult] = None,
) -> None                            # raises on exhausted retries

client.smart_click_match(
    match: MatchResult,
    hover_texts: str | list[str],
    retry_hover: int = 3,
    click_cnt: int = 1,
    click_type: ClickType = ClickType.LEFT,
    center_point: bool = False,
    center_point_variance: int = 2,
    parent_sectors: list[MatchResult] = [],
) -> None
```

These are the **default tools** for clicking world objects. Use raw `click` only when you have a reason.

### Hover text
```python
client.get_hover_text() -> str                  # bottom-left RL panel via OCR
client.get_action_hover() -> str                # text under cursor (RL plugin)
client.hover_text                               # property: action_hover or fallback
client.get_hover_texts() -> list[str]           # both, concurrent, 5s timeout
client.compare_hover_match(target: str) -> float   # best similarity across both
```

### Game state
```python
client.is_mining        # property
client.is_fishing
client.is_cooking
client.is_woodcutting
client.makin_cannonballs
client.get_skilling_state(substring: str) -> bool

client.is_moving(sleep_between=0.8, retry_cnt=2) -> bool
client.get_position(retry_cnt=0) -> PlayerPosition   # (tile, chunk, region)

client.quick_prayer_active   # property
```

`PlayerPosition.tile` is `(x, y, z)`. `client.get_position` OCRs the RuneLite player-position overlay (`data/ui/player-position-state.png`) — requires the location overlay plugin enabled.

### Chat
```python
client.get_chat_text() -> str                       # OCR full chat
client.find_chat_text(text: str) -> MatchResult     # locate one line
client.click_chat_text(text: str)                   # click that line
client.is_text_in_chat(text, confidence=0.7) -> bool  # per-line similarity
```

### Right-click menus
```python
client.get_right_click_menu(sc=None) -> MatchResult
client.choose_right_click_opt(option: str)          # OCR-find and click
```

### Sectors (cached UI regions)
```python
client.sectors.toolplane   # MatchResult for the right-side tab pane
client.sectors.chat        # MatchResult for chat box
client.minimap.health      # MatchResult for health orb
client.minimap.prayer      # ...
client.minimap.run
client.minimap.spec
client.minimap.map         # main minimap area
```

These rebuild on window resize automatically.

---

## Banking: `core.bank.BankInterface`

```python
self.bank.is_open                                  # property → bool
self.bank.bank_sc                                  # cropped Image of the bank window

self.bank.deposit_inv()                            # click "deposit inventory"
self.bank.withdraw(item_id: str|int, amount: int = 1)   # amount=-1 → All
self.bank.search(item_name: str) -> bool
self.bank.close() -> bool
self.bank.get_item_count(item_id, min_confidence=0.7, hover_verify=True) -> int

self.bank.set_withdraw_setting(option: str)        # 'Item' | 'Noted'
self.bank.set_rearrange_setting(option: str)       # 'Swap' | 'Insert'
self.bank.set_quantity_setting(option: str)        # '1' | '5' | '10' | 'X' | 'All'
self.bank.set_default_quantity(option: int)        # sets X to N if needed
self.bank.get_settings() -> dict
self.bank.get_bank_tabs() -> list[MatchResult]
```

Anchors live in `data/ui/bank-top-left.png`, `bank-bottom-right.png`, `bank-deposit-inv.png`, `bank-rearrange-swap.png`, `bank-rearrange-insert.png`, and `new_bank.png`. If a specific button anchor goes stale on a future RuneLite update, recapture the anchor PNG — don't reach for manual `find_in_window` workarounds.

---

## Movement: `core.movement.MovementOrchestrator`

```python
self.mover.get_position(verify=False) -> PlayerPosition
self.mover.get_tile_diff(waypoint: WaypointParam) -> tuple[int, int]
self.mover.set_minimap_zoom(zoom_level: int = 2)

self.mover.execute_route(route: RouteParam) -> None
self.mover.go_to_waypoint(tile_value: TileValue) -> bool
self.mover.determine_direction(waypoint) -> MatchResult

self.mover.push_to_clipboard(tiles: list[TileValue])
self.mover.pull_from_clipboard() -> list[TileValue]
self.mover.tile_import(tiles: list[TileValue])
```

The minimap is divided into 8 elliptical sectors (`self.mover.north`, `.south`, `.east`, `.west`, `.north_east`, `.north_west`, `.south_east`, `.south_west`), each a `MatchResult` you can `click`. `go_to_waypoint` clicks these repeatedly (max 15 attempts) using `get_tile_diff` to choose direction.

`TileValue(waypoint, color)` pairs a `WaypointParam` with an `RGBParam` for tile-marker visualization.

To collect a route:
1. In RuneLite, enable tile-marker plugin, mark the tiles, export.
2. Use `RouteParam.load(json_list)` or hardcode the waypoints in your `BotConfig`.

---

## Items: `core.item_db.ItemLookup`

Singleton, loaded from `data/items/items-cache-data.json` + `data/items/icons-items-complete.json`.

```python
self.itemdb.get_item_by_id(item_id: int) -> Item | None
self.itemdb.get_item_by_name(name: str) -> Item | None        # case-insensitive exact
self.itemdb.get_item(any) -> Item | None
self.itemdb.search_items(query: str, limit=50) -> dict[int, Item]
self.itemdb.search_items_advanced(query, filters=None, limit=50) -> list[Item]
self.itemdb.list_all_items() -> dict[int, str]
```

```python
@dataclass
class Item:
    id: int; name: str; icon_b64: str; noted: bool
    stackable: bool; equipable: bool; tradeable_on_ge: bool; members: bool
    cost: int; lowalch: int; highalch: int

    @property
    def icon(self) -> PIL.Image                     # decodes b64
    def get_count(self, item_match: MatchResult, sc: PIL.Image) -> int
```

---

## Geometry: `core.region_match.MatchResult`

```python
m.start_x; m.start_y; m.end_x; m.end_y
m.width; m.height
m.confidence; m.shape   # MatchShape.RECT or MatchShape.ELIPSE

m.get_center() -> (x, y)
m.get_point_within() -> (x, y)        # rejection-sampled random pixel inside
m.contains(x, y) -> bool

m.transform(dx, dy) -> MatchResult    # returns new offset copy
m.scale_px(pixels) -> MatchResult     # grow/shrink
m.crop_in(img: Image) -> Image
m.remove_from(img: Image) -> Image
m.debug_draw(img, color='red') -> Image
m.find_overlap(other) -> MatchResult | None
m.copy() -> MatchResult
```

---

## CV primitives: `core.tools`

```python
from core import tools

tools.find_subimage(parent, template, min_scale=0.9, max_scale=1.1) -> MatchResult
tools.find_subimages(parent, template, min_scale=1, max_scale=1,
                     min_confidence=0.7, max_count=None) -> list[MatchResult]
tools.find_color_box(img, color: RGBParam | tuple, tol=20) -> MatchResult
tools.mask_colors(img, colors: list, tolerance=5) -> Image
tools.mask_above_color_value(img, threshold: int) -> Image      # zero dim pixels
tools.text_similarity(a: str, b: str) -> float                  # difflib ratio
tools.write_text_to_image(img, text, color, font_size) -> Image
tools.seconds_to_hms(seconds: float) -> str

@tools.timeit()
def something(): ...           # logs duration at DEBUG
```

`find_subimage(s)` automatically feeds `cv_debug.enqueue_match` — every CV call shows up in `http://127.0.0.1:5555`.

---

## OCR: `core.ocr`

```python
from core import ocr

ocr.execute(img, font=ocr.FontChoice.RUNESCAPE_PLAIN_12,
            psm=ocr.TessPsm.SPARSE_TEXT, preprocess=True,
            raise_on_blank=True) -> str

ocr.get_number(img, font=ocr.FontChoice.RUNESCAPE_PLAIN_11,
               preprocess=True) -> int

ocr.find_string_bounds(img, text, lang=ocr.FontChoice.RUNESCAPE_BOLD_12.value) -> dict
# returns { x1, y1, x2, y2, confidence }
```

`FontChoice`: `RUNESCAPE_PLAIN_11`, `RUNESCAPE_PLAIN_12`, `RUNESCAPE_BOLD_12`, `AUTO`.
`TessPsm`: `SPARSE_TEXT`, `SINGLE_LINE`, `AUTO`, plus the Tesseract PSM values.

For the player-position overlay, `core.ocr.custom.read_location_numbers(img)` is bespoke and faster than Tesseract.

---

## Logging: `core.logger`

```python
from core.logger import get_logger, set_debug, set_info, set_all_loggers_level

log = get_logger("MyBot", log_to_file=None, level=logging.DEBUG)
log.debug(...); log.info(...); log.warning(...); log.error(..., exc_info=True)

set_debug()                      # all loggers → DEBUG
set_info()
set_all_loggers_level("WARNING")
```

What you get:
- Console with elapsed timestamps (`HH:MM:SS` since process start).
- WebSocket broadcast on `ws://0.0.0.0:18765` (auto-fallback 18766–18769) — this is what the UI log viewer subscribes to.
- Optional `RotatingFileHandler` (5 MB × 3 backups) when `log_to_file` is set.
- Per-logger level can be changed at runtime via WS command.

Inside a `Bot`, `self.log` is created with `name = getattr(self, 'name', 'Bot')`. Set `BotExecutor.name = "Your Bot"` and that's the logger name you filter on in the UI.

---

## CV debugger: `core.cv_debug`

```python
from core import cv_debug

cv_debug.enable(host="127.0.0.1", port=5055)        # Bot.__init__ already calls this @ 5555
cv_debug.disable()
cv_debug.enqueue_match(parent: Image, template: Image | (r,g,b), match: MatchResult)
```

UI at `http://127.0.0.1:5555`. Last 20 matches in a ring buffer. Each entry has the template and annotated parent side by side, plus confidence and bbox. All `find_subimage(s)` calls feed this for free.

---

## Input: `core.input.mouse_control`

You'll generally use `client.click` / `client.move_to` instead. Bare functions if you need them:

```python
from core.input.mouse_control import click, move_to, ClickType, InteractionRandomness

move_to(x, y, rand_move_chance=0.1, ...)
click(x, y, click_type=ClickType.LEFT, click_cnt=1, min_click_interval=0.3)
# Pass (-1, -1) to click at the current cursor position.

# Tune the bot's "humanness" globally:
RuneLiteClient(randomness=InteractionRandomness(
    rand_move_chance=0.05,
    after_click_settle_chance=0.15,
    after_click_settle_sleep=(0.2, 0.6),
))
```

Bezier-curve movement, sub-pixel jitter, randomized speed. All Windows SendInput-based; macOS/Linux backends exist but are less tested.

---

## What you do NOT touch

- `core/window_manager.py` — handled inside `GenericWindow`.
- `core/api.py` (`BotAPI`) — exposes status/screenshot/control to the web UI. Do not extend it from a bot.
- `core/input/key_listener.py` — used by `ScriptControl`. Adding your own `keyboard` hooks will collide.
- `core/osrs_client.py` internals: `_listen_for_control`, `find_matches`, `MinimapContext`, `ToolplaneContext`, `UISectors`. They rebuild themselves on resize.
