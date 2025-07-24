from core.osrs_client import RuneLiteClient
from core import tools
from core.item_db import ItemLookup
import threading
import keyboard
from PIL import Image
import time
import random
from concurrent.futures import ThreadPoolExecutor

client = RuneLiteClient()
terminate = False
ORE_TILES = [(100,100,255), (100,200,100)]
DEPOSIT_TILE = (255,0,100)
ORE = 'coal'
itemdb = ItemLookup()
SLEEP_CHANCE = .03 
SLEEP_RANGE = (25,122)

DEPOSIT_INV_BTN = Image.open('data/ui/bank-deposit-inv.png')
CLOSE_UI_ELEMENT = Image.open('data/ui/close-ui-element.png')

LAST_MINED = None

def listen_for_escape():
    """Thread function to listen for the Esc key."""
    global terminate
    while True:
        if keyboard.is_pressed('esc'):
            print("Terminating...")
            terminate = True
            return
        time.sleep(0.1)
threading.Thread(target=listen_for_escape, daemon=True).start()

def main():
    while not terminate:
        if is_inventory_full():
            print("Inventory is full, depositing...")
            deposit_inventory()
            
            
        elif client.is_mining:
            print("Mining in progress...")
            time.sleep(2)
        else:
            print("Not mining, attempting to mine ore...")
            propose_break()
            if mine_ore():
                print("Ore mined successfully.")
                time.sleep(4)
            else:
                print("No ore found, retrying...")
                time.sleep(1)
       



def mine_ore():
    global LAST_MINED
    def find_ore_tile(tile_color):
        try:
            return [tile_color, tools.find_color_box(
                client.get_screenshot(),
                tile_color,
                tol=40
            )]
        except Exception as e:
            print(f"Error finding ore tile: {e}")
            return None
    with ThreadPoolExecutor() as executor:
        results = list(executor.map(find_ore_tile, ORE_TILES))
    tiles = [tile for tile in results if tile is not None]

    tiles.sort(key=lambda x: x[1].confidence, reverse=True)
    if tiles and tiles[0][0] == LAST_MINED:
        tiles.append(tiles.pop(0))

    clicked = False
    for tile in tiles:
        try: 
            client.smart_click_match(tile[1], ORE)
            clicked = True
            LAST_MINED = tile[0]
            break
        except Exception as e:
            print(f"Error clicking tile: {e}")
            continue
    if clicked:
        # chance to move off window after clicking
        if random.random() < .3:
            client.move_off_window()
    return clicked
    

def deposit_inventory():
    client.smart_click_tile(
        DEPOSIT_TILE, ['deposit','bank','posit']
    )
    for _ in range(6):
        if terminate: return
        time.sleep(random.uniform(2,3))
        try:
            deposit = client.find_in_window(DEPOSIT_INV_BTN, min_confidence=0.7)
            exit = client.find_in_window(CLOSE_UI_ELEMENT, min_confidence=0.7)
            
        except Exception as e:
            print(e)
            print("Deposit button not found, retrying...")

            continue
        client.click(deposit)
        if ORE == 'coal':
            empty_coal_bag()
        
        time.sleep(random.uniform(.3, 2))
        client.click(exit)
        break

def empty_coal_bag():
    coal_bag = itemdb.get_item_by_name('Open coal bag')
    try:
        coal_bag_match = client.find_in_window(coal_bag.icon, min_confidence=0.9)
        if coal_bag_match:
            client.click(coal_bag_match)
            print("Coal bag emptied.")
    except Exception as e:
        print(f"Error emptying coal bag: {e}")

def is_inventory_full():
    """Check if the inventory is full."""
    try:
        full_match = client.find_chat_text('too full')
        if full_match.confidence > 0.84:
            print("Inventory is full.")
            return True
    except:
        pass
    return False

def propose_break():
    if random.random() < SLEEP_CHANCE:
        t = random.randint(*SLEEP_RANGE)
        print(f'sleeping for {tools.seconds_to_hms(t)}')
        client.move_off_window()
        for _ in range(t):
            if terminate: raise RuntimeError('Terminated during sleep')
            time.sleep(1)


#mine_ore()
#deposit_inventory()

main()



# while not terminate:
#     is_mining = client.get_skilling_state('mine')
#     if is_mining:
#         print("Mining in progress...")
#         time.sleep(1)
#     else:
#         print("Not mining, waiting...")
#         time.sleep(2)