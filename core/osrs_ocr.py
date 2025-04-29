import base64, io, cv2, numpy as np
from pathlib import Path
from typing import List, Dict
from PIL import Image
from pathlib import Path
from functools import lru_cache
from typing import Dict, Iterable, Optional
from enum import Enum

import numpy as np
from PIL import Image, ImageDraw, ImageFont, UnidentifiedImageError

class FontChoice(Enum):
    RUNESCAPE = "runescape"
    RUNESCAPE_BOLD = "runescape_bold"
    RUNESCAPE_SMALL = "runescape_small"
    AUTO = "auto"                       # pick font with best overall score


# Absolute or relative paths to the *.ttf files
_FONT_FILES: Dict[FontChoice, Path] = {
    FontChoice.RUNESCAPE:       Path("data/fonts/runescape.ttf"),
    FontChoice.RUNESCAPE_BOLD:  Path("data/fonts/runescape_bold.ttf"),
    FontChoice.RUNESCAPE_SMALL: Path("data/fonts/runescape_small.ttf"),
}

def render_font_glyphs(
    ttf_path: str | Path,
    *,
    characters: Optional[Iterable[str]] = None,
    pt_size: int = 24,
    text_color: int | tuple[int, int, int, int] = 255,   # white
    bg_color: int | tuple[int, int, int, int] = 0,       # black
    oversample: int = 4,          # supersampling factor for crisp edges
) -> Dict[str, Image.Image]:
    """
    Render every glyph in *characters* (defaults to printable ASCII) using the
    font at *ttf_path*, returning a dict {char: PIL.Image} where each image is
    tightly cropped around the non-background pixels.

    The images are *mode* “L” (8-bit grayscale).  Change `text_color/bg_color`
    or convert to “1” later if you need pure binary masks.
    """
    characters = (
        characters
        if characters is not None
        else (
            "".join(chr(c) for c in range(48, 58)) +  # digits 0-9
            "".join(chr(c) for c in range(65, 91)) +  # uppercase A-Z
            "".join(chr(c) for c in range(97, 123))   # lowercase a-z
        )
    )

    font = ImageFont.truetype(str(ttf_path), pt_size * oversample)

    glyphs: Dict[str, Image.Image] = {}
    for ch in characters:
        # Pillow ≥10: textbbox; Pillow <10: textsize or getbbox fallback
        try:
            bbox = font.getbbox(ch)
            w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        except AttributeError:
            w, h = font.getsize(ch)  # Pillow <10
            bbox = (0, 0, w, h)

        if w == 0 or h == 0:
            # Skip missing glyphs (e.g., space) or zero-width chars
            continue

        img = Image.new("L", (w, h), color=bg_color)
        draw = ImageDraw.Draw(img)
        # Draw at the negative offset of the bbox so the glyph starts at (0,0)
        draw.text((-bbox[0], -bbox[1]), ch, font=font, fill=text_color)

        # Down-sample to the requested size if we oversampled
        if oversample != 1:
            target = (w // oversample, h // oversample)
            img = img.resize(target, resample=Image.Resampling.LANCZOS)

        # Tight crop (in case of empty border after resize)
        nz = np.nonzero(np.array(img))
        if nz[0].size:  # avoid zero-sized glyphs
            ymin, ymax = nz[0].min(), nz[0].max() + 1
            xmin, xmax = nz[1].min(), nz[1].max() + 1
            img = img.crop((xmin, ymin, xmax, ymax))

        glyphs[ch] = img

    return glyphs


# ────────────────────────────────────────────────────────────────────
# 1.  Glyph library  –– every digit maps to a *list* of variants
#     (0 & 1 have two versions; the others just one for now)
# ────────────────────────────────────────────────────────────────────
digit_templates: Dict[str, List[Image.Image]] = {
    
}

for font, file in _FONT_FILES.items():
    if not file.exists():
        raise FileNotFoundError(f"Font file {file} not found.")

    glyphs = render_font_glyphs(
        file, pt_size=18, oversample=1
    )
    for ch, img in glyphs.items():
        digit_templates.setdefault(ch, []).append(img)

# ────────────────────────────────────────────────────────────────────
# 2.  Decode every PNG → binary mask (height 12 px)
# ────────────────────────────────────────────────────────────────────
def _img_to_mask(img: Image.Image) -> np.ndarray:
    img = img.convert("L")
    return (np.array(img) > 0).astype(np.uint8)  # 0/1 mask
        

def _normalise(glyph: np.ndarray, height: int = 12) -> np.ndarray:
    h, w = glyph.shape
    w2 = int(round(w * height / h))
    return cv2.resize(glyph, (w2, height), interpolation=cv2.INTER_NEAREST) // 255

TEMPLATES: Dict[str, List[np.ndarray]] = {
    ch: [_normalise(_img_to_mask(b)) for b in blobs]    # <── added _normalise
    for ch, blobs in digit_templates.items()
}




# ────────────────────────────────────────────────────────────────────
# 3.  Core helpers (crop, split, normalise, distance)
# ────────────────────────────────────────────────────────────────────
def _crop_to_content(gray: np.ndarray) -> np.ndarray:
    coords = cv2.findNonZero(cv2.inRange(gray, 200, 255))
    if coords is None:
        return gray
    x, y, w, h = cv2.boundingRect(coords)
    return gray[y : y + h, x : x + w]


def _split_into_digits(strip: np.ndarray) -> List[np.ndarray]:
    mask = cv2.inRange(strip, 200, 255)
    col_sum = mask.sum(axis=0)

    rois, in_digit, start = [], False, 0
    for i, v in enumerate(col_sum):
        if v and not in_digit:          # start of a glyph
            start, in_digit = i, True
        elif not v and in_digit:        # end of a glyph
            rois.append(mask[:, start:i])
            in_digit = False
    if in_digit:
        rois.append(mask[:, start:])

    # tighten each ROI
    trimmed = []
    for roi in rois:
        x, y, w, h = cv2.boundingRect(cv2.findNonZero(roi))
        trimmed.append(roi[y : y + h, x : x + w])
    return trimmed





def _dist(a: np.ndarray, b: np.ndarray) -> int:
    """Hamming distance after width-padding."""
    _, w1 = a.shape
    _, w2 = b.shape
    w = max(w1, w2)
    a_pad = np.pad(a, ((0, 0), (0, w - w1)))
    b_pad = np.pad(b, ((0, 0), (0, w - w2)))
    return np.count_nonzero((a_pad > 0) ^ (b_pad > 0))


def _best_match(norm: np.ndarray) -> str:
    best_char, best_score = "?", 1e9
    for ch, masks in TEMPLATES.items():
        for m in masks:
            s = _dist(norm, m)
            if s < best_score:
                best_score, best_char = s, ch
    return best_char


# ────────────────────────────────────────────────────────────────────
# 4.  Public API
# ────────────────────────────────────────────────────────────────────
def execute(img: Image.Image) -> str:
    """
    Accepts a PIL.Image (screenshot crop of the HUD value)  
    Returns the recognised numeric string.
    """
    gray = np.array(img.convert("L"))
    digits = _split_into_digits(_crop_to_content(gray))
    
    return "".join(_best_match(_normalise(d)) for d in digits)


def debug():
    for character, templates in digit_templates.items():
        dest = Path(f'ocr_debug/fonts')
        dest.mkdir(parents=True, exist_ok=True)
        for i, template in enumerate(templates):
            template.save(dest / f"{character}_{i}.png")

debug()
        