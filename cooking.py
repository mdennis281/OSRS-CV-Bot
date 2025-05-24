from core.osrs_client import RuneLiteClient
from core.bank import BankInterface
from core.item_db import ItemLookup
from core import tools
import threading
import keyboard
import random
import time

food = 'Raw karambwan'
range_tile = (255,0,100)
bank_tile = (0,255,100)
SLEEP_CHANCE = .05
SLEEP_RANGE = (25,60)
MAX_TIME_MIN = 180

terminate = False


client = RuneLiteClient('')
db = ItemLookup()
bank = BankInterface(client,itemdb=db)


def main():
    threading.Thread(target=listen_for_escape, daemon=True).start()
    start = time.time()
    while not terminate:
        timeout_check(start)
        deposit_food()
        do_cook()
        propose_break()

def deposit_food():
    client.smart_click_tile(bank_tile,'bank',retry_match=5)
    while client.is_moving(): continue
    bank.deposit_inv()
    bank.withdraw(food,-1)
    client.move_off_window()
    bank.close()


def do_cook():
    client.smart_click_tile(range_tile,'cook',retry_match=5)
    while client.is_moving(): continue
    keyboard.press('space')
    
    time.sleep(random.uniform(3,7))
    client.move_off_window()
    while client.is_cooking: continue



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