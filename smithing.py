
from core.osrs_client import RuneLiteClient
from core.bank import BankInterface
from core.item_db import ItemLookup
from core import tools
import threading
import time
import random
import keyboard
#not ready :(
client = RuneLiteClient()
db= ItemLookup()
bank = BankInterface(client,db)
BANK_TILE = (150,0,110) 
FURNACE_TILE = (255,100,200)
SLEEP_CHANCE = .005
SLEEP_RANGE = (25,60)
MAX_TIME_MIN = 180
terminate = False

def main():

    threading.Thread(target=listen_for_escape, daemon=True).start()
    start = time.time()
    while not terminate:
        timeout_check(start)
        do_bank()
        do_smith()
        propose_break()
    


    
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
    

    
    # walk_to_box((147,26,112))
    # time.sleep(4)
    # walk_to_box((0,255,255))


    # furnace = tools.find_color_box(
    #     rl_client.get_screenshot(),
    #     (200,150,200),
    #     tol=20
    # )
    # bank = tools.find_color_box(
    #     rl_client.get_screenshot(),
    #     (0,255,0), tol=20
    # )
    # print(furnace)
    # m = furnace.debug_draw(rl_client.screenshot)
    # m = bank.debug_draw(m,color='blue')
    # #rl_client.click(furnace)
    # m.show()

main()