from __future__ import annotations
from core.osrs_client import RuneLiteClient, ToolplaneTab, MinimapElement
from core.tools import write_text_to_image
from core.input.mouse_control import ClickType
from core.item_db import ItemLookup
from core.tools import find_subimage, MatchResult, find_color_box
from core import ocr
import threading
import keyboard
from PIL import Image
import random
import cv2
import time
client = RuneLiteClient('')

terminate = False

NEXT = (0,255,100)
STOP = (255,0,50)
GRACE = (255,0,255)
ACTIONS = ['jump', 'climb', 'vault', 'gap', 'tree', 'cross', 'rope','wall','-up']

# il = ItemLookup()
# #il.get_item_by_name('Nature rune').icon.show()
# il.get_item_by_id(8783).icon.show()

# MOG Take
def main():
    threading.Thread(target=listen_for_escape, daemon=True).start()
    fails = 0
    while not terminate:
        action = click_tile(NEXT, ACTIONS)
        if action:
            fails = 0
            continue
        else:
            fails += 1
            if fails > 10: 
                print('shit is broke. PEACE')
                break
            time.sleep(1)
            
        click_tile(GRACE, 'take')
        



def click_tile(tile_color, action):
    box = None
    try: 
        box = find_color_box(client.get_screenshot(), tile_color, tol=40)
        # really just to verify we arent moving
        time.sleep(.8)
        box2 = find_color_box(client.get_screenshot(), tile_color, tol=40)
        if not box.find_overlap(box2):
            print('WE ARE MOVING, DELAYING ACTIONS')
            time.sleep(2)
            return False

        
    except: 
        print(f"Failed to find tile {tile_color}")
        return False
    try:
        client.smart_click_match(
            box, action,
            retry_hover=3
        )
    except Exception as e:
        
        print(f"Failed to click {action} on tile {tile_color}, {e}")
        return False
    time.sleep(random.uniform(4,6))
    return True

def listen_for_escape():
    """Thread function to listen for the Esc key."""
    global terminate
    while True:
        if keyboard.is_pressed('esc'):
            print("Terminating...")
            terminate = True
            return
        time.sleep(0.1)
main()



