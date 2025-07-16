from core.osrs_client import RuneLiteClient, ToolplaneTab
from core.bank import BankInterface
from core.item_db import ItemLookup
from core import tools
import threading
import time
import random
import keyboard
import pyautogui
from typing import List


client = RuneLiteClient()
db= ItemLookup()
bank = BankInterface(client,db)
BANK_TILE = (150,0,110) 
STALL_TILE = (255,100,20)
MIDDLE_TILE = (100,50,200)
DOOR_TILE = (200,100,100)
SLEEP_CHANCE = .005
SLEEP_RANGE = (25,60)
MAX_TIME_MIN = 180
terminate = False
OPEN_SLOTS = 28
SLEEP_BETWEEN_STEALS = (1, 2)

KEEP = ['Papaya Fruit', 'Strange Fruit', 'Golovanova fruit top']
DROP = [
    'Jangerberries','Strawberry','Cooking apple','Lemon',
    'Pineapple','Banana', 'Lime', 'Redberries',
    #'Silver ore', 'Silver bar','Tiara'
]
LAST = None

def main():

    threading.Thread(target=listen_for_escape, daemon=True).start()
    start = time.time()
    while steal(): continue
    print('Stealing complete.')
    #while not terminate:
        
    

def count_open_slots() -> int:
    matches = client.get_inv_items(KEEP,min_confidence=.97)
    return OPEN_SLOTS - len(matches)

def count_free_slots() -> int:
    matches = client.get_inv_items(DROP+KEEP,min_confidence=.97)
    return OPEN_SLOTS - len(matches)

def steal():
    """Steal from the stall."""
    global LAST
    if terminate: return
    time.sleep(random.uniform(1.5, 2.5))
    if count_free_slots() == 0:
        dropped = drop_items()
        if dropped == 0:
            if count_open_slots() == 0:
                return False
        else:
            LAST = None
    
    do_steal()
    
    return True

def do_steal():
    global LAST
    def is_in_hover() -> bool:
        hover = client.get_hover_text()
        for verb in ['steal','from','fruit','stall']:
            if verb in hover.lower():
                return True
        print(f'No verb match in: "{hover}"')
    def do_do_steal():
        global LAST
        ready = False
        for _ in range(5):
            if is_in_hover():
                ready = True
                break
            time.sleep(random.uniform(*SLEEP_BETWEEN_STEALS))
        if not ready:
            print('Rematchinsg stall tile...')
            LAST = None
            do_steal()
            # hopefully click walk here to ensure youre on the right tile
            time.sleep(random.uniform(.4,.6))
            client.click(LAST)
        client.click(
            LAST, 
            after_click_settle_chance=0,
            rand_move_chance=0
        )
    if not LAST:
        m = tools.find_color_box(client.get_screenshot(), STALL_TILE, tol=40)
        for _ in range(10):
            x,y = m.get_point_within()
            client.move_to((x,y))
            time.sleep(random.uniform(*SLEEP_BETWEEN_STEALS))
            if is_in_hover():
                LAST = (x,y)
                break
            if LAST: do_steal()
        if not LAST:
            raise RuntimeError('Failed to find stall tile for stealing.')
        
    do_do_steal()
                


def ensure_door_open():
    try:
        client.smart_click_tile(DOOR_TILE, 'open')
    except:
        print('door already open?')
    

def drop_items(items:List[str]=DROP) -> int:
    sort_keep()
    time.sleep(random.uniform(0.5, 1.5))
    client.move_off_window()
    matches = client.get_inv_items(items,min_confidence=.97)
    if matches:
        try:
            keyboard.press('shift')
            for match in matches:
                if terminate: return
                client.click(
                    match, 
                    after_click_settle_chance=0,
                    rand_move_chance=0
                )
        finally:
            keyboard.release('shift')
    return len(matches)


def sort_keep():
    keep_matches = client.get_inv_items(KEEP, min_confidence=.97)
    drop_matches = client.get_inv_items(DROP, min_confidence=.97)

    # Sort keep matches bottom-right first, and drop matches top-left first
    keep_matches.sort(key=lambda m: (-m.start_y, -m.start_x))
    drop_matches.sort(key=lambda m: (m.start_y, m.start_x))

    # Iterate through keep matches and swap with drop matches above or to the left
    for keep_match in keep_matches:
        for drop_match in drop_matches:
            # Ensure drop is either above or in the same row but to the left
            if drop_match.start_y < keep_match.start_y or (
                drop_match.start_y == keep_match.start_y and drop_match.start_x < keep_match.start_x
            ):
                swap_items(keep_match, drop_match)
                drop_matches.remove(drop_match)  # Remove swapped drop match
                break


def swap_items(m1: tools.MatchResult, m2: tools.MatchResult):
    """Swap two items in the inventory."""
    if not m1 or not m2:
        print("Invalid matches for swapping.")
        return
    
    try:
        client.move_to(m1.get_point_within())
        time.sleep(random.uniform(0.1, 0.3))
        pyautogui.mouseDown(button='left')
        time.sleep(random.uniform(0.1, 0.3))
        client.move_to(m2.get_center(), rand_move_chance=0)
        time.sleep(random.uniform(0.1, 0.3))
    finally:
        pyautogui.mouseUp(button='left')













def do_bank():
    client.smart_click_tile(BANK_TILE,'bank',retry_match=5)
    while client.is_moving(): continue
    bank.deposit_inv()
    bank.withdraw('Steel bar',-1)
    client.move_off_window()
    bank.close()
    

def do_smith():
    
    client.smart_click_tile(FURNACE_TILE, 'furnace', retry_match=5)
    while client.is_moving(): continue
    keyboard.press('space')
    client.move_off_window()
    time.sleep(random.uniform(3,7))
    while client.makin_cannonballs: continue

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