from core.osrs_client import RuneLiteClient
from core.item_db import ItemLookup
from core import tools
from PIL import Image
import keyboard
from core.input.mouse_control import ClickType
import time
import random
from typing import List

# load into memory now for faster loads
BANK_BR = Image.open('data/ui/bank-bottom-right.png')
BANK_TL = Image.open('data/ui/bank-top-left.png')
BANK_DEPO_INV = Image.open('data/ui/bank-deposit-inv.png')
BANK_SEARCH = Image.open('data/ui/bank-search.png')
BANK_CLOSE = Image.open('data/ui/close-ui-element.png')
BANK_TAB = Image.open('data/ui/bank-tab.png')

class BankInterface:
    def __init__(self,client:RuneLiteClient,itemdb:ItemLookup):
        self.itemdb = itemdb
        self.client = client
        self.bank_match: tools.MatchResult = None
        self.last_custom_quanity = 0

    @property
    def is_open(self):
        try:
            self.get_match()
            return True
        except:
            return False
        
    def deposit_inv(self):
        if not self.is_open: raise ValueError('Bank is not open')
        btn = self.client.find_in_window(
            BANK_DEPO_INV, min_scale=1,max_scale=1
        )
        if btn.confidence > .9:
            self.client.click(btn)

    def search(self, item_name:str):
        if not self.is_open: raise ValueError('Bank is not open')
        search_box = self.client.find_in_window(
            BANK_SEARCH, min_scale=1,max_scale=1
        )
        if search_box.confidence > .9:
            time.sleep(random.uniform(1,1.3))
            self.client.click(search_box)
            keyboard.write(item_name,delay=.2)
            return True
        
    def close(self):
        if not self.is_open: return
        close_btn = self.client.find_in_window(
            BANK_CLOSE, min_scale=1,max_scale=1
        )
        if close_btn.confidence > .9:
            while self.is_open:
                # potentially problematic
                self.client.click(close_btn)
            return True
        
    
    def smart_quantity(self, match:tools.MatchResult, amount:int, action:str):
        if amount < 5 and amount > 0:
            self.client.click(match, click_cnt=amount)
        else:
            self.client.click(
                match, click_type=ClickType.RIGHT, 
                after_click_settle_chance=0, rand_move_chance=0
            )
            if amount == 5:
                self.client.choose_right_click_opt(f'{action}-5')
            elif amount == 10:
                self.client.choose_right_click_opt(f'{action}-10')
            elif amount == -1:
                self.client.choose_right_click_opt(f'{action}-All')
            else:
                if self.last_custom_quanity == amount:
                    self.client.choose_right_click_opt(f'{action}-{amount}')
                else:
                    self.client.choose_right_click_opt(f'{action}-X')
                    time.sleep(random.uniform(1,1.3))
                    keyboard.write(str(amount),delay=.2)
                    keyboard.press('enter')
                    self.last_custom_quanity = amount

                
    def get_bank_tabs(self) -> List[tools.MatchResult]:
        if not self.is_open: raise ValueError('Bank is not open')
        
        matches = tools.find_subimages(
            self.bank_match.crop_in(self.client.get_screenshot()),
            BANK_TAB,
            min_scale=1,max_scale=1,
            min_confidence=.99
        )
        final = []
        
        for match in matches:
            final.append(
                match.transform(
                    self.bank_match.start_x,
                    self.bank_match.start_y
                )
            )

        return final

    def withdraw(self, item_id:str|int, amount:int=1):
        """
        Withdraw an item from the bank.
        -1 quantity = all
        """
        item = self.itemdb.get_item(item_id)

        if not item: raise ValueError(f'Item {item_id} not found in itemdb')

        item_ico = item.icon.crop((0,13,item.icon.width,item.icon.height))

        item_match = self.client.find_in_window(
            item_ico,
            min_scale=.9,
            max_scale=1.1,
            min_confidence=.1,
            sub_match=self.bank_match
        )
        self.client.move_to(
            item_match
        )
        likelihood = self.client.compare_hover_match(item.name)

        print(f'Item {item.name} likelihood: {likelihood:.2f}')
        if likelihood < .6:
            raise ValueError(f'Item {item.name} not found in bank')
        
        # self.client.click(
        #     item_match,click_type=ClickType.RIGHT,
        #     after_click_settle_chance=0,
        #     rand_move_chance=0
        # )

        self.smart_quantity(item_match, amount, 'Withdraw')
        




    def get_match(self) -> tools.MatchResult:
        sc = self.client.get_screenshot()
        tl = self.client.find_in_window(BANK_TL, sc, min_scale=1,max_scale=1)
        br = self.client.find_in_window(BANK_BR, sc, min_scale=1,max_scale=1)

        for m in [tl,br]:
            if m.confidence < .96:
                raise ValueError('Bank is probably not open')
            
        self.bank_match = tools.MatchResult(
            start_x=tl.start_x,
            start_y=tl.start_y,
            end_x=br.end_x,
            end_y=br.end_y
        )
        return self.bank_match

