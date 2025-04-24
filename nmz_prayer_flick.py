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




rl_client = RuneLiteClient()
terminate = False

sleep_range = (40, 50)
flick_forget_chance = 0.1  # X% chance to forget flicking
target_absorption = 950



def main():
    # Check if RuneLite is open
    if not rl_client.is_open:
        print("RuneLite is not open.")
        return
    
    
    # rl_client.debug_minimap()
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
        health = rl_client.get_minimap_stat(MinimapElement.HEALTH)

        # Click the prayer icon on the minimap twice
        rl_client.click_minimap(MinimapElement.PRAYER, click_cnt=2)

        handle_absorption()

        if health and health > 1:
            print(f'Health is {health}, rock cake...')
            
            rl_client.click_item(
                'Dwarven rock cake',
                click_cnt=min(health-1,8),
            )

def handle_absorption():

    def get_val():
        
        try:
            return nmz_pot_reader.absorption_value(rl_client.get_screenshot())
        except ValueError:
            raise RuntimeError("Failed to read absorption value.")

    
    ans = get_val()


    while get_val() + 50 < target_absorption and not terminate:
        print(f"Absorption is {ans}, rock cake...")
        rl_client.click_item(
            'Absorption (4)'
        )

        ans = get_val()



    
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


