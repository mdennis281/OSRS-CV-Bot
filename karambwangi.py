from core.osrs_client import RuneLiteClient, ToolplaneTab
from core.item_db import ItemLookup
from typing import List
from core import tools
import random
import keyboard
import threading
import time

client = RuneLiteClient()
db = ItemLookup()
terminate = False


def main():
    threading.Thread(target=listen_for_escape, daemon=True).start()
    while not terminate:
        while client.is_moving():
            if terminate: return
            continue
        time.sleep(random.uniform(1, 3))  # Random delay to avoid detection
        while client.is_fishing:
            if terminate: return
            continue
        #drop_items(['Raw shrimps','Raw trout'])
        find_fishing_spot()


def find_fishing_spot(retry=5):
    """Finds a fishing spot on the screen."""
    sc = client.get_screenshot()
    tp = client.sectors.toolplane
    sc = tp.remove_from(sc)
    fish = db.get_item_by_name('Raw karambwanji').icon
    m = client.find_in_window(
        fish, min_scale=1, max_scale=1, screenshot=sc
    )
    try:
        if m.confidence < .90:
            raise RuntimeError("Fishing spot not found with high enough confidence.")
        client.smart_click_match(m, ['net','fish','spot'], retry_hover=10)
    except RuntimeError as e:
        if retry > 0:
            print(f"Failed to find fishing spot, retrying {retry} more times...")
            sleep_time = random.randint(40, 70)
            print(f"Sleeping for {sleep_time:.2f} seconds before retrying...")
            for _ in range(sleep_time):
                if terminate: return
                time.sleep(1)
            find_fishing_spot(retry - 1)
        else: 
            raise e

def listen_for_escape():
    """Thread function to listen for the Esc key."""
    global terminate
    while True:
        if keyboard.is_pressed('esc'):
            print("Terminating...")
            terminate = True
            return
        time.sleep(0.1)

def drop_items(items:List[str]):
    client.click_toolplane(ToolplaneTab.INVENTORY)
    sc = client.get_screenshot()
    tp = client.sectors.toolplane
    sc = tp.crop_in(sc)
    matches: List[tools.MatchResult] = []
    for item in items:
        item_icon = db.get_item_by_name(item).icon
        if not item_icon:
            print(f"Item icon for '{item}' not found.")
            continue
        matches += tools.find_subimages(
            sc, item_icon, min_confidence=.99
        )
    matches.sort(
        key=lambda x: x.start_x, 
        reverse=random.choice([True, False])
    )
    matches.sort(
        key=lambda x: x.start_y, 
        reverse=random.choice([True, False])
    )
    keyboard.press('shift')
    try:
        for match in matches:
            client.click(
                match, 
                after_click_settle_chance=0,
                rand_move_chance=0,
                parent_sectors=[tp]
            )
    finally:
        keyboard.release('shift')

main()