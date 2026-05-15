# Screenshot Capture — Template

Copy this folder when starting screenshot collection for a new bot:

```bash
cp -r data/screenshots/_template data/screenshots/<bot_name>
```

Then edit this README to describe what shots are in this folder and why.

## Example contents

```
data/screenshots/cooking/
  README.md                                ← describes what's here
  inventory__27_raw_swordfish.png          ← baseline "ready to cook"
  inventory__27_raw_swordfish.json         ← sidecar
  range_interface__cooking_swordfish.png   ← the cook dialog
  chat__you_burn_one.png                   ← the failure chat line we OCR for
```

## Sidecar JSON template

Save next to each `.png` with the same name, `.json` extension:

```json
{
  "captured_at": "2025-05-11T19:00:00Z",
  "rl_version": "1.10.34",
  "ui_mode": "Resizable - Modern",
  "resolution": "1920x1080",
  "plugins_relevant": ["tile-markers", "action-hover"],
  "notes": "Captured while bot was failing at smart_click_tile — hover text was empty."
}
```

## Capture tips

- Maximize/restore RuneLite to its **default working size** before capturing — variable window sizes will produce templates that don't match other users' setups.
- For UI anchors, crop tightly. A 60×30 bank-button capture template-matches faster and more reliably than a 200×200 capture with surrounding noise.
- For tile color samples, take the screenshot with the cursor **off** the tile so action-hover doesn't render over it. Use `client.move_off_window()` first if scripting the capture.
- For chat OCR baselines, capture the chat box with the exact wording you want to detect. Don't crop the line — the OCR pipeline scans the whole chat region.

## Pixel coordinates

If you need to point a bot author at a specific region in your screenshot, use:

```
(x_start, y_start, x_end, y_end) relative to the screenshot's top-left
```

e.g. *"bank deposit-all button is at (720, 460, 755, 485) in `bank_open.png`"*.

For full-RL-window screenshots, the bot framework's `MatchResult` uses the same convention (`start_x`, `start_y`, `end_x`, `end_y` in window-relative pixels).
