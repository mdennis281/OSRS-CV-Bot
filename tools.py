import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter
from dataclasses import dataclass
from enum import Enum
import pytesseract

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
        """Get a random point within the match result."""
        if MatchShape.SQUARE == self.shape:
            x = np.random.randint(self.start_x, self.end_x)
            y = np.random.randint(self.start_y, self.end_y)
        elif MatchShape.CIRCLE == self.shape:
            center_x = (self.start_x + self.end_x) // 2
            center_y = (self.start_y + self.end_y) // 2
            radius_x = (self.end_x - self.start_x) // 2
            radius_y = (self.end_y - self.start_y) // 2

            angle = np.random.uniform(0, 2 * np.pi)
            r = np.sqrt(np.random.uniform(0, 1)) * min(radius_x, radius_y)

            x = int(center_x + r * np.cos(angle))
            y = int(center_y + r * np.sin(angle))
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
    
    def extract_text(self, image: Image.Image) -> str:
        """Extract text from the match result area."""
        img = image.crop((self.start_x, self.start_y, self.end_x, self.end_y))
        # Use OCR or any other method to extract text from cropped_image
        # For now, we will just return a placeholder string

        rgba = np.array(img)

        # 1. HSV masking to isolate colored text
        bgr = cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGR)
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        ranges = [
            ((40,  50,  50), (90, 255, 255)),   # green
            ((10, 100, 100), (25, 255, 255)),   # orange/yellow
            ((0,  100, 100), (10, 255, 255)),   # red low
            ((160,100, 100), (180,255,255)),    # red high
        ]
        mask = sum([cv2.inRange(hsv, lo, hi) for lo, hi in ranges])
        isolated = cv2.bitwise_and(rgba, rgba, mask=mask)

        # 2. Grayscale + Otsu threshold
        gray = cv2.cvtColor(isolated, cv2.COLOR_RGBA2GRAY)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        processed = Image.fromarray(binary)
        config = '--psm 7 -c tessedit_char_whitelist=0123456789'
        text = pytesseract.image_to_string(processed, config=config).strip()
        return text


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
    subimage_path = "ui_icons/quick-prayer-disabled.png"
    output_path = "output.png"

    match = find_subimage(screenshot_path, subimage_path)
    print(f"Match found at: ({match.start_x}, {match.start_y}) -> ({match.end_x}, {match.end_y}) with confidence: {match.confidence}")

    output_image = draw_box_on_image(screenshot_path, match, padding_x=0, padding_y=0, box_color="red")
    
    output_image.show()





# def find_and_draw_box(screenshot_path, subimage_path, output_path, tolerance=0.8, padding_x=0, padding_y=0,box_color=(0, 255, 0)):
#     # Load images
#     screenshot = cv2.imread(screenshot_path, cv2.IMREAD_UNCHANGED)
#     subimage = cv2.imread(subimage_path, cv2.IMREAD_UNCHANGED)

#     if screenshot is None or subimage is None:
#         print("Error loading images.")
#         return

#     # Ignore transparent pixels in screenshot (if any)
#     if screenshot.shape[-1] == 4:  # Has alpha channel
#         mask = screenshot[:, :, 3] > 0
#         screenshot = screenshot[:, :, :3]  # Remove alpha for matching

#     if subimage.shape[-1] == 4:  # Remove alpha channel from subimage
#         subimage = subimage[:, :, :3]

#     # Perform template matching
#     result = cv2.matchTemplate(screenshot, subimage, cv2.TM_CCOEFF_NORMED)
#     min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

#     if max_val < tolerance:
#         print(f"No match found within the given tolerance. {subimage_path}")
#         return

#     # Calculate bounding box coordinates
#     start_x, start_y = max_loc
#     end_x = start_x + subimage.shape[1]
#     end_y = start_y + subimage.shape[0]

#     # Apply padding
#     start_x = max(0, start_x - padding_x)
#     start_y = max(0, start_y - padding_y)
#     end_x = min(screenshot.shape[1], end_x + padding_x)
#     end_y = min(screenshot.shape[0], end_y + padding_y)

#     # Draw rectangle around detected region
#     cv2.rectangle(screenshot, (start_x, start_y), (end_x, end_y), box_color, 1)

#     # Save the modified screenshot
#     cv2.imwrite(output_path, screenshot)
#     print(f"Match found at: ({start_x}, {start_y}) -> ({end_x}, {end_y})")
#     print(f"Saved output image to: {output_path}")

# # Example usage
# TOLERANCE = 0.7
# find_and_draw_box("runelite_screenshot.png", "ui_icons/ui_inventory.png", "output.png", tolerance=.2, padding_x=3, padding_y=3,box_color=(255,0,0))
# find_and_draw_box("output.png", "ui_icons/equipment.webp", "output.png", tolerance=.6, padding_x=3, padding_y=3)
# find_and_draw_box("output.png", "ui_icons/prayer.webp", "output.png", tolerance=TOLERANCE, padding_x=3, padding_y=3)
# find_and_draw_box("output.png", "ui_icons/friends.webp", "output.png", tolerance=TOLERANCE, padding_x=3, padding_y=3)
# find_and_draw_box("output.png", "ui_icons/stats.webp", "output.png", tolerance=TOLERANCE, padding_x=3, padding_y=3)
# find_and_draw_box("output.png", "ui_icons/quests.webp", "output.png", tolerance=TOLERANCE, padding_x=3, padding_y=3)
# find_and_draw_box("output.png", "ui_icons/map.webp", "output.png", tolerance=TOLERANCE, padding_x=3, padding_y=3)
# find_and_draw_box("output.png", "ui_icons/spellbook.webp", "output.png", tolerance=TOLERANCE, padding_x=3, padding_y=3)
# find_and_draw_box("output.png", "ui_icons/inventory.webp", "output.png", tolerance=TOLERANCE, padding_x=3, padding_y=3)
# find_and_draw_box("output.png", "ui_icons/logout.webp", "output.png", tolerance=TOLERANCE, padding_x=3, padding_y=3)
# find_and_draw_box("output.png", "ui_icons/compass.webp", "output.png", tolerance=TOLERANCE, padding_x=3, padding_y=3)
# find_and_draw_box("output.png", "ui_icons/emotes.webp", "output.png", tolerance=.5, padding_x=3, padding_y=3)
# find_and_draw_box("output.png", "ui_icons/combat.webp", "output.png", tolerance=TOLERANCE, padding_x=3, padding_y=3)
# find_and_draw_box("output.png", "ui_icons/music.webp", "output.png", tolerance=.6, padding_x=3, padding_y=3)
# find_and_draw_box("output.png", "ui_icons/settings.webp", "output.png", tolerance=.5, padding_x=3, padding_y=3)
# find_and_draw_box("output.png", "ui_icons/chat.webp", "output.png", tolerance=TOLERANCE, padding_x=3, padding_y=3)
# find_and_draw_box("output.png", "ui_icons/account.webp", "output.png", tolerance=.6, padding_x=3, padding_y=3)
