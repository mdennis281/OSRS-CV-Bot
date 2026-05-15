# Screenshot Capture Directory

User-captured reference screenshots, organized per bot. These are **not auto-loaded** — they exist for the build conversation (Claude/Copilot/etc. ↔ user) when CV regions need verification.

## Why this exists

CV bots break when reality doesn't match assumptions: a different RuneLite UI version, a custom tile color, a plugin not enabled. Asking the user for a screenshot at the right moment is the single highest-leverage debugging move.

## Layout

```
data/screenshots/
  README.md                        ← this file
  _template/                       ← worked example to copy from
    README.md
    sample_capture.png             ← (placeholder; not a real shot)
    sample_capture.json            ← optional sidecar metadata
  <bot_name>/                      ← one folder per bot
    README.md                      ← what was captured and why
    <descriptive_name>.png         ← the screenshot
    <descriptive_name>.json        ← optional metadata sidecar
```

## When to add a screenshot here

- The bot author asks for one to verify a CV region, anchor, or tile color.
- A debugging session needs a baseline of "what the screen looks like when it works".
- The user wants to attach evidence to a bug report.

## File naming convention

`<bot_name>/<short_descriptor>__<state>.png`

Examples:
- `motherload_miner/bank_open__upstairs.png`
- `cooking/inventory__27_raw_swordfish.png`
- `karambwan/poh_servant_dialog__fetching.png`

Use `__` between descriptor and state. No spaces. Lowercase.

## Sidecar JSON (optional)

```json
{
  "captured_at": "2025-05-11T19:00:00Z",
  "rl_version": "1.10.34",
  "ui_mode": "Resizable - Modern",
  "resolution": "1920x1080",
  "plugins_relevant": ["tile-markers", "action-hover", "ground-markers"],
  "notes": "Bot was failing here — bank deposit-all button didn't register."
}
```

Fill in whatever you know. Anything is better than nothing.

## Gitignore policy

This directory is tracked. Don't commit large videos or hundreds of full-screen PNGs. If you need to capture a long-running session, crop to the relevant region first. Per-bot `_session_NNN/` folders for live-debug sessions can be added to `.gitignore` if they balloon.

## Promotion to permanent assets

If a screenshot becomes load-bearing for the bot (i.e. the bot's `Image.open` references it), **don't load it from `data/screenshots/`**. Move it to:

- `data/ui/` — global UI anchors used by `RuneLiteClient` (rare; coordinate with the framework owner).
- `data/<bot_name>/` — bot-specific templates referenced by exactly one bot.

`data/screenshots/` is for evidence and reference, not runtime loading.
