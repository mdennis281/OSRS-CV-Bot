import cv2
import numpy as np
import json
import base64
from PIL import Image
from io import BytesIO
import math

def find_best_matching_icon(input_image: Image.Image, icons_data: dict, tolerance=0.01):
    # Convert input image to OpenCV format (ignoring transparency)
    input_image = input_image.convert("RGBA")
    input_np = np.array(input_image)
    mask = input_np[:, :, 3] > 0  # Non-transparent pixels
    input_np = input_np[:, :, :3]  # Drop alpha channel
    
    cv_img = cv2.cvtColor(input_np, cv2.COLOR_BGR2Lab)

    matches = []

    for item_id, b64_icon in icons_data.items():
        # Decode base64 image
        icon_bytes = base64.b64decode(b64_icon)
        icon_img = Image.open(BytesIO(icon_bytes)).convert("RGBA")
        icon_np = np.array(icon_img)
        

        if icon_np.shape[0] > cv_img.shape[0] or icon_np.shape[1] > cv_img.shape[1]:
            continue  # Skip oversized icons

        # Create a transparency mask for non-transparent pixels
        icon_mask = icon_np[:, :, 3] > 0
        matched_pixels = np.sum(icon_mask)  # Count of non-transparent pixels

        if matched_pixels < 5:  # Ignore very small icons
            continue

        icon_np = icon_np[:, :, :3]  # Drop alpha channel
        cv_icon = cv2.cvtColor(icon_np, cv2.COLOR_BGR2Lab)

        # Apply transparency mask to avoid considering transparent areas
        cv_icon = cv2.bitwise_and(cv_icon, cv_icon, mask=icon_mask.astype(np.uint8))
        cv_img_masked = cv2.bitwise_and(cv_img, cv_img, mask=mask.astype(np.uint8))

        # Perform template matching
        result = cv2.matchTemplate(cv_img_masked, cv_icon, cv2.TM_SQDIFF_NORMED)
        min_val, max_val, _, max_loc = cv2.minMaxLoc(result)

        # if item_id in ["558","13563"]: 
        #     print(item_id)
        #     print(f'{max_val}, {max_loc}, {min_val}, {matched_pixels}')
        #     print()

        if max_val >= tolerance:
            # Weighted score to favor larger matched regions
            weighted_score = min_val #* math.log(1 + matched_pixels)
            matches.append((item_id, weighted_score, max_val, matched_pixels))

    # Sort based on weighted score in descending order
    matches.sort(key=lambda x: x[1], reverse=False)

    return matches[:20]




# Load input image
input_img = Image.open("output/1_1.png")

# Load item cache data
item_db_path = "osrsbox-db-master/data/items/items-cache-data.json"
with open(item_db_path, "r") as f:
    item_data = json.load(f)

# Load icons data
icons_json_path = "osrsbox-db-master/data/icons/icons-items-complete.json"
with open(icons_json_path, "r") as f:
    icons_data = json.load(f)

# Filter items based on criteria
valid_item_ids = {
    str(item_id): item["name"]
    for item_id, item in item_data.items()
    if item["linked_id_item"] is None and item["linked_id_placeholder"] is not None
}

# Filter icons to only include valid item IDs
filtered_icons_data = {item_id: icons_data[item_id] for item_id in valid_item_ids if item_id in icons_data}

# Find best matches
best_matches = find_best_matching_icon(input_img, filtered_icons_data)

# Print results
print("Best matching items:")
for match in best_matches:
    item_name = valid_item_ids.get(match[0], "Unknown Item")
    print(f"{match[0]} - {item_name} - Confidence: {match[1]:.2f}")

output_dir = "./output"

last_row = -1
print("Processing rows...")
for idx in range(28):
        row = (idx // 4) + 1
        col = (idx % 4) + 1
        if row != last_row:
            print(f"Processing row {row}...")
            last_row = row
        input_img = Image.open(f"{output_dir}/{row}_{col}.png")
        best_matches = find_best_matching_icon(input_img, filtered_icons_data)
        item_name = valid_item_ids.get(best_matches[0][0], "Unknown Item")
        print(f"\t{item_name} - Confidence: {int((1-best_matches[0][1]) * 100)}%")


