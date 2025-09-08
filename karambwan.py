"""
Prereqs:
  - 99 Construction
  - Portal nexus in POH, set to GE
  - karambwangi and vessel in inv
  - equipped dramen staff and construction skillcape
  - fairy ring set to DKP
  - left click cons cape to TP to POH
  - deposit all set in bank
"""

from core.bot import Bot
from core.osrs_client import ToolplaneTab
import random
import time

from core import cv_debug
cv_debug.enable()




MIN_FISH = 26
NEXUS_TILE = (255,112,0)
RING_TILE = (255, 0, 255)
BANK_TILE = (0, 255, 0)
FISH_TILE = (255, 0, 255)

bot = Bot()

def main():
    while True:
        teleport_home()
        time.sleep(random.uniform(2,4))

        karambwan_cnt = get_fish_cnt()
        
        if karambwan_cnt >= MIN_FISH:
            do_bank_from_house()
        else:
            do_fish_from_house()
        
            
def get_fish_cnt():
    current = bot.client.toolplane.get_active_tab(bot.client.get_screenshot())
    if current != ToolplaneTab.INVENTORY.value:
        bot.client.click_toolplane(ToolplaneTab.INVENTORY)
        bot.client.move_off_window()
    return len(bot.client.get_inv_items(['Raw karambwan']))   

def do_bank_from_house():
    bot.client.smart_click_tile(
        NEXUS_TILE,
        ['Grand', 'Exchange'],
        filter_ui=True
    )
    while bot.client.is_moving(): continue
    time.sleep(random.uniform(3,1))
    bot.client.smart_click_tile(
        BANK_TILE,
        ['bank', 'banker'],
        filter_ui=True
    )
    while bot.client.is_moving(): continue
    while not bot.bank.is_open: print('waiting for bank')
    fishes = bot.client.get_inv_items(['Raw karambwan'], verify_tab=False)
    fish = random.choice(fishes)
    bot.client.click(fish)
    bot.bank.close()

def do_fish_from_house():
    bot.client.smart_click_tile(
        RING_TILE,
        ['last', 'dest', 'fairy'],
        filter_ui=True
    )
    while bot.client.is_moving(): continue
    time.sleep(random.uniform(3,1))
    
    bot.client.smart_click_tile(
        FISH_TILE,
        ['fish', 'spot'],
        filter_ui=True,
        retry_hover=6,
        retry_match=6
    )
    while bot.client.is_moving(): continue
    time.sleep(random.uniform(3,1))
    while get_fish_cnt() < MIN_FISH:
        if bot.client.is_fishing: continue
        bot.client.smart_click_tile(
            FISH_TILE,
            ['fish', 'spot'],
            filter_ui=True
        )
        time.sleep(10)

def teleport_home():
    # probs need to be updated for noobs without 99 construction
    bot.client.click_item(
        'Construct. cape(t)',
        tab=ToolplaneTab.EQUIPMENT,
        min_confidence=.9
    )
    
main()