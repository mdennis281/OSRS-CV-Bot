import cv2
import numpy as np
from pathlib import Path
from PIL import Image

# Threshold for "near white" (0–255). Pixels with all channels ≥ this are kept.
NEAR_WHITE_THRESHOLD = 180

def filter_near_white_to_transparent(input_path: Path, output_path: Path, threshold: int = NEAR_WHITE_THRESHOLD):
    """
    Open the image at input_path, keep only pixels that are near white, and
    make all other pixels fully transparent. Save the result to output_path.
    """
    # Load with PIL as RGB
    pil_img = Image.open(input_path).convert("RGB")
    rgb = np.array(pil_img)  # shape: (H, W, 3), in RGB order

    # Convert RGB → BGR for OpenCV
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

    # Build mask: True where B, G, and R channels are all ≥ threshold
    mask = (
        (bgr[:, :, 0] >= threshold) &
        (bgr[:, :, 1] >= threshold) &
        (bgr[:, :, 2] >= threshold)
    )

    # Convert BGR → RGBA (adds an alpha channel set to 255 for every pixel)
    rgba_full = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGBA)  # shape: (H, W, 4)

    # Prepare an output RGBA array initialized to fully transparent (all zeros)
    filtered_rgba = np.zeros_like(rgba_full)

    # Copy RGBA pixels from rgba_full wherever mask is True (these have alpha=255)
    filtered_rgba[mask] = rgba_full[mask]

    # Create a PIL image from the filtered array (mode="RGBA")
    result_img = Image.fromarray(filtered_rgba, mode="RGBA")

    # Save to output_path (PNG will preserve transparency)
    result_img.save(output_path)
    print(f"Saved filtered image to: {output_path}")

def main():
    # Directory where this script resides
    script_dir = Path(__file__).parent

    # Find all files ending with "_raw.png" in the same directory
    for raw_path in script_dir.glob("*_raw.png"):
        stem = raw_path.stem
        if not stem.endswith("_raw"):
            continue
        base_name = stem[:-len("_raw")]
        output_path = script_dir / f"{base_name}.png"
        filter_near_white_to_transparent(raw_path, output_path)

if __name__ == "__main__":
    main()
