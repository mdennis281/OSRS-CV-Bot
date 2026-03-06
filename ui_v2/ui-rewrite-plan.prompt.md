# ui-v2 — React + FastAPI UI Rewrite Plan

Replacement for the Flask/Jinja2 UI (`ui/`). React frontend with a FastAPI backend.

## Architecture

```
┌─────────────────────────────────────────────┐
│               React SPA (Vite)              │
│  ┌─────────┐ ┌──────────┐ ┌──────────────┐ │
│  │Dashboard│ │BotDetail │ │ ItemDatabase │ │
│  └─────────┘ └──────────┘ └──────────────┘ │
│  ┌──────────┐ ┌──────────────────────────┐  │
│  │RunningBot│ │  LogWindow (floating)    │  │
│  └──────────┘ └──────────────────────────┘  │
└──────────────────┬──────────────────────────┘
                   │ HTTP + WebSocket
┌──────────────────▼──────────────────────────┐
│            FastAPI Backend                   │
│  /api/bots/*    /api/items/*                │
│  /api/cv-debug/* (proxy → :5555)            │
│  /ws/logs        (bridge → core logger WS)  │
│  /api/logging/port                          │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│           Core Services (unchanged)          │
│  core/item_db.py   core/control.py          │
│  core/bot.py       core/api.py (:5432)      │
│  core/cv_debug/    core/logger.py (WS)      │
│  bots/core/cfg_types.py                     │
└─────────────────────────────────────────────┘
```

## Key Decisions

- **FastAPI replaces Flask** for the UI backend (async-native, built-in WebSocket support, Pydantic models)
- **CV debugger proxied** through FastAPI (single origin, no CORS issues, React component replaces iframe)
- **Floating/draggable/resizable log window** persists across all pages (like VS Code floating editor)
- **`ItemListParam` added** to `bots/core/cfg_types.py`; `RouteParam` stays as the waypoint list type
- **All 13 config param types** get proper React form widgets (fixing Route/StringList/RGBList gap in current UI)
- **Same JSON format** for config import/export — full backward compatibility

## Key Differences from ui/

| Feature | Old (ui/) | New (ui-v2/) |
|---------|-----------|--------------|
| Backend | Flask + Jinja2 templates | FastAPI + React SPA |
| Config forms | Server-rendered HTML | React components per type |
| Log viewer | Embedded per-page or standalone | Floating window on all pages |
| CV debugger | iframe to :5555 | Proxied SSE, native React component |
| Route/StringList/RGBList widgets | Broken (no form widget) | Full widget support |
| ItemListParam | Not supported | New config type |
| Type safety | None (raw JS) | TypeScript throughout |

---

## Folder Structure

```
ui-v2/
├── README.md              # Project overview + setup
├── API.md                 # Full API endpoint reference
├── TYPES.md               # Config type system reference
├── backend/
│   ├── __init__.py
│   ├── main.py            # FastAPI app, CORS, lifespan
│   ├── routers/
│   │   ├── bots.py        # /api/bots/* endpoints
│   │   ├── items.py       # /api/items/* endpoints
│   │   ├── logging.py     # /api/logging/* endpoints
│   │   └── cv_debug.py    # /api/cv-debug/* proxy endpoints
│   ├── models/
│   │   ├── bot.py         # Pydantic models for bot metadata, status, config
│   │   ├── item.py        # Pydantic models for item search/detail
│   │   └── config.py      # Pydantic models for each config param type
│   ├── services/
│   │   ├── bot_manager.py # Bot discovery, lifecycle, config persistence
│   │   └── item_service.py # Wraps ItemLookup for API use
│   └── ws/
│       └── log_bridge.py  # WebSocket bridge (FastAPI WS ↔ core logger WS)
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── api/              # API client functions
│       │   ├── bots.ts
│       │   ├── items.ts
│       │   └── client.ts     # Shared fetch wrapper
│       ├── types/            # TypeScript interfaces
│       │   ├── bot.ts
│       │   ├── config.ts     # All 13 param types
│       │   └── item.ts
│       ├── hooks/
│       │   ├── useWebSocketLog.ts
│       │   ├── useBotStatus.ts
│       │   └── useCvDebug.ts
│       ├── components/
│       │   ├── layout/
│       │   │   ├── Sidebar.tsx
│       │   │   ├── Navbar.tsx
│       │   │   └── LogWindow.tsx       # Floating/draggable log
│       │   ├── config/                 # One widget per param type
│       │   │   ├── RGBInput.tsx
│       │   │   ├── RangeInput.tsx
│       │   │   ├── BreakCfgInput.tsx
│       │   │   ├── ItemPicker.tsx
│       │   │   ├── ItemListPicker.tsx  # NEW
│       │   │   ├── RoutePicker.tsx
│       │   │   ├── BooleanInput.tsx
│       │   │   ├── IntInput.tsx
│       │   │   ├── FloatInput.tsx
│       │   │   ├── StringInput.tsx
│       │   │   ├── StringListInput.tsx
│       │   │   ├── RGBListInput.tsx
│       │   │   └── ConfigForm.tsx      # Dynamic form renderer
│       │   ├── items/
│       │   │   ├── ItemSearchBar.tsx
│       │   │   ├── ItemCard.tsx
│       │   │   └── ItemDetailModal.tsx
│       │   ├── bots/
│       │   │   ├── BotCard.tsx
│       │   │   ├── BotStatusBadge.tsx
│       │   │   └── TierBadge.tsx
│       │   └── cv-debug/
│       │       └── CvDebugViewer.tsx   # SSE-powered, no iframe
│       ├── pages/
│       │   ├── Dashboard.tsx
│       │   ├── BotDetail.tsx
│       │   ├── RunningBot.tsx
│       │   ├── ItemDatabase.tsx
│       │   └── LogViewer.tsx           # Full-screen standalone
│       └── styles/
│           └── globals.css
```

---

## Implementation Steps

### Step 1: Add `ItemListParam` to `bots/core/cfg_types.py`

New class following the `RGBListParam` pattern — wraps `List[ItemParam]`, supports `to_json()`/`from_json()`/`load()`, is iterable/indexable. Register in the `TYPES` tuple.

JSON shape:
```json
{ "type": "ItemList", "value": [{ "type": "Item", "value": { "id": ..., "name": ... } }, ...] }
```

### Step 2: Build FastAPI Backend

Port all Flask routes from `ui/main.py` to FastAPI with these routers:

- `routers/bots.py` — all `/api/bots/*` and `/api/bot/{bot_id}/*` endpoints
- `routers/items.py` — `/api/items/search` and `/api/items/{item_id}`
- `routers/logging.py` — `/api/logging/port` + FastAPI WebSocket endpoint at `/ws/logs`
- `routers/cv_debug.py` — proxy endpoints from the bot's CV debug server on port 5555

Serve the built React SPA via `StaticFiles` mount at `/` as a catch-all.

### Step 3: Build React Frontend

- **Router**: React Router with routes `/`, `/bot/:botId`, `/running`, `/items`, `/logs`
- **Layout**: Sidebar (same nav as current) + main content area + floating `LogWindow`
- **LogWindow**: Floating, draggable, resizable panel. Connects via WebSocket to `/ws/logs`. Starts minimized. Click to expand. Maximizable to full screen. Persists across route changes. Level + logger filtering. Preferences in `localStorage`.
- **Dashboard**: Bot cards grid with tier badges, running bot status card, system status
- **BotDetail**: `ConfigForm` dynamically renders one widget per param based on `type`. Save/Reset/Export/Import buttons. Start/Stop controls. Instructions panel.
- **RunningBot**: Status card with runtime polling (2s), pause/resume/stop controls, tabs for CV Debug viewer + dedicated log view. Bot termination detection via WebSocket notifications.
- **ItemDatabase**: Search bar with debounce, filter panel, result grid, detail modal
- **CvDebugViewer**: Native React component using SSE (`EventSource` to `/api/cv-debug/stream`)

### Step 4: Config Form Widgets

Each widget receives `{ name, value, onChange }` props. The `ConfigForm` maps `param.type` to the widget:

| Type | Widget | Renders |
|------|--------|---------|
| `RGB` | `RGBInput` | 3 number inputs + color picker + swatch preview |
| `Range` | `RangeInput` | 2 number inputs (min/max) |
| `BreakCfg` | `BreakCfgInput` | 3 inputs: min duration, max duration, chance |
| `Item` | `ItemPicker` | Display card + "Browse" button → search modal |
| `ItemList` | `ItemListPicker` | List of ItemPicker cards + "Add Item" button |
| `Route` | `RoutePicker` | Sortable waypoint rows + "Add Waypoint" + "Reverse" |
| `Boolean` | `BooleanInput` | Toggle switch |
| `Int` | `IntInput` | Number input (step=1) |
| `Float` | `FloatInput` | Number input (step=0.1) |
| `String` | `StringInput` | Text input |
| `StringList` | `StringListInput` | Tag-style list + "Add" input |
| `RGBList` | `RGBListInput` | List of RGBInput rows + "Add Color" button |

### Step 5: Import/Export Compatibility

The React `gatherConfiguration()` equivalent must produce the **exact same JSON format** as the current system: complex types wrapped in `{ type, value }`, primitives as raw values. The import parser handles both the current export format AND the raw-value fallback. Old `*_config.json` files work in the new UI and vice versa.

### Step 6: WebSocket Log Bridge

FastAPI WebSocket endpoint at `/ws/logs`:
1. On client connect, opens a WebSocket to `ws://127.0.0.1:{logger_port}`
2. Forwards all messages bidirectionally
3. Handles reconnection if the core logger WS isn't up yet
4. React `useWebSocketLog` hook manages connection, subscription, filtering, and message buffering (cap at 1000 entries)

### Step 7: CV Debug Proxy

FastAPI routes in `routers/cv_debug.py`:
- `GET /api/cv-debug/recent` → proxy to `http://localhost:5555/api/recent`
- `GET /api/cv-debug/recent_ids` → proxy to `http://localhost:5555/api/recent_ids`
- `GET /api/cv-debug/items?ids=...` → proxy to `http://localhost:5555/api/items?ids=...`
- `GET /api/cv-debug/stream` → SSE passthrough from `http://localhost:5555/stream`

React `CvDebugViewer` uses `EventSource` on `/api/cv-debug/stream` for real-time matches.

---

## API Endpoint Reference

### Bot Management

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/bots` | GET | List all discovered bots |
| `/api/bot/{bot_id}/status` | GET | Get bot running status |
| `/api/bot/{bot_id}/start` | POST | Start a bot — body: `{ config, username }` |
| `/api/bot/{bot_id}/stop` | POST | Stop the running bot |
| `/api/bot/{bot_id}/control` | POST | Pause/resume/terminate — body: `{ action, value }` |
| `/api/bot/{bot_id}/config` | GET | Get current config |
| `/api/bot/{bot_id}/config` | POST | Save config |
| `/api/bot/{bot_id}/reset` | POST | Reset to defaults |

#### `GET /api/bots` Response
```json
{
  "<bot_id>": {
    "id": "woodcutter",
    "name": "Woodcutter",
    "description": "Chops trees and banks logs",
    "instructions": "Markdown instructions...",
    "tier": "A",
    "file_path": "bots/woodcutter.py",
    "module_name": "bots.woodcutter",
    "config_params": {
      "param_name": {
        "type": "RGB",
        "value": { "rgb": [255, 0, 0], "hex": "#FF0000" },
        "description": "Target tile color"
      }
    },
    "default_config": { "..." : "..." }
  }
}
```

#### `GET /api/bot/{bot_id}/status` Response
```json
{
  "status": "running | paused | terminated | not_running",
  "paused": false,
  "runtime": 3621.5,
  "runtime_formatted": "01:00:21",
  "start_time": 1709301234.0
}
```

#### `POST /api/bot/{bot_id}/start` Request
```json
{
  "config": { "<param_name>": "<value>", "..." : "..." },
  "username": "player_name"
}
```

#### `POST /api/bot/{bot_id}/control` Request
```json
{ "action": "pause | resume | terminate", "value": null }
```

#### `POST /api/bot/{bot_id}/config` Request (Save)
```json
{
  "break_config": { "type": "BreakCfg", "value": { "break_duration": { "type": "Range", "value": [300, 600] }, "break_chance": 0.05 } },
  "target_color": { "type": "RGB", "value": [255, 128, 0] },
  "target_item": { "type": "Item", "value": { "id": 1234, "name": "Lobster", "icon_b64": "..." } },
  "speed_range": { "type": "Range", "value": [1.0, 3.5] },
  "max_attempts": 5,
  "use_spec": true,
  "mode": "aggressive"
}
```

### Item Database

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/items/search` | GET | Search items — params: `q`, `limit`, `tradeable`, `members`, `stackable`, `equipable` |
| `/api/items/{item_id}` | GET | Get item detail |

#### `GET /api/items/search` Response
```json
{
  "success": true,
  "results": [
    {
      "id": 4151,
      "name": "Abyssal whip",
      "tradeable_on_ge": true,
      "members": true,
      "noted": false,
      "noteable": true,
      "stackable": false,
      "equipable": true,
      "cost": 120001,
      "lowalch": 48000,
      "highalch": 72000,
      "icon_b64": "iVBORw0KGgo..."
    }
  ],
  "count": 1
}
```

#### `GET /api/items/{item_id}` Response
```json
{
  "success": true,
  "item": {
    "id": 4151,
    "name": "Abyssal whip",
    "tradeable_on_ge": true,
    "members": true,
    "noted": false,
    "noteable": true,
    "placeholder": false,
    "stackable": false,
    "equipable": true,
    "cost": 120001,
    "lowalch": 48000,
    "highalch": 72000,
    "icon_b64": "iVBORw0KGgo..."
  }
}
```

### Logging

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/logging/port` | GET | Get WebSocket logging port |
| `/ws/logs` | WebSocket | Bridged connection to core logging server |

#### WebSocket `/ws/logs` Protocol

**Client → Server:**

| Command | Payload |
|---------|---------|
| `get_loggers` | `{ "command": "get_loggers" }` |
| `subscribe` | `{ "command": "subscribe", "loggers": ["Bot", "ItemLookup"] }` |
| `set_logger_level` | `{ "command": "set_logger_level", "logger_name": "Bot", "level": "DEBUG" }` |
| `ping` | `{ "command": "ping" }` |

**Server → Client:**

| Type | Shape |
|------|-------|
| `log` | `{ "type": "log", "timestamp": "00:12:34", "logger_name": "Bot", "level": "INFO", "message": "..." }` |
| `loggers_list` | `{ "type": "loggers_list", "loggers": ["Bot", "ItemLookup", ...] }` |
| `notification` | `{ "type": "notification", "message": "Bot terminated", "level": "warning" }` |
| `pong` | `{ "type": "pong", "timestamp": "00:12:34", "active_connections": 3 }` |

### CV Debug (Proxy)

All endpoints proxy to the bot's CV debug server (port 5555). Only available when a bot is running.

Include a toggle to turn the debugging on and off, it should be default off as it has a performance impact. it shouldnt be a heavy refactor to add an endpoint to toggle with the current design.

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/cv-debug/recent` | GET | Recent match items |
| `/api/cv-debug/recent_ids` | GET | IDs of recent items |
| `/api/cv-debug/items?ids=1,2,3` | GET | Fetch items by ID |
| `/api/cv-debug/stream` | GET (SSE) | Real-time match stream |

#### Match Item Shape
```json
{
  "id": 1709301234567,
  "timestamp": "00:12:34",
  "confidence": 0.987,
  "scale": 1.0,
  "bbox": [100, 200, 150, 250],
  "images": {
    "template": "data:image/png;base64,...",
    "parent_annotated": "data:image/png;base64,..."
  }
}
```

### Bot Runtime API (per-bot, port 5432)

Served by `core/api.py` on the bot's API port. React may call these directly for screenshot display.

| Endpoint | Method | Response |
|----------|--------|----------|
| `/api/status` | GET | `{ "running": true, "paused": false, "runtime": 123.4, "bot_name": "ExampleBot" }` |
| `/api/control/terminate` | GET/POST | `{ "terminate": false }` |
| `/api/control/pause` | GET/POST | `{ "pause": false }` |
| `/api/screenshot` | GET | PNG binary |
| `/api/runtime` | GET | `{ "runtime_seconds": 123.4, "formatted": "00:02:03", "started_at": 1709301234.0 }` |

---

## Config Parameter Type System

All bot configuration parameters use typed wrappers defined in `bots/core/cfg_types.py`. The React UI renders a specific widget for each type.

### JSON Envelope Format

Complex types serialize as `{ "type": "<TypeName>", "value": <payload> }`.
Primitives (Boolean, Int, Float, String) serialize as **raw values** in config exports.

### Type Reference

#### RGB
```json
{ "type": "RGB", "value": { "rgb": [255, 128, 0], "hex": "#FF8000" } }
```
```typescript
interface RGBValue { rgb: [number, number, number]; hex: string; }
```

#### Range
```json
{ "type": "Range", "value": [0.3, 0.7] }
```
```typescript
type RangeValue = [number, number]; // [min, max]
```

#### BreakCfg
```json
{
  "type": "BreakCfg",
  "value": {
    "break_duration": { "type": "Range", "value": [300, 600] },
    "break_chance": 0.02
  }
}
```
*Also accepts legacy format `[[300, 600], 0.02]`.*
```typescript
interface BreakCfgValue {
  break_duration: { type: "Range"; value: [number, number] };
  break_chance: number;
}
```

#### Waypoint
```json
{ "type": "Waypoint", "value": { "x": 3200, "y": 3200, "z": 0, "chunk": 12850, "tolerance": 2 } }
```
```typescript
interface WaypointValue { x: number; y: number; z: number; chunk: number; tolerance: number; }
```

#### Route
```json
{
  "type": "Route",
  "value": [
    { "type": "Waypoint", "value": { "x": 3200, "y": 3200, "z": 0, "chunk": 12850, "tolerance": 2 } },
    { "type": "Waypoint", "value": { "x": 3210, "y": 3205, "z": 0, "chunk": 12850, "tolerance": 2 } }
  ]
}
```
```typescript
type RouteValue = { type: "Waypoint"; value: WaypointValue }[];
```

#### Item
```json
{
  "type": "Item",
  "value": {
    "id": 4151, "name": "Abyssal whip", "icon_b64": "iVBORw0KGgo...",
    "stackable": false, "equipable": true, "tradeable_on_ge": true,
    "members": true, "cost": 120001, "highalch": 72000, "lowalch": 48000
  }
}
```
```typescript
interface ItemValue {
  id: number; name: string; icon_b64?: string;
  stackable: boolean; equipable: boolean; tradeable_on_ge: boolean;
  members: boolean; cost: number; highalch: number; lowalch: number;
}
```

#### ItemList *(NEW)*
```json
{
  "type": "ItemList",
  "value": [
    { "type": "Item", "value": { "id": 4151, "name": "Abyssal whip", "..." : "..." } },
    { "type": "Item", "value": { "id": 4153, "name": "Dragon defender", "..." : "..." } }
  ]
}
```
```typescript
type ItemListValue = { type: "Item"; value: ItemValue }[];
```

#### Boolean
Config JSON: `true` (raw) — Full: `{ "type": "Boolean", "value": true }`

#### Int
Config JSON: `5` (raw) — Full: `{ "type": "Int", "value": 5 }`

#### Float
Config JSON: `0.85` (raw) — Full: `{ "type": "Float", "value": 0.85 }`

#### String
Config JSON: `"hello"` (raw) — Full: `{ "type": "String", "value": "hello" }`

#### StringList
```json
{ "type": "StringList", "value": ["oak", "willow", "maple"] }
```
```typescript
type StringListValue = string[];
```

#### RGBList
```json
{
  "type": "RGBList",
  "value": [
    { "type": "RGB", "value": { "rgb": [255, 0, 0], "hex": "#FF0000" } },
    { "type": "RGB", "value": { "rgb": [0, 255, 0], "hex": "#00FF00" } }
  ]
}
```
```typescript
type RGBListValue = { type: "RGB"; value: RGBValue }[];
```

### ConfigForm Widget Map

```typescript
const WIDGET_MAP: Record<string, React.FC<ConfigWidgetProps>> = {
  RGB:        RGBInput,
  Range:      RangeInput,
  BreakCfg:   BreakCfgInput,
  Waypoint:   WaypointInput,
  Route:      RoutePicker,
  Item:       ItemPicker,
  ItemList:   ItemListPicker,
  Boolean:    BooleanInput,
  Int:        IntInput,
  Float:      FloatInput,
  String:     StringInput,
  StringList: StringListInput,
  RGBList:    RGBListInput,
};
```

For raw-value params (no `type` field), infer type: `boolean` → Boolean, `number` with decimal → Float, integer → Int, `string` → String.

---

## Verification Checklist

- [ ] Unit tests: Port `tests/test_items_api.py` and `tests/test_cfg_types.py` to test FastAPI endpoints
- [ ] Config round-trip: Export from old UI → import in new → export again → diff identical
- [ ] Log viewer: Two browsers receive logs in real-time through WS bridge
- [ ] CV debugger: Start bot, match items appear in React CvDebugViewer via SSE
- [ ] All param types: Test bot with every type → configure → save → reload → verify
- [ ] Import old configs: Load every existing `data/configs/*.json` into new UI
- [ ] Route/StringList/RGBList: Verify these now render and save properly (broken in old UI)
