from core.osrs_client import RuneLiteClient, ToolplaneTab
from PIL import Image
from core import tools
import time
import random
import threading
import keyboard

ITEM_TO_ALCH = 1396 # water battlestaff (noted)
client = RuneLiteClient('')

CHANCE_CHANGE_POINT = .01
CHANCE_REST = 0#.008
REST_RANGE = (5,35)
PAUSED = False
# interval to check that alch is done (makes it more human)
TAB_CHECK_RANGE = (.5,1.75)

terminate = False

def main():
    start_time = time.time()
    nattys, items = init(ITEM_TO_ALCH)

    print(f'Found: {nattys} nattys & {items} items')
    alch_count = min(nattys,items)
    print(f'Alching {alch_count} times')

    overlap_match = get_overlap(ITEM_TO_ALCH)

    # prob already there but sanity check
    client.click_toolplane(ToolplaneTab.SPELLS)

    try:
        overlap_point = overlap_match.get_point_within()
    except AttributeError as e:
        raise RuntimeError('Make sure the item and high alch are on top of each other')


    for i in range(alch_count):
        while get_active_tab() != 'spells':
            time.sleep(random.uniform(*TAB_CHECK_RANGE))
            if terminate: return
        if terminate: return
        client.click(
            overlap_point, click_cnt=2, 
            rand_move_chance=0, 
            after_click_settle_chance=0
        )
        


        if random.random() < CHANCE_CHANGE_POINT:
            overlap_point = overlap_match.get_point_within()
            print(f'Changed click point: {overlap_point}')
        
        alched = alch_count-(i+1)
        if not alched % 10:
            print(f'Remaining items: {alched}')
        
        if random.random() < CHANCE_REST:
            rest_sec = random.randint(*REST_RANGE)
            print(f'Resting for {rest_sec}s')
            client.move_off_window()
            overlap_point = overlap_match.get_point_within()
            time.sleep(rest_sec)
        do_pause()
    duration = tools.seconds_to_hms(time.time() - start_time)
    
    print(f'All done. Alched {alch_count} items in {duration}')


def do_pause():
    while PAUSED:
        time.sleep(1)


    
def get_active_tab() -> ToolplaneTab:
    tab = client.toolplane.get_active_tab(client.get_screenshot())
    return tab

def get_overlap(identifier):
    item_match = client.find_item(identifier, min_confidence=.9)

    client.click_toolplane(ToolplaneTab.SPELLS)

    alch_img = Image.open('data/spells/high-level-alchemy.png')

    alch_match = client.find_in_window(alch_img)

    return alch_match.find_overlap(item_match)

def init(identifier):
    # TODO fix whatever tf is going on here
    natty_count = client.get_item_cnt('Nature rune',min_confidence=.9)
    item_count = client.get_item_cnt(identifier, min_confidence=.9)
    
    threading.Thread(target=listen_for_escape, daemon=True).start()
    threading.Thread(target=listen_for_pause, daemon=True).start()

    return natty_count, item_count

def listen_for_pause():
    global PAUSED
    while True:
        if keyboard.is_pressed('`'):
            
            PAUSED = not PAUSED
            print('PAUSED' if PAUSED else 'UNPAUSED')
        time.sleep(0.1)

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


