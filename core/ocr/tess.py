import pytesseract
from PIL import Image, ImageFilter
import cv2
import numpy as np
import os
import sys
import shutil
import re
from typing import List, Tuple, Optional, Dict
from difflib import SequenceMatcher
from core.ocr.enums import TessOem, TessPsm, FontChoice

# Set Tesseract command path per OS
if sys.platform.startswith('win'):
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
else:
    # On Linux/macOS assume 'tesseract' is in PATH or default install dir
    pytesseract.pytesseract.tesseract_cmd = shutil.which('tesseract') or 'tesseract'

os.environ['TESSDATA_PREFIX'] = os.path.abspath('./data/fonts')

def _preprocess(pil_img: Image.Image) -> Image.Image:
    """Upscale & grayscale (no binarization)."""
    img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    img = cv2.resize(img, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    img = Image.fromarray(gray)
    return img.filter(ImageFilter.UnsharpMask(radius=2, percent=200))

            

def execute(
        img: Image.Image,
        font: FontChoice = FontChoice.AUTO,
        oem: TessOem = TessOem.DEFAULT,
        psm: TessPsm = TessPsm.SINGLE_LINE,
        preprocess: bool = True,
        characters: str = None,
        raise_on_blank = True
    ) -> str:
    """
    Run Tesseract on `img` and return the text it found.
    """
    lang = ""
    if font == FontChoice.AUTO:
        lang += f'{FontChoice.RUNESCAPE.value}'
        lang += f'+{FontChoice.RUNESCAPE_BOLD.value}'
        lang += f"+{FontChoice.RUNESCAPE_SMALL.value}"
    else:
        lang += f"{font.value}"

    if preprocess:
        img = _preprocess(img)
        
    config = f'--oem {oem.value} --psm {psm.value}'
    if characters is not None:
        config += f' -c tessedit_char_whitelist={characters}'

    
    ans = pytesseract.image_to_string(
        img, 
        lang=lang, 
        config=config,
        timeout=5
    ).strip()
    if not ans and raise_on_blank:
        print(f"lang: {lang}, config: {config}")
        img.show()
        raise ValueError('OCR yielded no characters')
    return ans


def find_string_bounds(
    img: Image.Image,
    string_to_search: str,
    *,
    lang: str = "eng",
    psm: int = 6,
    preprocess: bool = True,
    case_sensitive: bool = False,
    margin: int = 0,
) -> Optional[Dict[str, float]]:
    """
    Locate the closest match to `string_to_search` in the image,
    returning its bounding box and a difflib-based “confidence” score
    between 0.0 and 1.0.
    """
    if preprocess:
        img = _preprocess(img)

    cfg = f"--psm {psm}"
    data = pytesseract.image_to_data(
        img, lang=lang, 
        config=cfg, 
        output_type=pytesseract.Output.DICT, 
        timeout=5
        )

    # Group words by line
    n = len(data["text"])
    lines: Dict[Tuple[int,int,int], List[int]] = {}
    for i in range(n):
        txt = data["text"][i].strip()
        if not txt:
            continue
        key = (data["page_num"][i], data["block_num"][i], data["line_num"][i])
        lines.setdefault(key, []).append(i)

    # Prepare target
    target = string_to_search if case_sensitive else string_to_search.lower()
    # we'll compare on stripped words
    targ_words = re.findall(r"\w+['-]?\w*|\w", target)
    if not case_sensitive:
        targ_words = [w.lower() for w in targ_words]
    target_joined = " ".join(targ_words)

    best_score = -1.0
    best_box = None

    # Scan every line / every window of the right size
    for idxs in lines.values():
        idxs.sort(key=lambda i: data["word_num"][i])
        words = [data["text"][i] for i in idxs]
        words_cmp = [w if case_sensitive else w.lower() for w in words]
        # strip punctuation for fair comparison
        words_stripped = [re.sub(r"[^\w'-]", "", w) for w in words_cmp]

        L = len(targ_words)
        # if fewer words in line than target, skip
        if len(words_stripped) < L:
            continue

        # slide window of length L
        for start in range(len(words_stripped) - L + 1):
            window = words_stripped[start:start+L]
            candidate = " ".join(window)
            score = SequenceMatcher(None, candidate, target_joined).ratio()
            if score <= best_score:
                continue

            # compute bounding box for this window
            xs, ys, xe, ye = [], [], [], []
            for widx in range(start, start+L):
                i = idxs[widx]
                x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
                xs.append(x); ys.append(y)
                xe.append(x + w); ye.append(y + h)

            scale = 3 if preprocess else 1
            x1 = min(xs)/scale - margin
            y1 = min(ys)/scale - margin
            x2 = max(xe)/scale + margin
            y2 = max(ye)/scale + margin

            best_score = score
            best_box = {
                "x1": int(max(x1, 0)),
                "y1": int(max(y1, 0)),
                "x2": int(x2),
                "y2": int(y2),
                "confidence": float(score),
            }

    print(f"best_box: {best_box}")
    return best_box


def get_number(img: Image.Image, font: FontChoice = FontChoice.AUTO, preprocess:bool=True) -> str:
    """
    Return the number as a string (e.g. '60', '2009').
    Raises a ValueError if *nothing* is read.
    """
    # Single text-line mode; whitelist digits only
    txt = execute(
        img, font=font, 
        psm=TessPsm.SINGLE_LINE, 
        characters="0123456789.",
        preprocess=preprocess
    )
    try:
        
        if not txt:
            raise OcrError("No digits recognised – Tesseract returned an empty string.", img)
        if not txt.isdigit():
            raise OcrError(f"Expected digits only, got: {txt}", img)
        if '.' in txt:
            return float(txt)

        return int(txt)
    except ValueError as e:
        print( e , f"txt: '{txt}'")
        raise e
    
class OcrError(Exception):
    """Base class for OCR errors."""
    def __init__(self, message: str, image: Image.Image = None):
        super().__init__(message)
        self.image = image

