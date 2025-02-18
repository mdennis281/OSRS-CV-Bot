import cv2
import numpy as np
import json
import base64
from PIL import Image
from io import BytesIO
import math
from collections import Counter
from dataclasses import dataclass
from typing import List
from scipy.spatial.distance import cdist
from concurrent.futures import ThreadPoolExecutor

def rgb_to_lab(color):
    """Converts an RGB color tuple to LAB space for better color distance measurement."""
    color = np.array(color, dtype=np.uint8).reshape(1, 1, 3)
    return cv2.cvtColor(color, cv2.COLOR_RGB2Lab).flatten()

def color_distance(c1, c2):
    """Computes Euclidean distance in LAB space for two RGB colors."""
    return np.linalg.norm(rgb_to_lab(c1) - rgb_to_lab(c2))

def compare_color_distributions(dist1, dist2):
    """Computes a normalized similarity score between two color distributions using LAB color distance."""
    color_matrix1 = np.array([rgb_to_lab(c) for c in dist1.keys()])
    color_matrix2 = np.array([rgb_to_lab(c) for c in dist2.keys()])
    
    distances = cdist(color_matrix1, color_matrix2, metric='euclidean')
    min_distances = distances.min(axis=1)  # Find closest match for each color
    
    # Normalize distance into similarity (higher means more similar, between 0 and 1)
    max_distance = 100  # Approximate max LAB color distance
    color_similarity = np.exp(-min_distances / max_distance).sum() / len(dist1)
    
    return max(0, min(1, color_similarity))  # Ensure score is between 0 and 1

@dataclass
class ItemMatchCandidate:
    item_id: int
    color_score: float
    template_score: float

    @property
    def total_score(self) -> float:
        if self.color_score < 0:
            return self.template_score
        return (self.template_score * 0.4) + (self.color_score * 0.6)  # Balance weighting

def extract_color_distribution(image_np):
    """Extracts color distribution from an image (handling both RGB and RGBA formats)."""
    pixels = image_np.reshape(-1, image_np.shape[-1])
    
    if image_np.shape[-1] == 4:  # RGBA image
        mask = pixels[:, 3] > 0  # Use alpha channel to filter
        filtered_pixels = pixels[mask][:, :3]  # Keep only RGB values
    else:  # RGB image
        filtered_pixels = pixels[:, :3]  # No alpha channel to filter
    
    # Convert to tuple for hashing
    color_counts = Counter(map(tuple, filtered_pixels))
    total_pixels = sum(color_counts.values())
    
    # Normalize
    color_distribution = {color: count / total_pixels for color, count in color_counts.items()}
    return color_distribution

def process_icon(item, threshold=0.5):
    
    item_id, b64_icon, input_colors, cv_img, mask = item
    #print('Starting process_icon - '+item_id)
    # Decode base64 image
    icon_bytes = base64.b64decode(b64_icon)
    icon_img = Image.open(BytesIO(icon_bytes)).convert("RGBA")
    icon_np = np.array(icon_img)
    
    if icon_np.shape[0] > cv_img.shape[0] or icon_np.shape[1] > cv_img.shape[1]:
        return None  # Skip oversized icons

    # Create a transparency mask
    icon_mask = icon_np[:, :, 3] > 0
    matched_pixels = np.sum(icon_mask)
    
    if matched_pixels < 5:
        return None  # Ignore very small icons
    
    icon_np = icon_np[:, :, :3]  # Drop alpha channel
    cv_icon = cv2.cvtColor(icon_np, cv2.COLOR_RGB2BGR)

    # Apply transparency mask
    cv_icon = cv2.bitwise_and(cv_icon, cv_icon, mask=icon_mask.astype(np.uint8))
    cv_img_masked = cv2.bitwise_and(cv_img, cv_img, mask=mask.astype(np.uint8))

    # Perform template matching
    result = cv2.matchTemplate(cv_img_masked, cv_icon, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, _ = cv2.minMaxLoc(result)
    
    # Color similarity using improved metric
    if max_val >= threshold:
        icon_colors = extract_color_distribution(icon_np)
        color_similarity = compare_color_distributions(input_colors, icon_colors)
    else: color_similarity = -1
    
    return ItemMatchCandidate(
        item_id=int(item_id),
        color_score=color_similarity,
        template_score=max_val
    )

def find_best_matching_icon(input_image: Image.Image, icons_data: dict, tolerance=0.01):
    input_image = input_image.convert("RGBA")
    input_np = np.array(input_image)
    
    mask = input_np[:, :, 3] > 0  # Non-transparent pixels
    input_np = input_np[:, :, :3]  # Drop alpha channel
    
    cv_img = cv2.cvtColor(input_np, cv2.COLOR_RGB2BGR)
    input_colors = extract_color_distribution(np.array(input_image))
    
    matches = []
    items = [(item_id, b64_icon, input_colors, cv_img, mask) for item_id, b64_icon in icons_data.items()]
    
    with ThreadPoolExecutor(max_workers=20) as executor:
        results = list(executor.map(process_icon, items))
    
    matches = [r for r in results if r is not None]
    matches.sort(key=lambda c: c.total_score, reverse=True)
    return matches[:20]




# Load input image
input_img = Image.open("output/7_1.png")

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
# print("Best matching items:")
# for match in best_matches:
#     item_name = valid_item_ids.get(str(match.item_id), "Unknown Item")
#     print(f"{match.item_id} - {item_name} - Total: {int(match.total_score*100)}% - Template: {int(match.template_score*100)}% - Color: {int(match.color_score*100)}%")

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
        item_name = valid_item_ids.get(str(best_matches[0].item_id), "Unknown Item")
        match = best_matches[0]
        print(f"{match.item_id} - {item_name} - Total: {int(match.total_score*100)}% - Template: {int(match.template_score*100)}% - Color: {int(match.color_score*100)}%")








