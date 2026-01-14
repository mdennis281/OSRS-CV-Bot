from __future__ import annotations
from core.osrs_client import RuneLiteClient, ToolplaneTab, MinimapElement
from core.bank import BankInterface
from core.tools import write_text_to_image
from core.input.mouse_control import ClickType
from bots.core.cfg_types import RouteParam, WaypointParam
from core.item_db import ItemLookup
from core.tools import find_subimage, MatchResult, find_color_box
from core import ocr
import threading
import keyboard
from PIL import Image
import cv2
import time
from core.bot import Bot
from core.logger import get_logger

log = get_logger('test')
bot = Bot()

print(bot.bank.get_settings())
bot.bank.set_default_quantity(10)
bot.bank.set_default_quantity(14)
bot.bank.set_withdraw_setting('Note')
bot.bank.withdraw('Uncut diamond',14)
# route = RouteParam([
#     WaypointParam(3161,3477,0,809394,10)
#     # WaypointParam(2956,3231,0,756115,10),
#     # WaypointParam(2959,3268,0,756120,10),
#     # WaypointParam(3001,3299,0,768412,10),
#     # WaypointParam(3038,3255,0,776598,10),
#     # WaypointParam(3014,3213,0,770449,10),
#     # WaypointParam(2990,3178,0,764301,10)
# ])

# bot.mover.execute_route(route)

#bot.bank.withdraw('Grimy Marrentill', -1)
# for x in range(5):
#     bot.mover.set_minimap_zoom(x+1)
#     print(f'zoom {x+1}')
#     time.sleep(1)

# for x in reversed(range(5)):
#     bot.mover.set_minimap_zoom(x+1)
#     print(f'zoom {x+1}')
#     time.sleep(1)

#bot.client.get_filtered_screenshot().show()
# print(client.is_moving())
# # bank.deposit_inv()
# # bank.withdraw('Iron ore',14)
# # bank.withdraw('Coal',14)

# print(client.is_cooking)

# for x in range(28):
#     print('takin da talizmanz: ',x+1)
#     bank.deposit_inv()
#     bank.withdraw('Air talisman',x+1)

terminate = False


# il = ItemLookup()
# #il.get_item_by_name('Nature rune').icon.show()
# il.get_item_by_id(8783).icon.show()

# client.get_position()




def find_box_tiles():
    tiles = [(0,255,100)]
    sc = client.get_screenshot()
    result = client.get_screenshot()
    for tile in tiles:
        box = find_color_box(sc, tile, tol=30)
        result = box.debug_draw(result, color='orange')
    result.show()
        

#find_box_tiles()

def main():
    threading.Thread(target=listen_for_escape, daemon=True).start()
    while not terminate:
        print(f'moving: {client.is_moving}')
        #time.sleep(2)




def listen_for_escape():
    """Thread function to listen for the Esc key."""
    global terminate
    while True:
        if keyboard.is_pressed('esc'):
            print("Terminating...")
            terminate = True
            return
        time.sleep(0.1)

#main()