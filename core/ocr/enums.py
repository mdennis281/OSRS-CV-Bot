from enum import Enum

class FontChoice(Enum):
    RUNESCAPE = "osrs"
    RUNESCAPE_BOLD = "osrs_bold"
    RUNESCAPE_SMALL = "osrs_small"
    AUTO = "auto"   

class TessOem(Enum):
    TESSERACT_ONLY = 0
    LSTM_ONLY = 1
    TESSERACT_AND_LSTM = 2
    DEFAULT = 3

class TessPsm(Enum):
    SINGLE_COLUMN = 1
    SINGLE_BLOCK_VERT_TEXT = 2
    SINGLE_LINE = 3
    SINGLE_WORD = 4
    CIRCLE_WORD = 5
    SINGLE_CHAR = 6
    SPARSE_TEXT = 7
    SPARSE_TEXT_OSD = 8
    RAW_LINE = 9
    COUNT = 10

class TessPsm(Enum):
    """Page Segmentation Mode (layout analysis strategy)."""
    OSD_ONLY                       = 0   # Orientation & script detection, no OCR
    AUTO_OSD                       = 1   # Automatic layout + OSD
    AUTO_NO_OSD                    = 2   # Layout, but no OSD (rarely used)
    AUTO                           = 3   # Fully automatic page segmentation  ← default
    SINGLE_COLUMN                  = 4   # One column of text, ragged right
    SINGLE_BLOCK_VERT_TEXT         = 5   # Vertical block (Asian)
    SINGLE_BLOCK                    = 6   # Uniform block of text (screenshots, code)
    SINGLE_LINE                    = 7   # Exactly one text line
    SINGLE_WORD                    = 8   # One word
    CIRCLE_WORD                    = 9   # Word in a circle (e.g. logo)
    SINGLE_CHAR                    = 10  # One character (or box file training)
    SPARSE_TEXT                    = 11  # Sparse text, no order
    SPARSE_TEXT_OSD                = 12  # Sparse text with OSD
    RAW_LINE                       = 13  # Single line, no interpretation (fast)