from enum import Enum

class FontChoice(Enum):
    # modern
    RUNESCAPE_BARBARIAN_ASSAULT = "RuneScape Barbarian Assault"
    RUNESCAPE_BOLD_12 = "RuneScape Bold 12"
    RUNESCAPE_FAIRY_LARGE = "RuneScape Fairy Large"
    RUNESCAPE_FAIRY = "RuneScape Fairy"
    RUNESCAPE_PLAIN_11 = "RuneScape Plain 11"
    RUNESCAPE_PLAIN_12 = "RuneScape Plain 12"
    RUNESCAPE_QUILL_8 = "RuneScape Quill 8"
    RUNESCAPE_QUILL_CAPS = "RuneScape Quill Caps"
    RUNESCAPE_QUILL = "RuneScape Quill"
    # RUNESCAPE_SUROK intentionally omitted (no TTF present)
    
    # legacy (values match legacy TTF stems)
    RUNESCAPE = "osrs"
    RUNESCAPE_BOLD = "osrs_bold"
    RUNESCAPE_SMALL = "osrs_small"
    AUTO = "auto"   

# New canonical identifiers for all TTFs (existing ones treated as legacy)

class TessOem(Enum):
    TESSERACT_ONLY = 0
    LSTM_ONLY = 1
    TESSERACT_AND_LSTM = 2
    DEFAULT = 3

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