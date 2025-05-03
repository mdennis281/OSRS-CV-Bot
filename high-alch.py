from core.osrs_client import RuneLiteClient, ToolplaneTab
from PIL import Image
import time
import random
import threading
import keyboard

ITEM_TO_ALCH = 1396 # water battlestaff (noted)
client = RuneLiteClient('')

CHANCE_CHANGE_POINT = .01
CHANCE_REST = .008
REST_RANGE = (5,35)

# interval to check that alch is done (makes it more human)
TAB_CHECK_RANGE = (.5,1.75)

terminate = False

def main():
    nattys, items = init(ITEM_TO_ALCH)

    print(f'Found: {nattys} nattys & {items} items')
    alch_count = min(nattys,items)
    print(f'Alching {alch_count} times')

    overlap_match = get_overlap(ITEM_TO_ALCH)

    # prob already there but sanity check
    client.click_toolplane(ToolplaneTab.SPELLS)

    overlap_point = overlap_match.get_point_within()


    for i in range(alch_count):
        while get_active_tab() != 'spells':
            time.sleep(random.randint(*TAB_CHECK_RANGE))
            if terminate: return
        if terminate: return
        client.click(overlap_point, click_cnt=2)


        if random.random() < CHANCE_CHANGE_POINT:
            overlap_point = overlap_match.get_point_within()
            print(f'changed click point: {overlap_point}')
        
        if not (i+1) % 10:
            print(f'Remaining items: {alch_count-(i+1)}')
        
        if random.random() < CHANCE_REST:
            rest_sec = random.randint(*REST_RANGE)
            print(f'Resting for {rest_sec}s')
            client.move_off_window()
            time.sleep(rest_sec)


    
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

    natty_count = client.get_item_cnt('Nature rune',min_confidence=.9)
    item_count = client.get_item_cnt(identifier, min_confidence=.9)
    threading.Thread(target=listen_for_escape, daemon=True).start()

    return natty_count, item_count

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


