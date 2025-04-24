import base64, io, cv2, numpy as np
from pathlib import Path
from typing import List, Dict
from PIL import Image

# ────────────────────────────────────────────────────────────────────
# 1.  Glyph library  –– every digit maps to a *list* of variants
#     (0 & 1 have two versions; the others just one for now)
# ────────────────────────────────────────────────────────────────────
digit_templates_b64: Dict[str, List[str]] = {
    "0": [
        # wide “0”
        "iVBORw0KGgoAAAANSUhEUgAAAAcAAAAMCAAAAACL/vjMAAAAKUlEQVR4nFWMQQoAMAzCsv7/z9lhq7QiBAUFUCginwWx+0nPzpPZ/98LqcANA3RwVbgAAAAASUVORK5CYII=",
        # narrow “0”
        "iVBORw0KGgoAAAANSUhEUgAAAAIAAAAMCAAAAABt1zOIAAAAEklEQVR4nGNg+M/0n4GJAR8CAENuAhVTklnDAAAAAElFTkSuQmCC",
    ],
    "1": [
        # original “1”
        "iVBORw0KGgoAAAANSUhEUgAAAAYAAAAMCAAAAABkPJPyAAAAI0lEQVR4nIXLoREAAAjEsMD+Oz8Ch0FF9AqhgSaQrKd91E4DhIcHC1sG/ekAAAAASUVORK5CYII=",
        # shorter “1”
        "iVBORw0KGgoAAAANSUhEUgAAAAQAAAAMCAAAAABgyUPPAAAAH0lEQVR4nIXHsQ0AAAgDIOz/P9fBA1xIQEVJ4crDKAvNpQUP5Sq68QAAAABJRU5ErkJggg==",
    ],
    "2": [
        "iVBORw0KGgoAAAANSUhEUgAAAAcAAAAMCAAAAACL/vjMAAAAKklEQVR4nG3LMQ4AIAzDwGv//+cwUDqRxbKlFKG0WYKsbb+66G99f2riATeJC/72eVScAAAAAElFTkSuQmCC"
    ],
    "3": [
        "iVBORw0KGgoAAAANSUhEUgAAAAYAAAAMCAAAAABkPJPyAAAAJ0lEQVR4nGNkYPjPwMDIxAAB//8zMDD8h7KhgowQJaiCaNT//0gqAcN1Cgmnm5EAAAAAAElFTkSuQmCC"
    ],
    "4": [
        "iVBORw0KGgoAAAANSUhEUgAAAAcAAAAMCAAAAACL/vjMAAAAH0lEQVR4nGP4/5+BgYGBgYmBgTD9H7c8438GBEBSBwAVRQUPESb5zQAAAABJRU5ErkJggg=="
    ],
    "5": [
        "iVBORw0KGgoAAAANSUhEUgAAAAYAAAAMCAAAAABkPJPyAAAAKUlEQVR4nE3KsQkAMAzEwHuT/Vd2CkOcSggpDQo4ZK3oyTxu+zFfaHIBLD0ID6TLaYAAAAAASUVORK5CYII="
    ],
    "6": [
        "iVBORw0KGgoAAAANSUhEUgAAAAcAAAAMCAAAAACL/vjMAAAAKklEQVR4nGXLsQ0AIBDDwNPvv7MpQFAQpYodKMZNu+HtczwVPX97ff+DFmlDEvjgksL0AAAAAElFTkSuQmCC"
    ],
    "7": [
        "iVBORw0KGgoAAAANSUhEUgAAAAYAAAAMCAAAAABkPJPyAAAAI0lEQVR4nGP8z8DAwMDAxIAE/kNJJhQhKI8JRRmM9/8/khwALWcHB6rHcOcAAAAASUVORK5CYII="
    ],
    "8": [
        "iVBORw0KGgoAAAANSUhEUgAAAAcAAAAMCAAAAACL/vjMAAAAJ0lEQVR4nGNgYGD4/5+BgYkBDv5D0H8oG8pngAlB+HD1UHUY+qFSAML4E/NEJ02EAAAAAElFTkSuQmCC",
        "iVBORw0KGgoAAAANSUhEUgAAAAcAAAAMCAAAAACL/vjMAAAAKElEQVR4nGXLsREAMAzCwHf235kUiRubCk4IEo6RBNKzXq/J21v+v1wu2Ar+CzraPQAAAABJRU5ErkJggg=="
    ],
    "9": [
        "iVBORw0KGgoAAAANSUhEUgAAAAcAAAAMCAAAAACL/vjMAAAAKUlEQVR4nG2KsQ0AMAzCTP//2RmaVB3CAlgOCOTQUQDnP3490+Pjqz9d79oICsS2dXQAAAAASUVORK5CYII="
    ],
}

# ────────────────────────────────────────────────────────────────────
# 2.  Decode every PNG → binary mask (height 12 px)
# ────────────────────────────────────────────────────────────────────
def _b64_to_mask(b64str: str) -> np.ndarray:
    img = Image.open(io.BytesIO(base64.b64decode(b64str))).convert("L")
    return (np.array(img) > 0).astype(np.uint8)  # 0/1 mask


TEMPLATES: Dict[str, List[np.ndarray]] = {
    ch: [_b64_to_mask(b) for b in blobs] for ch, blobs in digit_templates_b64.items()
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


def _normalise(glyph: np.ndarray, height: int = 12) -> np.ndarray:
    h, w = glyph.shape
    w2 = int(round(w * height / h))
    return cv2.resize(glyph, (w2, height), interpolation=cv2.INTER_NEAREST) // 255


def _dist(a: np.ndarray, b: np.ndarray) -> int:
    """Hamming distance after width-padding."""
    h, w1 = a.shape
    h, w2 = b.shape
    w = max(w1, w2)
    a_pad = np.pad(a, ((0, 0), (0, w - w1)))
    b_pad = np.pad(b, ((0, 0), (0, w - w2)))
    return np.count_nonzero(a_pad ^ b_pad)


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