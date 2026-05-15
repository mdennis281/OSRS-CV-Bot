# Debugging Playbook

When a bot misbehaves, work through this in order. Don't skip levels.

---

## 0. The two checkpoints that catch 80% of issues

Before anything else:

1. **Is RuneLite focused and not minimized?** `client.bring_to_focus()` runs on every screenshot, but if the window is on a different virtual desktop or behind UAC, captures will be wrong. Move RuneLite to the primary monitor and bring it to front manually.
2. **Did you re-`pip install -r requirements.txt`?** This is the single most common 3am bug. New CV / OCR dependencies land all the time.

---

## 1. Read the log

The UI log stream is at the **Logs** page in `http://localhost:8010`. WebSocket source is `ws://localhost:18765`.

Filter by your bot's logger name (`getattr(self, 'name')` — e.g. `"Dart Fletcher Bot"`).

What to look for:

| Symptom | Likely cause | Fix |
|---|---|---|
| `Item ... not found in window. Confidence: 0.8x` | `min_confidence` too high, or item not in expected tab | Tune `min_confidence` to 0.92–0.95, or pass `tab=` |
| `[SmartClick] cant find match` | Hover text doesn't match verbs | Add more aliases to `hover_text` list, or check verb wording |
| `Match did not meet minimum confidence` from `find_in_window` | Template was captured at different resolution | Recapture template, save to `data/ui/` |
| `OcrError` on chat / minimap | Font not loaded or color filter too tight | Check the `mask_colors` colors; OCR `RUNESCAPE_PLAIN_11` vs `_12` |
| Bot idle, no errors | Stuck in `while is_moving():` or `is_mining` reading stale state | Add timeout to all `while client.is_X` loops |
| Pause/PageUp does nothing | A bare `time.sleep(big_n)` inside a `@control.guard`-less function | Either decorate with `@self.control.guard` or `time.sleep` in 1s chunks checking `self.terminate` |

Crank logging if needed:
```python
from core.logger import set_debug
set_debug()
```

---

## 2. Open the CV debugger

`http://127.0.0.1:5555`

Shows the last 20 template matches. Each card has:
- The template image (what we were looking for).
- The parent image with a green box around the best match.
- Confidence, scale, bbox.

What to look for:
- **Low confidence (< 0.7)**: template is wrong size, wrong resolution, or outdated. Recapture.
- **Right confidence, wrong location**: scan box is too broad. Use `sub_match=client.sectors.toolplane` etc. to restrict.
- **Nothing showing**: your bot isn't calling into `tools.find_subimage(s)` — it might be using a custom matcher. Add `cv_debug.enqueue_match(parent, template, match)` after your custom logic.

---

## 3. Verify state directly

Drop into a REPL or temporary script while the game is in the state you expect:

```python
from core.osrs_client import RuneLiteClient, ToolplaneTab, MinimapElement
c = RuneLiteClient("")

c.get_screenshot().show()           # what does the bot see?
c.toolplane.get_active_tab(c.get_screenshot())
c.get_minimap_stat(MinimapElement.HEALTH)
c.is_mining
c.get_position()
c.get_hover_texts()
c.get_chat_text()
```

Do this **before** changing bot code. The bot is a thin wrapper over `RuneLiteClient`; confirming behavior at the client level isolates whether the bug is in CV or in your loop.

---

## 4. Reproduce with an offline screenshot

The existing test `tests/test_bank_find_battlestaff.py` shows the pattern:

```python
from PIL import Image
from core import tools
from core.item_db import ItemLookup

# Save your "broken" state to disk:
# In your bot, drop in a one-shot:
#   self.client.get_screenshot().save('data/screenshots/<bot>/broken_state.png')

screenshot = Image.open("data/screenshots/<bot>/broken_state.png")
item = ItemLookup().get_item_by_name("Coal")

match = tools.find_subimage(screenshot, item.icon)
print(match.confidence, match.start_x, match.start_y)
match.debug_draw(screenshot).show()
```

Offline reproduction is free; iterate here before re-running the live bot.

---

## 5. Common pathologies and their fixes

### "It clicks the wrong tile / NPC"
- Add hover-text verification: replace `client.click(tile_match)` with `client.smart_click_match(tile_match, ['expected_verb', 'expected_noun'])`.
- Widen tile color tolerance: `smart_click_tile(..., retry_match=3)` — each retry adds `+10` to `tol`.
- Are there multiple marked tiles with the same color? Use a different color per role.

### "It clicks the right thing but nothing happens"
- The action was too fast (animation hasn't started). Bump `action_delay` lower bound by 200ms.
- The click landed on a UI overlay (chat box, prayer orb tooltip). Use `client.get_filtered_screenshot()` for tile detection.
- Window lost focus mid-click. Verify `client.bring_to_focus()` is being called (it is, by `click`).

### "It pauses for 1 second every iteration"
- `@control.guard` checks pause/break every 1s. If you decorated a hot inner function, that's expected. Move the guard outwards.

### "It says terminated but keeps running"
- You have a `try / except Exception:` that's swallowing `ScriptTerminationException`. Either catch it explicitly first, or change to `except ScriptTerminationException: raise` then `except Exception:`.

### "It refuses to start — `ItemParam` ValueError"
- `ItemParam("X")` is evaluated at class-body time. A typo crashes import. Use the item DB browser at `standalone/icon_visualizer.py` (`python standalone/icon_visualizer.py`) to verify item names.

### "Hover text is wrong"
- `client.get_action_hover()` requires the RuneLite action hover plugin enabled. If user has it off, fall back to `client.get_hover_text()` (bottom-left RL panel).
- OCR fails on some font weights — try `compare_hover_match(target)` which scores against both sources.

### "Bot ran for an hour then went silent"
- Almost always a `while ...: continue` with no timeout. Search your code: `grep -n "while.*continue" bots/your_bot.py` — every match needs a `start_time = time.time(); if time.time()-start_time > N: break` exit.

### "Bank looks weird / actions don't register"
- The bank anchors live in `data/ui/bank-top-left.png`, `bank-bottom-right.png`, `bank-deposit-inv.png`, `bank-rearrange-swap.png`, `bank-rearrange-insert.png`, `new_bank.png`. If `self.bank.is_open` flips false when the bank is clearly open, one of those anchors has drifted from the live UI — recapture the offending PNG (cropped tight) and the rest of `BankInterface` keeps working.
- For quantity prompts, the X-quantity tooltip read is OCR-driven; if `set_default_quantity` mis-syncs, check the `_read_x_quantity_hover` log line — Tesseract sometimes returns garbage and the code falls back to the slower right-click path.

### "OCR reads numbers wrong"
- The framework masks specific colors before OCR (yellow = stack < 100k, white = 100k+, green = 10M+). The current code in `get_item_cnt` only handles yellow. If you're banking 100k+ items, OCR will return 0. Open an issue or extend `mask_colors` calls.

---

## 6. Adding instrumentation while debugging

When you can't tell what the bot is "seeing," temporarily save artifacts to disk:

```python
# At the suspect location:
sc = self.client.get_screenshot()
sc.save(f"data/screenshots/{self.name}/debug_{int(time.time())}.png")
self.log.warning(f"Saved debug screenshot at iter {self.iterations}")

# Or annotate a match:
match.debug_draw(sc, color='lime').save(f"data/screenshots/{self.name}/match_{int(time.time())}.png")
```

Remove these before committing. Better: gate them behind `if self.cfg.debug_dump_screens:` and add a `BooleanParam` to the config.

---

## 7. When you need to ask the user for help

Ask **with evidence**. Bad: "the bot doesn't work." Good:

> The smart_click_tile call is finding a tile at (412, 380) with confidence 0.81 but the hover text returns `''`. Can you take a screenshot with your cursor over the same tile and save it to `data/screenshots/<bot>/hover_failing.png`? I want to see what the action-hover plugin is rendering on your machine.

Always include:
- What the bot was trying to do.
- What it actually got (match confidence, hover text, chat text — quote them).
- What screenshot or run output you need from the user.
- Where they should save it.

---

## 8. Useful one-liners

```python
# Force all bots to DEBUG
from core.logger import set_debug; set_debug()

# Visual dump of all minimap sectors
self.mover.debug_minimap_sectors()

# Visual dump of toolplane tab matches
self.client.debug_toolplane()

# Visual dump of minimap orbs
self.client.debug_minimap()

# Manual screenshot from REPL
from core.osrs_client import RuneLiteClient
RuneLiteClient("").save_screenshot("snap.png")
```

---

## 9. Reporting a framework bug (as opposed to a bot bug)

If you've narrowed it to `core/`:
1. Reproduce with a minimal script using `RuneLiteClient` directly.
2. Save the broken state screenshot.
3. File an issue at `https://github.com/mdennis281/OSRS-CV-Bot/issues` with the screenshot, code, and what you expected.
