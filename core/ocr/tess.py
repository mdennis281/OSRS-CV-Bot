import pytesseract
from PIL import Image
import cv2
import numpy as np
import os
import sys

from core.ocr.enums import TessOem, TessPsm, FontChoice

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

os.environ['TESSDATA_PREFIX'] = os.path.abspath('./data/fonts')
print(os.environ['TESSDATA_PREFIX'])

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
            raise ValueError("No digits recognised – Tesseract returned an empty string.")
        if not txt.isdigit():
            raise ValueError(f"Expected digits only, got: {txt}")
        if '.' in txt:
            return float(txt)

        return int(txt)
    except ValueError as e:
        print( e , f"txt: '{txt}'")
        raise e
    