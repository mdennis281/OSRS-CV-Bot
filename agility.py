from __future__ import annotations
from core.osrs_client import RuneLiteClient, ToolplaneTab, MinimapElement
from core.tools import write_text_to_image
from core.input.mouse_control import ClickType
from core.item_db import ItemLookup
from core.tools import find_subimage, MatchResult, find_color_box
from core import tools
from core import ocr
import threading
import keyboard
from PIL import Image
import random
import cv2
import time
client = RuneLiteClient('')

terminate = False

# NEED BETTER AGILITY PLUGIN
# NEED WORLD LOCATION PLUGIN (youll get an error about it with more info)
# (it's just the improved version)
# change opacity to 100% in settings
# the colors below are (Red, Green, Blue)

# NOTE: zoom out camera and ensure hover text is
# outside of the viewport thing
NEXT = (0,255,100)
STOP = (255,0,50)
GRACE = (255,0,255)
ACTIONS = [
    'jump', 'climb', 'vault', 'gap', 'cross', 
    'rope','wall','-up', 'grab', 'leap',
    'cross', 'monkey', '-on', 'hurdle'
]
FAIL_MAX = 10
SLEEP_CHANCE = .005
SLEEP_RANGE = (25,60)
MAX_TIME_MIN = 180


def main():
    threading.Thread(target=listen_for_escape, daemon=True).start()
    start = time.time()
    fails = 0
    while not terminate:
        timeout_check(start)
        action = click_tile(NEXT, ACTIONS)
        if action:
            fails = 0
            propose_break()
            continue
        else:
            fails += 1
            if fails % 2 == 0:
                client.move_off_window()
            if fails > FAIL_MAX: 
                print('shit is broke. PEACE')
                break
            time.sleep(1)
            
        click_tile(GRACE, ['take','grace'])
        



def click_tile(tile_color, action):
    box = None
    try: 
        box = find_color_box(client.get_screenshot(), tile_color, tol=40)
    except: 
        print(f"Failed to find tile {tile_color}")
        return False
    try:
        client.smart_click_match(
            box, action,
            retry_hover=3,
            center_point=True,
            center_point_variance=10
        )
        client.move_to(client.window_match)
    except Exception as e:
        
        print(f"Failed to click {action} on tile {tile_color}, {e}")
        return False
    
    while client.is_moving(): continue
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


def timeout_check(start):
    runtime = time.time() - start
    if runtime/60 > MAX_TIME_MIN:
        raise RuntimeError('MAX TIME LIMIT EXCEEDED')

def propose_break():
    if random.random() < SLEEP_CHANCE:
        t = random.randint(*SLEEP_RANGE)
        print(f'sleeping for {tools.seconds_to_hms(t)}')
        client.move_off_window()
        time.sleep(t)
main()



