import cv2
import numpy as np
from pathlib import Path
from PIL import Image

# Threshold for "almost black" (0–255). Pixels with all channels ≤ this will be made transparent.
ALMOST_BLACK_THRESHOLD = 10

def convert_almost_black_to_transparent(input_path: Path, output_path: Path, threshold: int = ALMOST_BLACK_THRESHOLD):
    """
    Open the image at input_path, make every pixel whose RGB values are all ≤ threshold
    fully transparent, and keep all other pixels unchanged. Save the result to output_path.
    """
    # Load with PIL as RGB
    pil_img = Image.open(input_path).convert("RGB")
    rgb = np.array(pil_img)  # shape: (H, W, 3) in RGB order

    # Convert RGB → BGR for cv2
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

    # Convert BGR → BGRA (adds an alpha channel set to 255)
    bgra_full = cv2.cvtColor(bgr, cv2.COLOR_BGR2BGRA)  # shape: (H, W, 4)

    # Build mask: True where B, G, and R channels are all ≤ threshold (i.e., "almost black")
    black_mask = (
        (bgr[:, :, 0] <= threshold) &
        (bgr[:, :, 1] <= threshold) &
        (bgr[:, :, 2] <= threshold)
    )

    # Wherever mask is True, set alpha channel to 0; else leave alpha at 255
    bgra_full[:, :, 3][black_mask] = 0

    # Convert BGRA → RGBA for saving with PIL
    rgba_result = cv2.cvtColor(bgra_full, cv2.COLOR_BGRA2RGBA)
    result_img = Image.fromarray(rgba_result, mode="RGBA")

    # Save to output_path (PNG preserves transparency)
    result_img.save(output_path)
    print(f"Saved converted image to: {output_path}")

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
        convert_almost_black_to_transparent(raw_path, output_path)

if __name__ == "__main__":
    main()
