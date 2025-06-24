import base64
import io
import cv2
import numpy as np
from PIL import Image
from data.fonts.location_numbers import digit_templates
from core.tools import find_subimages, find_subimage
from typing import Dict, List, Tuple
from core.region_match import MatchResult

# Cache for digit templates to avoid reloading
_DIGIT_TEMPLATE_CACHE = None

def _load_digit_templates() -> Dict[str, Image.Image]:
    """Load digit templates from base64 encodings (cached)."""
    global _DIGIT_TEMPLATE_CACHE
    
    if _DIGIT_TEMPLATE_CACHE is None:
        _DIGIT_TEMPLATE_CACHE = {}
        for digit, b64_data in digit_templates.items():
            try:
                # Decode base64 to binary data
                image_bytes = base64.b64decode(b64_data)
                # Create an in-memory file-like object
                image_file = io.BytesIO(image_bytes)
                # Open and fully load the image immediately
                template = Image.open(image_file)
                template.load()  # Ensure image is fully loaded
                # Store the template in cache
                _DIGIT_TEMPLATE_CACHE[digit] = template
            except Exception as e:
                print(f"Error loading template for digit '{digit}': {e}")
                continue
    
    return _DIGIT_TEMPLATE_CACHE

def _match_digit(parent: Image.Image, template: Image.Image, digit: str) -> List[Tuple[str, MatchResult]]:
    """Match a single digit template against an image, with error handling."""
    matches = []
    try:
        # Manual template matching to avoid the PIL assertion error
        parent_np = np.array(parent.convert('L'))
        template_np = np.array(template.convert('L'))
        
        # Get template dimensions
        h, w = template_np.shape
        
        # Ensure template fits in parent
        if h > parent_np.shape[0] or w > parent_np.shape[1]:
            return []
            
        # Perform template matching using OpenCV directly
        result = cv2.matchTemplate(parent_np, template_np, cv2.TM_CCORR_NORMED)
        
        # Find all matches above threshold
        threshold = 0.98
        locations = np.where(result >= threshold)
        
        for pt in zip(*locations[::-1]):  # Switch columns and rows
            match_result = MatchResult(
                start_x=pt[0],
                start_y=pt[1],
                end_x=pt[0] + w,
                end_y=pt[1] + h,
                confidence=result[pt[1], pt[0]],
                scale=1.0
            )
            matches.append((digit, match_result))
            
    except Exception as e:
        print(f"Error matching digit '{digit}': {e}")
        
    return matches

def read_location_numbers(image: Image.Image) -> str:
    """
    Extract numerical text from images like coordinate displays.
    Uses predefined digit templates for matching.
    
    Args:
        image: PIL Image containing numerical text
        
    Returns:
        Recognized text as a string
    """
    templates = _load_digit_templates()
    if not templates:
        return ""
    
    # Convert image to grayscale to improve matching
    image = image.convert('L').convert('RGB')
    
    # Find matches for all digits - use a static copy of the templates to prevent dictionary changes during iteration
    all_matches = []
    template_items = list(templates.items())  # Create a static copy of items
    
    for digit, template in template_items:
        if template is not None:  # Additional safety check
            matches = _match_digit(image, template, digit)
            all_matches.extend(matches)
    
    # Filter out overlapping matches by keeping highest confidence
    all_matches.sort(key=lambda x: x[1].confidence, reverse=True)
    kept_matches = []
    
    for digit, match in all_matches:
        should_keep = True
        for _, kept_match in kept_matches:
            # Check for significant overlap
            overlap_x = max(0, min(match.end_x, kept_match.end_x) - 
                           max(match.start_x, kept_match.start_x))
            overlap_y = max(0, min(match.end_y, kept_match.end_y) - 
                           max(match.start_y, kept_match.start_y))
            
            if overlap_x > 0 and overlap_y > 0:
                match_width = match.end_x - match.start_x
                match_height = match.end_y - match.start_y
                overlap_area = overlap_x * overlap_y
                match_area = match_width * match_height
                
                if overlap_area / match_area > 0.25:  # 25% overlap threshold
                    should_keep = False
                    break
        
        if should_keep:
            kept_matches.append((digit, match))
    
    # Sort by x-coordinate to get correct reading order
    kept_matches.sort(key=lambda x: x[1].start_x)
    
    # Build final result string
    result = ''.join(digit for digit, _ in kept_matches)
    return result
