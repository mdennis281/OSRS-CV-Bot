import pytesseract
from PIL import Image
import cv2
import numpy as np
import os
import sys
from typing import List, Tuple, Optional

from core.ocr.enums import TessOem, TessPsm, FontChoice

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

os.environ['TESSDATA_PREFIX'] = os.path.abspath('./data/fonts')

def _preprocess(pil_img: Image.Image) -> Image.Image:

    # 2) PIL → OpenCV (BGR)
    img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

    # 3) upscale 3×
    img = cv2.resize(img, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)

    # 4) grayscale + adaptive threshold
    #gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # thr  = cv2.adaptiveThreshold(gray, 255,
    #     cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
    #     cv2.THRESH_BINARY, 31, 8)
    return Image.fromarray(img)



def execute(
        img: Image.Image,
        font: FontChoice = FontChoice.AUTO,
        oem: TessOem = TessOem.DEFAULT,
        psm: TessPsm = TessPsm.SINGLE_LINE,
        preprocess: bool = True,
        characters: str = None
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


    ans = pytesseract.image_to_string(img, lang=lang, config=config).strip()
    if not ans:
        print(f"lang: {lang}, config: {config}")
        img.show()
    return ans


def find_string_bounds(
    img: Image.Image,
    string_to_search: str,
    *,
    lang: str = "eng",
    psm: int = 6,
    confidence_threshold: int = 40,
    preprocess: bool = True,
    case_sensitive: bool = False,
) -> Optional[dict]:
    """
    Locate `string_to_search` in the supplied image.

    Parameters
    ----------
    img : PIL.Image
    string_to_search : str
        Text to find – exact substring match (spaces allowed).
    lang : str
        Tesseract language(s) to use (e.g. "eng", "osd", "runescape+eng", …).
    psm : int
        Page-Seg mode (6 = assume a single uniform block of text).
    confidence_threshold : int
        Ignore words whose individual confidence < this value.
    case_sensitive : bool
        If False (default) both OCR output and search string are lower-cased.

    Returns
    -------
    MatchResult or None
        Bounding rectangle around the whole match.
        None if the string is not found.
    """
    if preprocess:
        img = _preprocess(img)

    cfg = f"--psm {psm}"

    data = pytesseract.image_to_data(
        img,
        lang=lang,
        config=cfg,
        output_type=pytesseract.Output.DICT,
    )

    # ── Step 1: group OCR output into per-line lists ──────────────────────────
    n = len(data["text"])
    lines: dict[Tuple[int, int, int], List[int]] = {}
    for i in range(n):
        if int(data["conf"][i]) < confidence_threshold or not data["text"][i].strip():
            continue
        key = (data["page_num"][i], data["block_num"][i], data["line_num"][i])
        lines.setdefault(key, []).append(i)

    # ── Step 2: search each line for the target substring ─────────────────────
    target = string_to_search if case_sensitive else string_to_search.lower()

    for idxs in lines.values():
        # sort by word position
        idxs.sort(key=lambda i: data["word_num"][i])
        words = [data["text"][i] for i in idxs]
        if not case_sensitive:
            words_low = [w.lower() for w in words]
        else:
            words_low = words

        joined = " ".join(words_low)
        start_pos = joined.find(target)
        if start_pos == -1:
            continue

        # Figure out which *words* participate in the match
        # Build a map of char index → word index
        char_map: List[int] = []
        for w_i, word in enumerate(words_low):
            char_map.extend([w_i] * (len(word) + 1))  # +1 for the space
        # slice corresponding part
        involved_word_idxs = set(
            char_map[start_pos : start_pos + len(target)]
        )

        # Bounding box union across those words
        xs, ys, xe, ye, confs = [], [], [], [], []
        for i in involved_word_idxs:
            j = idxs[i]
            xs.append(data["left"][j])
            ys.append(data["top"][j])
            xe.append(data["left"][j] + data["width"][j])
            ye.append(data["top"][j] + data["height"][j])
            confs.append(int(data["conf"][j]))
        scale = 3 if preprocess else 1
        return {
            'x1': int(min(xs)/scale),
            'y1': int(min(ys)/scale),
            'x2': int(max(xe)/scale),
            'y2': int(max(ye)/scale),
            'confidence': float(np.mean(confs))/100
        }

    return None  # not found


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

