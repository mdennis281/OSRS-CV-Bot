import cv2
import numpy as np

def find_inventory(screenshot_path, 
                   template_modern_path, 
                   template_classic_path,
                   inv_width, 
                   inv_height, 
                   match_threshold=0.8):
    """
    Attempts to locate and crop the OSRS inventory panel from a full screenshot.
    Returns the cropped inventory image (as a NumPy array) or None if not found.
    """

    # Read main screenshot
    screenshot = cv2.imread(screenshot_path, cv2.IMREAD_COLOR)
    gray_screenshot = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)

    # Load templates
    template_modern = cv2.imread(template_modern_path, cv2.IMREAD_GRAYSCALE)
    template_classic = cv2.imread(template_classic_path, cv2.IMREAD_GRAYSCALE)

    # Helper to run template matching and return best match location + value
    def match_template(img, templ):
        res = cv2.matchTemplate(img, templ, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
        return max_val, max_loc  # correlation, (x, y)

    # 1) Try modern anchor
    corr_modern, loc_modern = match_template(gray_screenshot, template_modern)
    if corr_modern >= match_threshold:
        x, y = loc_modern
        # Crop out the inventory
        inv_crop = screenshot[y : y + inv_height, x : x + inv_width]
        return inv_crop

    # 2) If modern fails, try classic anchor
    corr_classic, loc_classic = match_template(gray_screenshot, template_classic)
    if corr_classic >= match_threshold:
        x, y = loc_classic
        inv_crop = screenshot[y : y + inv_height, x : x + inv_width]
        return inv_crop

    # 3) If both fail, return None
    return None


# Example usage:
if __name__ == "__main__":
    # Suppose you measured your inventory panel to be 210 px wide x 320 px tall.
    INVENTORY_WIDTH  = 210
    INVENTORY_HEIGHT = 320

    cropped_inv = find_inventory(
        screenshot_path="runelite_screenshot.png",
        template_modern_path="inv_anchor_modern.png",
        template_classic_path="inv_anchor_classic.png",
        inv_width=INVENTORY_WIDTH,
        inv_height=INVENTORY_HEIGHT,
        match_threshold=0.8
    )

    if cropped_inv is not None:
        cv2.imwrite("cropped_inventory.png", cropped_inv)
        print("Inventory cropped and saved.")
    else:
        print("Could not find inventory region.")
