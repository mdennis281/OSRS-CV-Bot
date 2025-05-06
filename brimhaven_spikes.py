
from core.osrs_client import RuneLiteClient, MinimapElement
from core import tools
import time
import random
import keyboard
import threading

rl_client = RuneLiteClient()
terminate = False


# set tiles with these colors on both
# side of the spikes (one color for each side)
TILE_1 = (255,118,96)
TILE_2 = (0,0,167)

def main():
    threading.Thread(target=listen_for_escape, daemon=True).start()
    do_loop()
    

FAILS = 0
def walk_to_box(color, tolerance=40):
    global FAILS
    try:
        sc = rl_client.get_screenshot()
        tile = tools.find_color_box(
            sc,
            color,
            tolerance
        )
        rl_client.click(tile)
        FAILS = 0
    except ValueError as e:
        print(f'failed to click: {color}')
        
        FAILS += 1
        if FAILS > 3:
            raise RuntimeError('idek bro it dont got gas in it')
    #tile.debug_draw(sc).show()
    

def do_loop():
    health = health_val()
    while True:
        for val in [TILE_1,TILE_2]:
            if terminate: return
            if health > health_val():
                print('ouch!')
                walk_to_box( TILE_1 if val == TILE_2 else TILE_2 )
                health = health_val()
                if health < 10:
                    return
                time.sleep(random.uniform(2.25,2.75))
                if terminate: return

            walk_to_box(val)
            time.sleep(random.uniform(2.25,3))

def listen_for_escape():
    """Thread function to listen for the Esc key."""
    global terminate
    while True:
        if keyboard.is_pressed('esc'):
            print("Terminating...")
            terminate = True
            return
        time.sleep(0.1)

def health_val():
    return rl_client.get_minimap_stat(MinimapElement.HEALTH)
main()