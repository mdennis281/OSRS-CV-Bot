import numpy as np
from PIL import Image
import os
def extract_osrs_items(image_path):
    """
    Extracts all 28 OSRS inventory items using a pure PIL-based approach for precise centering.
    
    Ensures:
    - No overlapping icons on edges
    - No bottom menu artifacts
    - Icons are centered in the image (X & Y)
    - All images are the same height and width
    
    :param image_path: Path to the inventory image
    :return: List of centered and segmented inventory item images.
    """
    # Load image with PIL for correct transparency handling
    pil_image = Image.open(image_path).convert("RGBA")
    width, height = pil_image.size
    
    # Define OSRS inventory grid properties
    cols, rows = 4, 7
    slot_size = 36  # Standard slot size
    spacing_x = 6  # Spacing between slots
    spacing_y = 0

    # Compute inventory grid positioning starting from the center row
    total_grid_width = cols * (slot_size + spacing_x) - spacing_x
    total_grid_height = rows * (slot_size + spacing_y) - spacing_y
    start_x = (width - total_grid_width) // 2
    start_y = (height - total_grid_height) // 2
    center_row = rows // 2

    extracted_items = []

    row_order = [0,1,2,3,4,5,6]
    
    for row in row_order:
        for col in range(cols):
            # Compute bounding box per slot
            x1 = start_x + col * (slot_size + spacing_x)
            y1 = start_y + row * (slot_size + spacing_y)
            x2 = x1 + slot_size
            y2 = y1 + slot_size

            # Crop individual item slot
            slot_img = pil_image.crop((x1, y1, x2, y2))
            
            # Find the bounding box of the non-transparent pixels
            bbox = slot_img.getbbox()
            if not bbox:
                continue  # Skip empty slots
            
            # Crop to the item's actual bounding box
            item_crop = slot_img.crop(bbox)
            item_w, item_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
            
            # Create a new transparent canvas
            final_item = Image.new("RGBA", (40, 40), (255, 255, 255, 255))  # White background for visibility
            paste_x = (40 - item_w) // 2
            paste_y = (40 - item_h) // 2
            final_item.paste(item_crop, (paste_x, paste_y), item_crop)
            # replace all pixels that are #3e3529
            

            inventory_colors = [
                (62, 53, 41),  # Background color
                (64, 54, 44),  # Border color
                (47, 38, 25),
                (59, 50, 38),
                (55,47,35)

            ]
            for color in inventory_colors:
                final_item = replace_color(
                    final_item, 
                    color, 
                    (255, 255, 255)
                )

            final_item = make_white_transparent(final_item)


            # Ensure precise centering
            bbox_final = final_item.getbbox()
            if bbox_final:
                centered_item = Image.new("RGBA", (40, 40), (255, 255, 255, 0))
                paste_x = (40 - (bbox_final[2] - bbox_final[0])) // 2
                paste_y = (40 - (bbox_final[3] - bbox_final[1])) // 2
                centered_item.paste(final_item.crop(bbox_final), (paste_x, paste_y), final_item.crop(bbox_final))
                final_item = centered_item
            
            extracted_items.append(final_item)
    
    return extracted_items

def make_white_transparent(img):
    img = img.convert("RGBA")  # Convert to RGBA mode
    data = img.getdata()

    new_data = []
    for item in data:
        if item[0] == 255 and item[1] == 255 and item[2] == 255:  # Check if pixel is white
            new_data.append((255, 255, 255, 0))  # Set alpha to 0 for white pixels
        else:
            new_data.append(item)

    img.putdata(new_data)
    return img

def visualize_extracted_items(items):
    """
    Creates a stitched image of extracted items with spacing and a white background.
    
    :param items: List of extracted inventory item images.
    :return: Stitched image showing all extracted items for debugging.
    """
    cols = 4  # Display as 7 items per row
    rows = (len(items) + cols - 1) // cols  # Compute required rows
    spacing = 10  # Space between items
    
    output_width = cols * (40 + spacing) - spacing
    output_height = rows * (40 + spacing) - spacing
    stitched_image = Image.new("RGBA", (output_width, output_height), (255, 255, 255, 0))
    
    for idx, item in enumerate(items):
        row, col = divmod(idx, cols)
        x = col * (40 + spacing)
        y = row * (40 + spacing)
        stitched_image.paste(item, (x, y), item)
    
    stitched_image.show()
    #return stitched_image

def replace_color(image: Image, old_color, new_color):

    img = image.convert("RGB")  # Ensure image is in RGB mode
    pixels = img.load()

    width, height = img.size

    for x in range(width):
        for y in range(height):
            if pixels[x, y] == old_color:
                pixels[x, y] = new_color

    return img.convert("RGBA")
# Example usage
if __name__ == "__main__":
    input_image_path = "./inventory.png"
    output_dir = "./output"
    os.makedirs(output_dir, exist_ok=True)

    # Load image
    input_image = Image.open(input_image_path)

    # Extract slots
    inventory_slots = extract_osrs_items(input_image_path)
    visualize_extracted_items(inventory_slots)

    # Save slots
    for idx, slot in enumerate(inventory_slots):
        row = (idx // 4) + 1
        col = (idx % 4) + 1
        slot.save(f"{output_dir}/{row}_{col}.png")