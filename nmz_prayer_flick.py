from osrs_client import RuneLiteClient, ToolplaneTab, MinimapElement
from mouse_control import random_double_click
from tools import MatchResult, MatchShape
from PIL import Image
import nmz_pot_reader
import threading
import keyboard
import random
import time
import cv2
import math




rl_client = RuneLiteClient()
terminate = False

sleep_range = (40, 50)
flick_forget_chance = 0.1  # X% chance to forget flicking
min_absorption = 800
afk = True



def main():
    # Check if RuneLite is open
    if not rl_client.is_open:
        print("RuneLite is not open.")
        return
    
    
    #rl_client.debug_minimap()
    # rl_client.debug_toolplane()
    
    threading.Thread(target=listen_for_escape, daemon=True).start()
    threading.Thread(target=listen_for_debug, daemon=True).start()

    main_loop()

#qp = rl_client.quick_prayer_active

        




def main_loop():
    while not terminate:
        if random.random() < flick_forget_chance:
            print("Forgetting to flick...")
            
        else:
            print("Flicking...")
            flick_routine()

        wait(random.uniform(*sleep_range))

        
def flick_routine():
        
        prayer = rl_client.get_minimap_stat(MinimapElement.PRAYER)

        # Click the prayer icon on the minimap twice
        if prayer and prayer > 0:
            rl_client.click_minimap(
                MinimapElement.PRAYER, 
                click_cnt=2
            )

        handle_health()
        handle_absorption()

        ensure_prayer_state(False)

        if afk:
            rl_client.move_off_window()


        


def ensure_prayer_state(state: bool = False):
    # just make sure it's not already on
    if rl_client.quick_prayer_active != state:
        print(f"Quick prayer is {'off' if state else 'on'}.. why?")
        rl_client.click_minimap(
            MinimapElement.PRAYER
        )

def handle_health():
    health = rl_client.get_minimap_stat(MinimapElement.HEALTH)
    if health and health > 1:
        print(f'Health is {health}, rock cake...')
        
        try:
            rl_client.click_item(
                'Dwarven rock cake',
                click_cnt=min(health-1,8),
                min_click_interval=0.6
            )
        except ValueError:
            print("Warning: no rock cake found. weird flex but ok.")
            return
        handle_health()


def handle_absorption():

    def get_val():
        
        try:
            return nmz_pot_reader.absorption_value(rl_client.get_screenshot())
        except ValueError:
            raise RuntimeError("Failed to read absorption value, assuming not in NMZ. gg")

    
    ans = get_val()

    pots_to_drink = (min_absorption - ans) / 200

    pots_to_drink = max(0, math.ceil(pots_to_drink)) 

    if pots_to_drink > 0:
        print(f"Drinking {pots_to_drink} absorption potions...")

    for _ in range(pots_to_drink):
        if terminate:
            return

        try:
            rl_client.click_item(
                'Absorption (4)',
                min_confidence=0.94,
                min_click_interval=1,
                click_cnt=4,
            )
        except ValueError:
            print("Warning: no nmz pots found.")
            break

        



    
def wait(duration):
    for _ in range(int(duration)):
            if terminate:
                return
            time.sleep(1)
    
def listen_for_debug():
    while True:
        if keyboard.is_pressed('`'):
            print("Debugging...")
            rl_client.debug_minimap()
            rl_client.debug_toolplane()
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
#handle_absorption()
#get_absorbtion_val()


