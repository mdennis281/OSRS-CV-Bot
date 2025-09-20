from core.osrs_client import RuneLiteClient, ToolplaneTab
from PIL import Image
from core import tools
import time
import random
import threading
import keyboard
import pyautogui



client = RuneLiteClient('')
terminate = False
hull_color = (255,0,255)
reward_color = (255,0,100)
gangplank_color = (0,255,100)
ladder_color = (113,113,255)

minigame_active = False

def run_action():
    ht = client.get_action_hover()

    if ht:
        sim = tools.text_similarity(ht,'fill leak')
        print(f'ht: "{ht}" sim: {sim}')
        if sim > .6:
            pyautogui.click()
            time.sleep(1)
    


while True:
    run_action()


def main():
    global minigame_active
    try:
        tools.find_color_box(client.get_screenshot(), hull_color)
        repair_hull()
    finally:
        pass
        
    while not terminate:
        init()
        get_rewards_nav_to_boat()
        
        while not minigame_active and not terminate:
            try:
                repair_hull()
            except:
                print('waiting for game start')
                time.sleep(10)
        minigame_active=False

def get_rewards_nav_to_boat():
    client.smart_click_tile(reward_color,'inspect')
    time.sleep(5)
    try:
        bank = Image.open('data/ui/trawler-bank-rewards.png')
        m = tools.find_subimage(client.get_screenshot(),bank)
        print(f'Bank all button confidence: {m.confidence}')
        if m.confidence > .9:
            client.click(m)
        else:
            raise ValueError('didnt get rewards')
    except Exception as e:
        print('didnt get rewards, moving on')
    client.smart_click_tile(
        gangplank_color,'cross',
        retry_match=10
    )
    time.sleep(10)
    client.smart_click_tile(
        ladder_color,'climb',
        retry_match=10
        )
    



def repair_hull():
    global minigame_active
    match: tools.MatchResult = tools.find_color_box(client.get_screenshot(), hull_color)
    print(f'Hull confidence: {match.confidence}')
    minigame_active = True
    client.move_to(match.get_point_within(), rand_move_chance=0)
    while not terminate:
        text = client.get_hover_text()
        if 'fill' in text.lower():
            client.click(match.get_point_within(),rand_move_chance=0,after_click_settle_chance=0)
            time.sleep(1)
            try:
                match: tools.MatchResult = tools.find_color_box(client.get_screenshot(), hull_color)
            finally:
                print('match not found')
            print(f'Hull confidence: {match.confidence}')
            client.move_to(match.get_point_within(),rand_move_chance=0)
        if random.random() < .1:
            client.click(match.get_point_within(),rand_move_chance=0,after_click_settle_chance=0)
            

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

#main()