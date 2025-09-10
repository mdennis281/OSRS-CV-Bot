"""
isolate the red / yellow / white stack numbers that appear on
OldSchool RuneScape item icons and read them with Tesseract.

usage:
    from stack_ocr import read_stack
    print(read_stack("bank_icon.png"))       # -> '538'
    print(read_stack("inv_icon_red.png"))    # -> '45'
"""
from pathlib import Path
from typing  import Union

from PIL import Image

from core import tools

import core.ocr.custom as ocr


def read_stack(path_or_img: Union[str, Path, Image.Image]) -> str:
    """
    Return the stack size as a string (e.g. '60', '2009').
    Raises a ValueError if *nothing* is read.
    """
    img   = Image.open(path_or_img) if not isinstance(path_or_img, Image.Image) else path_or_img
    
    number_img = tools.mask_colors(img, [(255,255,0), (255,0,0), (255,255,255)],  tolerance=10)
    # Single text-line mode; whitelist digits only
    txt = ocr.read_location_numbers(number_img)

    if not txt and txt != 0:
        raise ValueError("No digits recognised – Tesseract returned an empty string.")
    return int(txt)


def get_sack_img(sc: Image.Image) -> Image.Image:
    abs_img = Image.open('data/ui/plank-sack-state.png')

    match = tools.find_subimage(
        sc, abs_img, min_scale=0.9, max_scale=1.1
    )
    
    return match.crop_in(sc)

def plank_sack_cnt(sc: Image.Image) -> str:
    """
    Return the stack size as a string (e.g. '60', '2009').
    Raises a ValueError if *nothing* is read.
    """

    img = get_sack_img(sc)

    return read_stack(img)