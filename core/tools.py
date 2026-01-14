import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageChops
from dataclasses import dataclass
from enum import Enum
from core import ocr
from typing import Tuple, Optional, List
from core.region_match import MatchResult, ShapeResult, MatchShape
from functools import wraps
# Add this import (safe even if not enabled; enqueue is a no-op until enable() is called)
from core import cv_debug
from io import BytesIO
import base64
from core.logger import get_logger



def find_subimage(parent: Image.Image,
                  template: Image.Image,
                  min_scale: float = 1,
                  max_scale: float = 1,
                  scale_step: float = 0.1,
                  method=cv2.TM_CCORR_NORMED
                  ) -> MatchResult:
    """
    Search `parent` for the best match to `template`, ignoring transparent pixels
    and trying scales from min_scale to max_scale in increments of scale_step.
    Returns the MatchResult at the scale & location with highest confidence.
    """
    # --- prepare parent image as BGR ---
    parent_rgba = np.array(parent.convert("RGBA"))
    parent_bgr  = cv2.cvtColor(parent_rgba, cv2.COLOR_RGBA2BGR)

    # --- prepare template + mask from its alpha channel ---
    tpl_rgba = np.array(template.convert("RGBA"))
    tpl_bgr  = cv2.cvtColor(tpl_rgba, cv2.COLOR_RGBA2BGR)
    tpl_mask = tpl_rgba[:, :, 3]  # alpha channel: 0 = transparent, 255 = opaque

    best = MatchResult(0, 0, 0, 0, confidence=-1.0, scale=1.0)
    parent_h, parent_w = parent_bgr.shape[:2]

    # loop over scales
    scale = min_scale
    while scale <= max_scale + 1e-6:
        # compute new size
        w = int(tpl_bgr.shape[1] * scale)
        h = int(tpl_bgr.shape[0] * scale)
        # skip if template is larger than parent
        if 1 < w < parent_w and 1 < h < parent_h:
            resized_tpl  = cv2.resize(tpl_bgr, (w, h),
                                      interpolation=cv2.INTER_AREA if scale < 1.0 else cv2.INTER_CUBIC)
            resized_mask = cv2.resize(tpl_mask, (w, h), interpolation=cv2.INTER_NEAREST)

            # matchTemplate with mask (only works for SQDIFF or CCORR_NORMED)
            result = cv2.matchTemplate(parent_bgr,
                                       resized_tpl,
                                       method,
                                       mask=resized_mask)
            
            result = np.nan_to_num(result, nan=-1.0, posinf=-1.0, neginf=-1.0)

            # get best match
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            if method in (cv2.TM_CCORR_NORMED, cv2.TM_CCOEFF_NORMED):
                confidence = max_val
                top_left   = max_loc
            else:
                # TM_SQDIFF variants: lower = better, so invert
                confidence = 1.0 - min_val
                top_left   = min_loc
                
            if confidence > best.confidence:
                best = MatchResult(
                    start_x=top_left[0],
                    start_y=top_left[1],
                    end_x=top_left[0] + w,
                    end_y=top_left[1] + h,
                    confidence=confidence,
                    scale=scale
                )

        scale += scale_step

    if best.confidence < 0:
        raise ValueError("No valid match found (template never fit inside parent).")

    # Non-blocking debug enqueue; does nothing unless cv_debug.enable() was called.
    try:
        cv_debug.enqueue_match(parent, template, best)
    except Exception:
        pass

    return best

def find_subimages(
    parent: Image.Image,
    template: Image.Image,
    min_scale: float = 1,
    max_scale: float = 1,
    scale_step: float = 0.1,
    method=cv2.TM_CCORR_NORMED,
    min_confidence: float = 0.5,
    max_count: int = 9999
) -> List[MatchResult]:
    answers = []
    parent = parent.copy()
    m = find_subimage(
        parent=parent,
        template=template,
        min_scale=min_scale,
        max_scale=max_scale,
        scale_step=scale_step,
        method=method
    )
    while m.confidence >= min_confidence and max_count > len(answers):
        answers.append(m)
        # remove the found match from the parent image
        parent = m.remove_from(parent)
        # find the next match in the updated parent image
        m = find_subimage(
            parent=parent,
            template=template,
            min_scale=min_scale,
            max_scale=max_scale,
            scale_step=scale_step,
            method=method
        )
    return answers


def mask_colors(
        image: Image.Image, 
        colors: List[Tuple[int, int, int]], 
        tolerance: int = 30
    ) -> Image.Image:
    """
    Create a mask for the specified colors in the image.
    The mask will be a new image where pixels matching the specified colors
    are set to white, and all other pixels are set to black.
    """
    mask = Image.new("L", image.size, 0)  # Create a black mask

    for color in colors:
        # Create a color range for the mask
        r, g, b = color
        lower_bound = (max(0, r - tolerance), max(0, g - tolerance), max(0, b - tolerance))
        upper_bound = (min(255, r + tolerance), min(255, g + tolerance), min(255, b + tolerance))

        # Create a temporary image to find the matching pixels
        temp_image = image.convert("RGB")
        temp_mask = Image.new("L", image.size, 0)

        for x in range(temp_image.width):
            for y in range(temp_image.height):
                pixel = temp_image.getpixel((x, y))
                if (lower_bound[0] <= pixel[0] <= upper_bound[0] and
                    lower_bound[1] <= pixel[1] <= upper_bound[1] and
                    lower_bound[2] <= pixel[2] <= upper_bound[2]):
                    temp_mask.putpixel((x, y), 255)

        # Combine the temporary mask with the main mask for each color
        mask = ImageChops.lighter(mask, temp_mask)
    return mask.convert("L")  # Convert to binary mask (black and white)
    





def write_text_to_image(image: Image, text: str, font_size: int = 20, color="black") -> Image.Image:

    # Load a default font with the specified size
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except IOError:
        font = ImageFont.load_default()

    # Calculate text dimensions
    text_width = font.getlength(text)
    new_width = max(image.width, text_width + 20)
    new_height = image.height + font_size + 20
    new_image = Image.new("RGBA", (int(new_width), int(new_height)), (255, 255, 255, 0))

    # Paste the original image onto the new image
    new_image.paste(image, (0, 0))

    # Write the text below the original image
    draw = ImageDraw.Draw(new_image)
    text_x = (new_width - text_width) // 2
    text_y = image.height + 10
    draw.text((text_x, text_y), text, fill=color, font=font)

    return new_image

def draw_box_on_image(image: Image, match: MatchResult, padding_x=0, padding_y=0, box_color="green") -> Image.Image:

    # Apply padding
    start_x = max(0, match.start_x - padding_x)
    start_y = max(0, match.start_y - padding_y)
    end_x = min(image.width, match.end_x + padding_x)
    end_y = min(image.height, match.end_y + padding_y)

    # Draw rectangle
    draw = ImageDraw.Draw(image)
    draw.rectangle([start_x, start_y, end_x, end_y], outline=box_color, width=2)

    return image

def draw_circle_on_image(image: Image, match: MatchResult, padding_x=0, padding_y=0, box_color="green") -> Image.Image:

    # Apply padding
    start_x = max(0, match.start_x - padding_x)
    start_y = max(0, match.start_y - padding_y)
    end_x = min(image.width, match.end_x + padding_x)
    end_y = min(image.height, match.end_y + padding_y)

    # Draw rectangle
    draw = ImageDraw.Draw(image)
    draw.circle([start_x, start_y, end_x, end_y], outline=box_color, width=2)

    return image

# ── helper to order cv2.boxPoints result TL‑TR‑BR‑BL ───────────────────
def _order_box(pts: np.ndarray) -> list[tuple[int, int]]:
    # sort by y (row) then x (col)
    pts = pts[np.lexsort((pts[:, 0], pts[:, 1]))]      # top 2 then bottom 2
    tl, tr = sorted(pts[:2], key=lambda p: p[0])       # left‑most is TL
    bl, br = sorted(pts[2:], key=lambda p: p[0])       # left‑most is BL
    return [tuple(tl), tuple(tr), tuple(br), tuple(bl)]

# ───────────────────────────────────────────────────────────────────────
def find_color_box(
    pil_img: Image.Image,
    target_rgb: Tuple[int, int, int],
    tol: int = 40,
) -> ShapeResult:
    """
    Locate the largest rectangular outline drawn in `target_rgb` (± `tol`)
    and return a ShapeResult whose four vertices sit *inside* that border.
    Works for both axis‑aligned and rotated rectangles.
    """
    # 1. colour mask ────────────────────────────────────────────────────
    arr = np.asarray(pil_img.convert("RGB"))
    diff = np.abs(arr - np.array(target_rgb))
    mask = np.all(diff <= tol, axis=2) if tol else np.all(arr == target_rgb, axis=2)

    # 2. connected components – grab largest blob ──────────────────────
    num, labels = cv2.connectedComponents(mask.astype(np.uint8), connectivity=4)
    if num <= 1:
        raise ValueError("No pixels found with the specified colour.")

    best_area, coords_best = -1, None
    for lbl in range(1, num):
        coords = np.column_stack(np.where(labels == lbl))
        if coords.shape[0] > best_area:
            best_area, coords_best = coords.shape[0], coords

    rows, cols = coords_best[:, 0], coords_best[:, 1]
    top, bottom = rows.min(), rows.max()
    left, right = cols.min(), cols.max()
    h, w = bottom - top, right - left

    # 3. decide: on‑axis or rotated? ────────────────────────────────────
    # a narrow blob (thickness 1‑3 px) with very thin diagonals means axis‑aligned
    # 3. decide: on‑axis or rotated? ────────────────────────────────────
    if h == 0 or w == 0:
        raise ValueError("Degenerate box.")

    axis_ratio = min(h, w) / max(h, w)
    if axis_ratio < 0.05:
        axis_ratio = 0

    # replace this line ↓
    # filled = cv2.countNonZero(mask[top:bottom+1, left:right+1])
    filled = np.count_nonzero(mask[top:bottom + 1, left:right + 1])

    # 4B. rotated rectangle path ────────────────────────────────────────
    # OpenCV wants (x, y) not (row, col)
    pts_xy = np.flip(coords_best, axis=1).astype(np.float32)
    rect = cv2.minAreaRect(pts_xy)               # (cx,cy), (w,h), angle
    box = cv2.boxPoints(rect)                    # 4×2 float
    box = np.int32(box)

    # nudge each vertex 1 px toward the centre so it sits *inside* outline
    centre = np.mean(box, axis=0)
    vecs = centre - box
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    norms[norms == 0] = 1                        # avoid div‑by‑0
    box_in = (box + (vecs / norms)).astype(int)  # pull 1 px inward
    ordered = _order_box(box_in)

    # confidence ≈ blob area ÷ box perimeter (works for rotated too)
    w_rot, h_rot = rect[1]
    expected_perim = 2 * (w_rot + h_rot)
    confidence = best_area / max(expected_perim, 1)

    sr = ShapeResult(points=ordered, confidence=confidence)

    # Non-blocking debug enqueue; does nothing unless cv_debug.enable() was called.
    try:
        cv_debug.enqueue_match(pil_img, target_rgb, sr)
    except Exception:
        pass

    return sr


def mask_above_color_value(
        image: Image.Image,
        threshold: int = 200,
):
    """
    Create a mask for pixels in the image that have a color value above the specified threshold.
    The mask will be a new image where pixels above the threshold are set to white, and all other pixels are set to black.
    """
    # Create a binary mask based on the threshold for RGB channels
    mask = Image.new("L", image.size, 0)  # Create a black mask

    for x in range(image.width):
        for y in range(image.height):
            r, g, b = image.getpixel((x, y))
            if r > threshold or g > threshold or b > threshold:
                mask.putpixel((x, y), 255)

    return mask.convert("L")


def calculate_color_percentage(
    image: Image.Image,
    target_color: Tuple[int, int, int],
    tolerance: int = 30
) -> float:
    """
    Calculate the percentage of pixels in the image that match the target color
    within the specified tolerance. Returns a float between 0.0 and 1.0.
    
    Args:
        image: PIL Image to analyze
        target_color: (R, G, B) tuple of the target color
        tolerance: Allowable difference per channel (0-255)
        
    Returns:
        float: Percentage of matching pixels (0.0 to 1.0)
    """
    if image.mode != "RGB":
        image = image.convert("RGB")
        
    # Use int16 to handle potential negative results from subtraction before abs to prevent wrap-around
    img_arr = np.array(image, dtype=np.int16)
    target = np.array(target_color, dtype=np.int16)
    
    # Calculate absolute difference per channel
    # This creates a (H, W, 3) array of differences
    diff = np.abs(img_arr - target)
    
    # Check matching pixels: all channels must be <= tolerance
    # Axis 2 is the color channel dimension
    matches = np.all(diff <= tolerance, axis=2)
    
    total_pixels = image.width * image.height
    if total_pixels == 0:
        return 0.0
        
    return np.count_nonzero(matches) / total_pixels


from functools import wraps
import time
import inspect
from PIL import ImageFont
import re
from difflib import SequenceMatcher

def text_similarity(basetext: str, subtext: str) -> float:
    """
    Calculate similarity for a potential substring match.
    
    For exact substring matches, returns 1.0.
    Otherwise, finds the best matching segment within basetext.
    
    Args:
        basetext (str): The full text to search within.
        subtext (str): The text expected to be a partial or full substring.
        
    Returns:
        float: The similarity ratio (0.0 to 1.0), with 1.0 indicating exact substring match.
    """
    # Fast path for exact substring
    if subtext in basetext:
        return 1.0
    
    # Otherwise find best matching segment
    best_ratio = 0.0
    subtext_len = len(subtext)
    
    # For very short subtexts, revert to general similarity
    if subtext_len <= 3:
        return SequenceMatcher(None, basetext, subtext).ratio()
    
    # Slide a window of subtext length through basetext
    for i in range(len(basetext) - subtext_len + 1):
        window = basetext[i:i+subtext_len]
        ratio = SequenceMatcher(None, window, subtext).ratio()
        best_ratio = max(best_ratio, ratio)
    
    return best_ratio

def timeit(func=None, *, do_log: bool = False):
    """Decorator usable as @timeit or @timeit(do_log=True).

    Shows ClassName.method only when the call truly originates from that class
    (instance or @classmethod).
    """
    log = get_logger("timeit")

    def _decorate(f):
        qual_parts = f.__qualname__.split(".")
        cls_name   = qual_parts[-2] if len(qual_parts) > 1 else None
        cls_obj    = None  # resolved lazily

        @wraps(f)
        def wrapper(*args, **kwargs):
            nonlocal cls_obj

            # Resolve the class object the first time we actually get called
            if cls_obj is None and cls_name:
                mod = inspect.getmodule(f)
                cls_obj = getattr(mod, cls_name, None)

            start = time.time()
            try:
                return f(*args, **kwargs)
            finally:
                dur   = time.time() - start
                first = args[0] if args else None

                if cls_obj and first is not None and (first is cls_obj or isinstance(first, cls_obj)):
                    label = f"{cls_name}.{f.__name__}"
                else:
                    label = f.__name__

                if do_log:
                    log.debug("%s took %.3f seconds", label, dur)

        return wrapper

    # Called as @timeit without parens
    if callable(func):
        return _decorate(func)
    # Called as @timeit(...)
    return _decorate

def seconds_to_hms(total_seconds: float | int) -> str:
    """
    Convert seconds → `HH:MM:SS` (hours may exceed 24 if you like).

    Examples
    --------
    >>> seconds_to_hms(3661)
    '01:01:01'
    >>> seconds_to_hms(98765.4)
    '27:26:05'
    """
    # Round to nearest second (change to int(total_seconds) for simple truncation)
    total_seconds = int(round(total_seconds))

    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    return f"{hours:02}:{minutes:02}:{seconds:02}"


# ───────────────────────────────────────────────────────────────────────
# New utilities: crop transparent borders and (de)serialization helpers
# ───────────────────────────────────────────────────────────────────────

def crop_transparent_border(img: Image.Image, padding: int = 0) -> Image.Image:
    """
    Remove fully transparent rows/columns around an image.
    A pixel is considered transparent if alpha == 0. Padding (in px) can
    be added back around the crop. Returns the cropped image (RGBA).
    """
    if img.mode != "RGBA":
        img = img.convert("RGBA")

    alpha = img.split()[-1]
    bbox = alpha.getbbox()  # bounding box of non-zero alpha
    if not bbox:
        # Entire image is fully transparent; return as-is
        return img

    left, top, right, bottom = bbox
    if padding:
        left = max(0, left - padding)
        top = max(0, top - padding)
        right = min(img.width, right + padding)
        bottom = min(img.height, bottom + padding)

    return img.crop((left, top, right, bottom))


def image_to_base64(img: Image.Image, fmt: str = "PNG") -> str:
    """Encode a PIL Image to a base64 string (without data URI prefix)."""
    buf = BytesIO()
    img.save(buf, format=fmt)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def base64_to_image(b64: str) -> Image.Image:
    """Decode a base64 image string (no data URI) to a PIL Image."""
    data = base64.b64decode(b64)
    return Image.open(BytesIO(data))