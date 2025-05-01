import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter
from dataclasses import dataclass
from enum import Enum
import pytesseract
from core import ocr
from typing import Tuple, Optional

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

class MatchShape(Enum):
    SQUARE = "square"
    CIRCLE = "circle"

@dataclass
class MatchResult:
    start_x: int
    start_y: int
    end_x: int
    end_y: int
    confidence: float = -1.0
    scale: float = 1.0
    shape: MatchShape = MatchShape.SQUARE

    def get_point_within(self) -> tuple[int, int]:
        """Uniform random pixel strictly inside the rectangle/ellipse."""
        # ── rectangle ────────────────────────────────────────────────
        if self.shape is MatchShape.SQUARE:
            return (
                np.random.randint(self.start_x, self.end_x),
                np.random.randint(self.start_y, self.end_y),
            )

        # ── ellipse ─────────────────────────────────────────────────
        cx, cy = (self.start_x + self.end_x) / 2, (self.start_y + self.end_y) / 2
        rx, ry = (self.end_x - self.start_x) / 2, (self.end_y - self.start_y) / 2

        if rx <= 0 or ry <= 0:            # degenerate → centre point
            return int(cx), int(cy)

        # rejection-sample integer pixels until one lands inside
        while True:
            x = np.random.randint(self.start_x, self.end_x)
            y = np.random.randint(self.start_y, self.end_y)
            dx = (x + 0.5) - cx           # +0.5 → test pixel-centre, not corner
            dy = (y + 0.5) - cy
            if (dx / rx) ** 2 + (dy / ry) ** 2 <= 1:
                return x, y
    
    def debug_draw(self, image: Image.Image, color="red", padding_x=0, padding_y=0) -> Image.Image:
        """Draw the match result on the image."""
        if self.shape == MatchShape.SQUARE:
            draw = ImageDraw.Draw(image)
            draw.rectangle([self.start_x - padding_x, self.start_y - padding_y, 
                            self.end_x + padding_x, self.end_y + padding_y], 
                           outline=color, width=2)
        elif self.shape == MatchShape.CIRCLE:
            draw = ImageDraw.Draw(image)
            center_x = (self.start_x + self.end_x) // 2
            center_y = (self.start_y + self.end_y) // 2
            radius_x = (self.end_x - self.start_x) // 2 + padding_x
            radius_y = (self.end_y - self.start_y) // 2 + padding_y
            draw.ellipse([center_x - radius_x, center_y - radius_y, 
                          center_x + radius_x, center_y + radius_y], 
                         outline=color, width=2)
            
        return image
    
    def extract_number(self, image: Image.Image, font: ocr.FontChoice = ocr.FontChoice.AUTO) -> str:
        """Extract text from the match result area."""
        img = image.crop((self.start_x, self.start_y, self.end_x, self.end_y))
        # Use OCR or any other method to extract text from cropped_image
        # For now, we will just return a placeholder string

        rgba = np.array(img)

        # 1. HSV masking to isolate colored text
        bgr = cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGR)
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        
        
        lower_hsv = np.array([ 0, 250, 250], dtype=np.uint8)
        upper_hsv = np.array([ 65, 255, 255], dtype=np.uint8)
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, lower_hsv, upper_hsv)
        #mask = sum([cv2.inRange(hsv, lo, hi) for lo, hi in ranges])
        isolated = cv2.bitwise_and(rgba, rgba, mask=mask)

        # 2. Grayscale + Otsu threshold
        gray = cv2.cvtColor(isolated, cv2.COLOR_RGBA2GRAY)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        #binary = cv2.bitwise_not(binary)
        processed = Image.fromarray(binary)
        ans = ocr.get_number(
            processed,
            font=font, #font,
            preprocess=False
        ) # , font)
        return ans


    def transform(self,offset_x: int, offset_y: int) -> 'MatchResult':
        """Transform the match result by applying an offset."""
        return MatchResult(
            start_x=self.start_x + offset_x,
            start_y=self.start_y + offset_y,
            end_x=self.end_x + offset_x,
            end_y=self.end_y + offset_y,
            shape=self.shape,
            confidence=self.confidence,
            scale=self.scale
        )
    
    def scale_px(self, pixels:int):
        """make the matchresult larger or smaller by a number of pixels"""
        self.start_x -= pixels
        self.start_y -= pixels
        self.end_x += pixels
        self.end_y += pixels

    def crop_in(self, image: Image.Image) -> Image.Image:
        """Crop the match result from the image."""
        return image.crop((self.start_x, self.start_y, self.end_x, self.end_y))
        



def find_subimage(parent: Image.Image,
                  template: Image.Image,
                  min_scale: float = 0.5,
                  max_scale: float = 1.5,
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

    return best

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

if __name__ == "__main__":
    # Example usage
    screenshot_path = "runelite_screenshot.png"
    subimage_path = "data/ui/quick-prayer-disabled.png"
    output_path = "output.png"

    match = find_subimage(screenshot_path, subimage_path)
    print(f"Match found at: ({match.start_x}, {match.start_y}) -> ({match.end_x}, {match.end_y}) with confidence: {match.confidence}")

    output_image = draw_box_on_image(screenshot_path, match, padding_x=0, padding_y=0, box_color="red")
    
    output_image.show()

def find_color_box(
    pil_img: Image.Image,
    target_rgb: Tuple[int, int, int],
    tol: int = 0,
) -> MatchResult:
    """
    Locate the largest rectangular outline drawn in `target_rgb`.
    Returns the bounding box strictly INSIDE the coloured outline.
    """
    # ─── 1.  Make a boolean mask of pixels that match the colour ────────────────
    img = pil_img.convert("RGB")
    arr = np.asarray(img)
    if tol == 0:
        mask = np.all(arr == target_rgb, axis=2)
    else:
        diff = np.abs(arr - np.array(target_rgb))
        mask = np.all(diff <= tol, axis=2)

    # ─── 2.  Connected-component labelling to split separate blobs ─────────────
    mask_u8 = mask.astype(np.uint8)
    num, labels = cv2.connectedComponents(mask_u8, connectivity=4)

    if num <= 1:
        raise ValueError("No pixels found with the specified colour.")

    # ─── 3.  Pick the blob with the most pixels (assume that is the box) ───────
    best_label = None
    best_area = -1
    coords_best = None

    for lbl in range(1, num):
        coords = np.column_stack(np.where(labels == lbl))
        area = coords.shape[0]
        if area > best_area:
            best_area = area
            best_label = lbl
            coords_best = coords

    if coords_best is None:
        raise ValueError("Could not find a coloured region.")

    # coords are (row, col)
    rows = coords_best[:, 0]
    cols = coords_best[:, 1]
    top, bottom = rows.min(), rows.max()
    left, right = cols.min(), cols.max()

    # shrink inside border (1 px) to guarantee we are within the outline
    if right - left > 2 and bottom - top > 2:  # avoid negative size
        left_in, right_in = left + 1, right - 1
        top_in, bottom_in = top + 1, bottom - 1
    else:  # fallback, use original
        left_in, right_in, top_in, bottom_in = left, right, top, bottom

    # confidence = coloured pixels inside / expected outline pixels
    expected_perimeter = 2 * ((right - left) + (bottom - top))
    confidence = best_area / max(expected_perimeter, 1)

    return MatchResult(left_in, top_in, right_in, bottom_in, confidence)



from functools import wraps
import time
from PIL import ImageFont


def timeit(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        # print(f"Function '{func.__name__}' took {end_time - start_time:.4f} seconds")
        return result
    return wrapper

