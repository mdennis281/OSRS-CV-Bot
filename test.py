from core.osrs_client import RuneLiteClient, ToolplaneTab, MinimapElement
from core.tools import write_text_to_image
from core.input.mouse_control import ClickType
from core.tools import find_subimage, MatchResult, find_color_box, find_pixels_with_color
from core import ocr
from PIL import Image
import cv2
import time
rl_client = RuneLiteClient('')

find_color_box(rl_client.screenshot, (0,255,0),tol=20).debug_draw(rl_client.screenshot).show()

