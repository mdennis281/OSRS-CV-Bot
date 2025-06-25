"""
stack_ocr.py – isolate the red / yellow stack numbers that appear on
OldSchool RuneScape item icons and read them with Tesseract.

usage:
    from stack_ocr import read_stack
    print(read_stack("bank_icon.png"))       # -> '538'
    print(read_stack("inv_icon_red.png"))    # -> '45'
"""
from pathlib import Path
from typing  import Union

import numpy as np
from PIL import Image, ImageOps

from core import tools

import core.ocr.custom as ocr


# ────────────────────────────────────────────────────────── helpers ──
def _to_mask(img: Image.Image) -> Image.Image:
    """
    Convert `img` → monochrome bitmap (white digits, black bg).
    We key off the *exact* hues Jagex uses for stack numbers:
        ● yellow ≈ (R≥205 , G≥205 , B≤120)
        ●   red ≈ (R≥180 , G≤80  , B≤80)
    Anything else is discarded.
    """
    a = np.asarray(img.convert("RGB"))
    R, G, B = a[:,:,0], a[:,:,1], a[:,:,2]
    yellow = (R > 200) & (G > 200) & (B < 120)
    red    = (R > 180) & (G <  80) & (B <  80)
    mask   = yellow | red

    mono           = np.zeros_like(R, np.uint8)
    mono[mask]     = 255
    mono_pil       = Image.fromarray(mono, mode="L")

    # Upscale 4× with nearest-neighbour – it helps Tesseract a *lot*
    mono_pil = mono_pil.resize(
        (mono_pil.width * 4, mono_pil.height * 4),
        Image.NEAREST
    )
    # Add a solid border so Tesseract doesn’t clip numbers that touch an edge
    return ImageOps.expand(mono_pil, border=8, fill=0)


def read_stack(path_or_img: Union[str, Path, Image.Image]) -> str:
    """
    Return the stack size as a string (e.g. '60', '2009').
    Raises a ValueError if *nothing* is read.
    """
    img   = Image.open(path_or_img) if not isinstance(path_or_img, Image.Image) else path_or_img
    
    number_img = tools.mask_colors(img, [(255,255,0), (255,0,0)],  tolerance=10)
    # Single text-line mode; whitelist digits only
    txt = ocr.read_location_numbers(number_img)

    if not txt and txt != 0:
        raise ValueError("No digits recognised – Tesseract returned an empty string.")
    return int(txt)


def absorption_value(sc: Image.Image) -> str:
    """
    Return the stack size as a string (e.g. '60', '2009').
    Raises a ValueError if *nothing* is read.
    """

    abs_img = Image.open('data/ui/nmz_abs.png')

    match = tools.find_subimage(
        sc, abs_img, min_scale=0.9, max_scale=1.1
    )
    
    img = match.crop_in(sc)



    return read_stack(img)