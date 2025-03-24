import cv2
import numpy as np
from PIL import Image, ImageDraw
from dataclasses import dataclass

@dataclass
class MatchResult:
    start_x: int
    start_y: int
    end_x: int
    end_y: int
    confidence: float

def find_subimage(screenshot_path, subimage_path) -> MatchResult:
    # Load images
    screenshot = cv2.imread(screenshot_path, cv2.IMREAD_UNCHANGED)
    subimage = cv2.imread(subimage_path, cv2.IMREAD_UNCHANGED)

    if screenshot is None or subimage is None:
        raise ValueError("Error loading images.")

    # Handle transparency
    if screenshot.shape[-1] == 4:  
        screenshot = screenshot[:, :, :3]  # Remove alpha for matching
    if subimage.shape[-1] == 4:  
        subimage = subimage[:, :, :3]

    # Perform template matching
    result = cv2.matchTemplate(screenshot, subimage, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)  # Best match location

    # Calculate bounding box
    start_x, start_y = max_loc
    end_x = start_x + subimage.shape[1]
    end_y = start_y + subimage.shape[0]

    return MatchResult(start_x, start_y, end_x, end_y, max_val)

def draw_box_on_image(image_path, match: MatchResult, padding_x=0, padding_y=0, box_color="green") -> Image.Image:
    # Load image with PIL
    image = Image.open(image_path).convert("RGB")

    # Apply padding
    start_x = max(0, match.start_x - padding_x)
    start_y = max(0, match.start_y - padding_y)
    end_x = min(image.width, match.end_x + padding_x)
    end_y = min(image.height, match.end_y + padding_y)

    # Draw rectangle
    draw = ImageDraw.Draw(image)
    draw.rectangle([start_x, start_y, end_x, end_y], outline=box_color, width=2)

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
