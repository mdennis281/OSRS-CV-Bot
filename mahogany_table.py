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
SLEEP_CHANCE = .008
SLEEP_RANGE = (25,122)
terminate = False

def main():
    start_time = time.time()
    items = init(PLANKS_NOTE)

    # sometimes it fails to unnote planks
    # calling it a feature, not bug
    missed_planks_cnt = 0

    while not terminate:
        unnote_planks()

        client.smart_click_tile(
            PORTAL_TILE,
            'Build'
        )

        sleep(5)

        for _ in range(4):
            propose_sleep()
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
            for _ in range(3):
                if terminate: break
                try:
                    match = client.find_img_in_window(
                        MAHOGANY_TABLE,
                        confidence=.98
                    )
                    break
                except Exception as e:
                    print(e)
                    print('missed mahogany table build btn')

            
            client.click(match)
            sleep(.4)
            
        propose_sleep()
        sleep(2)
        client.smart_click_tile(
            PORTAL_TILE,
            'Enter'
        )
        sleep(3)
    total_time = tools.seconds_to_hms(time.time() - start_time)
    print(f'Grinded for {total_time}')
    



def unnote_planks():
    done = False
    for _ in range(3):
        if terminate: break
        client.click_item(
            PLANKS_NOTE,
            crop=(0,13,0,0), # crop top off planks (count)
            min_confidence=.89
        )
        if terminate: break
        client.smart_click_tile(
            PHIALS_TILE,
            'Phials'
        )
        try:
            if terminate: break
            chat_text_clicker(
                'Exchange All:',
                'Waiting for Phials'
            )
            done = True
            break
        except: print('Phials is an elusive boi')
    if not done:
        raise RuntimeError('Phials evaded us :(')


def chat_text_clicker(text,wait_msg,wait=1,tries=5):
    done = False
    for _ in range(tries):
        if terminate: break
        try:
            time.sleep(wait)
            client.click_chat_text(text)
            done = True
            break
        except:
            print(wait_msg)
    if not done:
        raise RuntimeError(f'Could not find chat text {text}')

def propose_sleep():
    if random.random() < SLEEP_CHANCE:
        t = random.randint(*SLEEP_RANGE)
        print(f'sleeping for {tools.seconds_to_hms(t)}')
        time.sleep(t)

def sleep(base_time):
    mult = random.uniform(1.0,1.3)
    time.sleep(base_time*mult)
    


def init(identifier):

    item_count = client.get_item_cnt(identifier, min_confidence=.9)
    threading.Thread(target=listen_for_escape, daemon=True).start()

    return item_count


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