from PIL import Image
import cv2
import numpy as np

def extract_inventory_from_image(image: Image.Image) -> Image.Image:
    """
    Extracts the OSRS inventory section from a given PIL Image.

    Args:
        image (Image.Image): Input image as a PIL Image.

    Returns:
        Image.Image: Cropped inventory image as a PIL Image, or None if extraction fails.
    """
    # Convert PIL image to OpenCV format (numpy array)
    image_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

    # Convert to RGB for color comparison
    image_rgb = cv2.cvtColor(image_cv, cv2.COLOR_BGR2RGB)

    # Define the target inventory background color in RGB (converted from #3e3529)
    target_color = np.array([62, 53, 41])

    # Define a threshold for color similarity
    threshold = .1

    # Create a mask for color matching
    color_diff = np.abs(image_rgb - target_color)
    print(color_diff)

    mask = np.all(color_diff < threshold, axis=-1).astype(np.uint8) * 255
    # Find contours in the mask
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        # Find the best-matching rectangular contour
        possible_inventories = [
            cv2.boundingRect(contour) for contour in contours if cv2.contourArea(contour) > 5000
        ]

        if possible_inventories:
            # Select the largest detected region (assuming it's the inventory)
            x, y, w, h = max(possible_inventories, key=lambda b: b[2] * b[3])

            # Extract the inventory area
            inventory_crop = image_cv[y:y+h, x:x+w]

            # Convert back to PIL format
            return Image.fromarray(cv2.cvtColor(inventory_crop, cv2.COLOR_BGR2RGB))

    return None


if __name__ == "__main__":
    # Load an example screenshot
    example_screenshot = Image.open("./runelite_screenshot.png")

    # Extract the inventory section
    inventory_image = extract_inventory_from_image(example_screenshot)

    if inventory_image:
        inventory_image.save('inventory.png')
    else:
        print("Inventory extraction failed.")