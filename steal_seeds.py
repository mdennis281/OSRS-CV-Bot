
from core.osrs_client import RuneLiteClient, ToolplaneTab
from core.bank import BankInterface
from core.item_db import ItemLookup
from core import tools
import threading
import time
import random
import keyboard
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
SLEEP_BETWEEN_STEALS = (1,3)#(0.3, 0.5)

KEEP = []#['Papaya Fruit', 'Strange Fruit', 'Golovanova fruit top']
DROP = [
    # 'Jangerberries','Strawberry','Cooking apple','Lemon',
    # 'Pineapple','Banana', 'Lime', 'Redberries',
    'Silver ore', 'Silver bar','Tiara'
]
LAST = None

def main():

    threading.Thread(target=listen_for_escape, daemon=True).start()
    start = time.time()
    while not terminate:
        while steal(): continue
    

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
    do_steal()
    time.sleep(random.uniform(1.5, 2.5))
    if random.random() < .005: LAST = None

def do_steal():
    global LAST
    def is_in_hover() -> bool:
        hover = client.get_hover_text()
        for verb in ['steal','from','seed','stall']:
            if verb in hover.lower():
                return True
        print(f'No verb match in: "{hover}"')
    if not LAST:
        m = tools.find_color_box(client.get_screenshot(), STALL_TILE, tol=40)
        for _ in range(5):
            x,y = m.get_point_within()
            client.move_to((x,y))
            time.sleep(random.uniform(*SLEEP_BETWEEN_STEALS))
            if is_in_hover():
                LAST = (x,y)
                break
            if LAST: do_steal()
        if not LAST:
            raise RuntimeError('Failed to find stall tile for stealing.')
    else:
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
                


def ensure_door_open():
    try:
        client.smart_click_tile(DOOR_TILE, 'open')
    except:
        print('door already open?')
    

def drop_items(items:List[str]=DROP) -> int:
    
    keyboard.press('shift')
    try:
        matches = client.get_inv_items(items,min_confidence=.97)
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