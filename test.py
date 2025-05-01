from core.osrs_client import RuneLiteClient, ToolplaneTab, MinimapElement
from core.tools import write_text_to_image
from core.input.mouse_control import ClickType
from core.tools import find_subimage, MatchResult
from core import ocr
from PIL import Image
import cv2
import time
rl_client = RuneLiteClient()

while True:
    sc = rl_client.get_screenshot()
    print(rl_client.toolplane.get_active_tab(sc))
    time.sleep(5)

#rl_client.click((200,200), click_type=ClickType.RIGHT)

#rl_client.choose_right_click_opt('Walk here')

#print(match)
#print(ans.size)

#match.debug_draw(ans,color=(255,255,0)).show()






# while True:

#     rl_client.debug_minimap()
    



# import pytesseract, os
# from PIL import Image
# import cv2
# import numpy as np

# from PIL import Image
# from enum import Enum

# class FontChoice(Enum):
#     RUNESCAPE = "runescape"
#     RUNESCAPE_BOLD = "runescape_bold"
#     RUNESCAPE_SMALL = "runescape_small"
#     AUTO = "auto"   

# def preprocess_help_text(pil_img: Image.Image) -> Image.Image:
#     # 1) crop 8 px on left for icon, 4 px margins elsewhere
#     w, h = pil_img.size
#     pil_img = pil_img.crop((8, 4, w-4, h-4))

#     # 2) PIL → OpenCV (BGR)
#     img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

#     # 3) upscale 3×
#     img = cv2.resize(img, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)

#     # 4) grayscale + adaptive threshold
#     gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
#     thr  = cv2.adaptiveThreshold(gray, 255,
#                                  cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
#                                  cv2.THRESH_BINARY, 31, 8)
#     return Image.fromarray(thr)

# # if you didn't copy it to tessdata, point TESSDATA_PREFIX here:
# os.environ['TESSDATA_PREFIX'] = r'C:\Users\Michael\projects\auto_rs\data\fonts\tesseract'

# img = Image.open('some_test_image.png')
# img = preprocess_help_text(img)
# text = pytesseract.image_to_string(
#     img,
#     lang='eng_best+osrs',
#     config='--oem 1 --psm 3 -c preserve_interword_spaces=1 '
# )
# print(text)


