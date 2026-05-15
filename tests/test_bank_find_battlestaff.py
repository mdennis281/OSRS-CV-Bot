"""
Offline test: find a Battlestaff in the bank using the BankInterface's own
machinery, against data/ui/tmp/full_game_window.png.

We can't actually run hover_verify (no live game), so this exercises the
find-and-rank path inside `smart_find_item` with hover_verify=False, then
visualises:

  - bank_match bounding box on the full screenshot (red)
  - top-N item-icon candidates (cyan boxes)
  - best candidate (lime) with the full-icon bbox after ignore_count restoration

Outputs go to data/ui/tmp/test_bank_find_*.png. Run with:

    .env\\Scripts\\python.exe tests\\test_bank_find_battlestaff.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PIL import Image, ImageDraw, ImageFont

from core import tools
from core.bank import BANK_TL, BANK_BR
from core.item_db import ItemLookup


SCREENSHOT_PATH = ROOT / "data" / "ui" / "tmp" / "full_game_window.png"
OUT_DIR = ROOT / "data" / "ui" / "tmp"
ITEM_NAME = "Battlestaff"
TOP_N = 6
COUNT_PIXELS = 13


def adaptive_count_crop(ico: Image.Image, count_pixels: int = COUNT_PIXELS):
    """Mirror smart_find_item's adaptive ignore_count crop."""
    cp = min(count_pixels, max(0, ico.height - 12))
    if cp > 0:
        return ico.crop((0, cp, ico.width, ico.height)), cp
    return ico, 0


def main() -> int:
    if not SCREENSHOT_PATH.exists():
        print(f"missing screenshot: {SCREENSHOT_PATH}")
        return 1

    screenshot = Image.open(SCREENSHOT_PATH).convert("RGB")
    print(f"screenshot: {SCREENSHOT_PATH.name} {screenshot.size}")

    # 1. Locate the bank window via the same anchors BankInterface.get_match uses.
    tl = tools.find_subimage(screenshot, BANK_TL, min_scale=1, max_scale=1)
    br = tools.find_subimage(screenshot, BANK_BR, min_scale=1, max_scale=1)
    print(f"  TL conf={tl.confidence:.4f}  ({tl.start_x},{tl.start_y})-({tl.end_x},{tl.end_y})")
    print(f"  BR conf={br.confidence:.4f}  ({br.start_x},{br.start_y})-({br.end_x},{br.end_y})")
    assert tl.confidence >= 0.9 and br.confidence >= 0.9, "bank anchors below threshold"

    bank_match = tools.MatchResult(
        start_x=tl.start_x, start_y=tl.start_y,
        end_x=br.end_x,   end_y=br.end_y,
    )
    bank_crop = bank_match.crop_in(screenshot)
    print(f"  bank_match: ({bank_match.start_x},{bank_match.start_y})-"
          f"({bank_match.end_x},{bank_match.end_y}) size={bank_crop.size}")

    # 2. Look up the Battlestaff icon and crop it the way smart_find_item would.
    itemdb = ItemLookup()
    item = itemdb.get_item(ITEM_NAME)
    assert item, f"item {ITEM_NAME!r} not in db"
    full_icon = item.icon
    template, used_cp = adaptive_count_crop(full_icon)
    print(f"  icon: full={full_icon.size}  template={template.size}  cropped {used_cp} top rows")

    # 3. Run the same search smart_find_item runs (hover_verify off).
    candidates = tools.find_subimages(
        parent=bank_crop,
        template=template,
        min_scale=1, max_scale=1,
        min_confidence=0.5,
        max_count=TOP_N,
    )
    print(f"  found {len(candidates)} candidates:")
    for i, m in enumerate(candidates):
        print(f"    #{i}: conf={m.confidence:.3f} (in bank-crop coords) "
              f"({m.start_x},{m.start_y})-({m.end_x},{m.end_y})")

    # 4. Translate candidates to full-screenshot coords (matches what
    #    smart_find_item returns, including the ignore_count Y-restoration).
    translated = []
    for m in candidates:
        m2 = m.transform(bank_match.start_x, bank_match.start_y)
        m2.start_y -= used_cp  # extend up to cover the full icon
        translated.append(m2)

    # 5. Visualise on the full screenshot.
    viz_full = screenshot.copy()
    draw = ImageDraw.Draw(viz_full)
    draw.rectangle(
        (bank_match.start_x, bank_match.start_y, bank_match.end_x, bank_match.end_y),
        outline="red", width=2,
    )
    for i, m in enumerate(translated):
        col = "lime" if i == 0 else "cyan"
        draw.rectangle((m.start_x, m.start_y, m.end_x, m.end_y), outline=col, width=2)
        draw.text((m.start_x, max(0, m.start_y - 12)),
                  f"#{i} {m.confidence:.2f}", fill=col)
    out_full = OUT_DIR / "test_bank_find_full.png"
    viz_full.save(out_full)
    print(f"  saved {out_full}")

    # 6. Visualise on the bank crop (untranslated coords).
    viz_crop = bank_crop.copy()
    cdraw = ImageDraw.Draw(viz_crop)
    for i, m in enumerate(candidates):
        col = "lime" if i == 0 else "cyan"
        # show with full-icon Y range so it's obvious where the staff actually is
        full_bbox = (m.start_x, max(0, m.start_y - used_cp), m.end_x, m.end_y)
        cdraw.rectangle(full_bbox, outline=col, width=1)
        cdraw.text((full_bbox[0], max(0, full_bbox[1] - 10)),
                   f"#{i} {m.confidence:.2f}", fill=col)
    out_crop = OUT_DIR / "test_bank_find_bankcrop.png"
    viz_crop.save(out_crop)
    print(f"  saved {out_crop}")

    # 7. Save the best-candidate cutout for manual eyeballing.
    if translated:
        best = translated[0]
        pad = 4
        cut = screenshot.crop((
            max(0, best.start_x - pad),
            max(0, best.start_y - pad),
            min(screenshot.width, best.end_x + pad),
            min(screenshot.height, best.end_y + pad),
        ))
        cut.resize((cut.width * 8, cut.height * 8), Image.NEAREST).save(
            OUT_DIR / "test_bank_find_best_8x.png"
        )
        print(f"  saved {OUT_DIR / 'test_bank_find_best_8x.png'}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
