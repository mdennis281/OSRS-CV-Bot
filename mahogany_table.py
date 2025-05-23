from core.osrs_client import RuneLiteClient, ToolplaneTab
from PIL import Image
from core import tools
import time
import random
import threading
import keyboard


client = RuneLiteClient('')
PLANKS = 8782
PLANKS_NOTE = 8783 # mahogany plank (noted)
PHIALS_TILE = (0,255,255)
PORTAL_TILE = (255,55,255)
TABLE_TILE = (255,55,100)
MAHOGANY_TABLE = Image.open('data/ui/mahogany-table-build.png')
SLEEP_CHANCE = .01 #actually higher b/c this is referenced multiple times
SLEEP_RANGE = (25,122)
MAX_TIME_MIN = 180
terminate = False

"""
Plugins: [ 'Better NPC Highlight', 'Tile Indicators' ]
Setup:
 import tiles:
  [
	{"regionId":7513,"regionX":3,"regionY":11,"z":0,"color":"#FFFF37FF"},
	{"regionId":7513,"regionX":36,"regionY":60,"z":0,"color":"#FFFF3764"},
	{"regionId":11826,"regionX":8,"regionY":24,"z":0,"color":"#FFFF37FF"}
  ]
  NPC highlight: 
   NPC Highlight > Tile > Tile Names > "Phials"

"""

def main():
    start_time = time.time()
    init()

    while not terminate:
        timeout_check(start_time)
        if not planks_in_inventory():
            unnote_planks()

        client.smart_click_tile(
            PORTAL_TILE,
            'Build'
        )
        propose_break()

        sleep(5)

        for _ in range(4):
            if not planks_in_inventory():
                break
            propose_break()
            if terminate: break
            sleep(1)
            try:
                client.smart_click_tile(
                    TABLE_TILE,
                    'Remove'
                )
                if terminate: break
                chat_text_clicker(
                    'Yes',
                    'Waiting for table'
                )
            except: print('table already missing? aight')
            time.sleep(1)

            
            try:
                client.smart_click_tile(
                    TABLE_TILE,
                    'Build'
                )
            except Exception as e:
                print(e)
                print('couldnt find build button, lets assume it got pressed')

            time.sleep(1)
            match = None
            for _ in range(3):
                if terminate: break
                try:
                    match = client.find_in_window(
                        MAHOGANY_TABLE,
                        confidence=.98
                    )
                    break
                except Exception as e:
                    print('missed mahogany table build btn')

            if match:
                client.click(match)
            sleep(.4)
            
        propose_break()
        sleep(2)
        client.smart_click_tile(
            PORTAL_TILE,
            'Enter'
        )
        sleep(3)
    total_time = tools.seconds_to_hms(time.time() - start_time)
    print(f'Grinded for {total_time}')
    



def unnote_planks(recurse=0):
    if recurse >= 3:
        raise ValueError('WTF Phails??')
    done = False
    for _ in range(4):
        # seems overkill but im getting weird behavior
        if planks_in_inventory():
            return
        if terminate: break
        try:
            client.click_item(
                PLANKS_NOTE,
                crop=(0,13,0,0), # crop top off planks (count)
                min_confidence=.89
            )
        except:
            print('wheres the noted planks')
            client.click_toolplane(ToolplaneTab.SKILLS)
            client.move_off_window()
            time.sleep(random.randint(1,6))
            continue
        if terminate: break
        try:
            client.smart_click_tile(
                PHIALS_TILE,
                'Phials',
                retry_hover=2,
                retry_match=10
            )
        except:
            print('phials match miss')
            # unselect plank
            client.click_toolplane(ToolplaneTab.SKILLS)
            client.move_off_window()
            time.sleep(random.randint(1,6))
            
            continue
        try:
            if terminate: break
            chat_text_clicker(
                'Exchange All:',
                'Waiting for Phials',
                tries=4
            )
            done = True
            break
        except Exception as e: 
            print(e)
            print('Phials is an elusive boi')
    if not done:
        raise RuntimeError('Phials evaded us :(')
    time.sleep(1)
    if not planks_in_inventory():
        print('Apparently i didnt get planks :(')
        unnote_planks(recurse+1)


def chat_text_clicker(text,wait_msg,wait=.5,tries=8):
    done = False
    for _ in range(tries):
        if terminate: break
        try:
            time.sleep(wait)
            client.click_chat_text(text)
            done = True
            break
        except Exception as e:
            print(wait_msg)
    if not done:
        raise RuntimeError(f'Could not find chat text {text}')

def propose_break():
    if random.random() < SLEEP_CHANCE:
        t = random.randint(*SLEEP_RANGE)
        print(f'sleeping for {tools.seconds_to_hms(t)}')
        client.move_off_window()
        time.sleep(t)

def sleep(base_time):
    mult = random.uniform(1.0,1.3)
    time.sleep(base_time*mult)
    
def planks_in_inventory() -> bool:
    try:
        client.find_item(PLANKS,min_confidence=.95)
        return True
    except:
        return False
    
def timeout_check(start):
    runtime = time.time() - start
    if runtime/60 > MAX_TIME_MIN:
        raise RuntimeError('MAX TIME LIMIT EXCEEDED')

def init():

    print(f'initializing bot {__file__}')
    threading.Thread(target=listen_for_escape, daemon=True).start()


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