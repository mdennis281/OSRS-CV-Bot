from core.osrs_client import RuneLiteClient
from core.item_db import ItemLookup
from core import tools
from core import ocr
from core.logger import get_logger
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
BANK_ARROW_UP = Image.open('data/ui/bank-scroll-up.png')
BANK_ARROW_DOWN = BANK_ARROW_UP.rotate(180)


class BankSettings:
    def __init__(self, bank_match: tools.MatchResult):
        self._selected_color: tuple[int,int,int] = (126,30,28)
        
        self.rearrange_swap_btn = tools.MatchResult(
            start_x = bank_match.start_x + 4,
            start_y = bank_match.end_y - 26,
            end_x = bank_match.start_x + 44,
            end_y = bank_match.end_y - 7
        )
        self.rearrange_insert_btn = self.rearrange_swap_btn.transform(50,0)
        
        self.withdraw_item_btn = self.rearrange_insert_btn.transform(50,0)
        self.withdraw_note_btn = self.withdraw_item_btn.transform(50,0)
        
        self.quantity_1_btn = tools.MatchResult(
            start_x = bank_match.start_x + 204,
            start_y = bank_match.end_y - 26,
            end_x = bank_match.start_x + 218,
            end_y = bank_match.end_y - 7
        )
        
        self.quantity_5_btn = self.quantity_1_btn.transform(25,0)
        self.quantity_10_btn = self.quantity_5_btn.transform(25,0)
        self.quantity_x_btn = self.quantity_10_btn.transform(25,0)
        self.quantity_all_btn = self.quantity_x_btn.transform(25,0)
    
    def get_rearrange_setting(self, sc: Image.Image) -> str:
        rs_img = self.rearrange_swap_btn.crop_in(sc)
        ri_img = self.rearrange_insert_btn.crop_in(sc)
        
        rs_likelihood = tools.calculate_color_percentage(
            rs_img, 
            self._selected_color,
            tolerance=20
        )
        ri_likelihood = tools.calculate_color_percentage(
            ri_img,
            self._selected_color,
            tolerance=20
        )
        if rs_likelihood > ri_likelihood:
            return 'Swap'
        return 'Insert'
    
    def get_withdraw_setting(self, sc: Image.Image) -> str:
        wi_img = self.withdraw_item_btn.crop_in(sc)
        wn_img = self.withdraw_note_btn.crop_in(sc)
        
        wi_likelihood = tools.calculate_color_percentage(
            wi_img,
            self._selected_color,
            tolerance=20
        )
        wn_likelihood = tools.calculate_color_percentage(
            wn_img,
            self._selected_color,
            tolerance=20
        )
        
        if wi_likelihood > wn_likelihood:
            return 'Item'
        return 'Note'

    def get_quantity_setting(self, sc: Image.Image) -> str:
        buttons = {
            '1': self.quantity_1_btn,
            '5': self.quantity_5_btn,
            '10': self.quantity_10_btn,
            'x': self.quantity_x_btn,
            'all': self.quantity_all_btn
        }
        
        best_option = '1'
        best_score = -1.0
        
        for opt, btn in buttons.items():
            img = btn.crop_in(sc)
            score = tools.calculate_color_percentage(
                img,
                self._selected_color,
                tolerance=20
            )
            if score > best_score:
                best_score = score
                best_option = opt
                
        return best_option
    
    def get_button_match(self, category:str, option:str) -> tools.MatchResult:
        """
        Returns the MatchResult for the given category and option.
        Valid categories: 'Rearrange', 'Withdraw', 'Quantity'
        Valid options:
            - Rearrange: 'Swap', 'Insert'
            - Withdraw: 'Item', 'Note'
            - Quantity: '1', '5', '10', 'X', 'All'
        """
        category = category.lower()
        option = str(option).lower()
        
        if category == 'rearrange':
            if option == 'swap':
                return self.rearrange_swap_btn
            else:
                return self.rearrange_insert_btn
        elif category == 'withdraw':
            if option == 'item':
                return self.withdraw_item_btn
            else:
                return self.withdraw_note_btn
        elif category == 'quantity':
            if option == '1':
                return self.quantity_1_btn
            elif option == '5':
                return self.quantity_5_btn
            elif option == '10':
                return self.quantity_10_btn
            elif option == 'x':
                return self.quantity_x_btn
            elif option == 'all':
                return self.quantity_all_btn
        raise ValueError(f'Invalid category/option: {category}/{option}')


class BankInterface:
    def __init__(self,client:RuneLiteClient,itemdb:ItemLookup):
        self.itemdb = itemdb
        self.client = client
        self.bank_match: tools.MatchResult = None
        self.bs: BankSettings = None
        self.last_custom_quantity = 0
        self.log = get_logger('Bank')
        self._scrollbar_match: tools.MatchResult = None
        self.default_quantity: int = -1

    @property
    def is_open(self):
        try:
            self.get_match()
            return True
        except:
            return False
        
    @property
    def bank_sc(self) -> Image.Image:
        if not self.is_open: raise ValueError('Bank is not open')
        return self.bank_match.crop_in(self.client.get_screenshot())
    
    def transform_to_client(self, match:tools.MatchResult) -> tools.MatchResult:
        if not self.is_open: raise ValueError('Bank is not open')
        return match.transform(
            -self.bank_match.start_x,
            -self.bank_match.start_y
        )

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
    
    def get_item_count(
        self, 
        item_id:str|int, 
        min_confidence:float=0.9,
        hover_verify:bool=True
        
        ) -> int:
        if not self.is_open: raise ValueError('Bank is not open')

        sc = self.client.get_screenshot()
        
        item = self.itemdb.get_item(item_id) # verify it exists
        
        if not item: raise ValueError(f'Item {item_id} not found in itemdb')

        item_match = self.client.smart_find_item(
            item=item,
            parent_match=self.bank_match,
            hover_verify=hover_verify,
            ignore_count=True,
            min_confidence=min_confidence
        )
        
        if not item_match:
            raise ValueError('Match not found')

        return item.get_count(item_match, sc)

        
        
    
    def smart_quantity(self, match:tools.MatchResult, amount:int, action:str):
        if amount == self.default_quantity:
            self.client.click(match, click_cnt=1)
        elif amount < 5 and amount > 0:
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
                if self.last_custom_quantity == amount:
                    self.log.info(f'Custom quantity match - {amount}')
                    self.client.choose_right_click_opt(f'{action}-{amount}')
                else:
                    self.log.info(f'Withdrawing custom amount: {amount}')
                    self.client.choose_right_click_opt(f'{action}-X')
                    time.sleep(random.uniform(1,1.3))
                    keyboard.write(str(amount),delay=.2)
                    keyboard.press('enter')
                    self.last_custom_quantity = amount

                
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

    def get_settings(self):
        if not self.is_open: raise ValueError('Bank is not open')
        settings = BankSettings(self.bank_match)
        sc = self.client.get_screenshot()
        rearrange = settings.get_rearrange_setting(sc)
        withdraw = settings.get_withdraw_setting(sc)
        quantity = settings.get_quantity_setting(sc)
        return {
            'Rearrange': rearrange,
            'Withdraw': withdraw,
            'Quantity': quantity
        }
        
    def set_withdraw_setting(self, option:str):
        if not self.is_open: raise ValueError('Bank is not open')
        current = self.bs.get_withdraw_setting(self.client.get_screenshot())
        if current == option:
            return
        btn_match = self.bs.get_button_match('Withdraw', option)
        self.client.click(
            btn_match,
            after_click_settle_chance=0.5,
            rand_move_chance=0.3
        )
        
    
        
    def set_rearrange_setting(self, option:str):
        if not self.is_open: raise ValueError('Bank is not open')
        current = self.bs.get_rearrange_setting(self.client.get_screenshot())
        if current == option:
            return
        btn_match = self.bs.get_button_match('Rearrange', option)
        self.client.click(
            btn_match,
            after_click_settle_chance=0.5,
            rand_move_chance=0.3
        )
    
    def set_quantity_setting(self, option:str):
        if not self.is_open: raise ValueError('Bank is not open')
        current = self.bs.get_quantity_setting(self.client.get_screenshot())
        if current == option:
            return
        btn_match = self.bs.get_button_match('Quantity', option)
        self.client.click(
            btn_match,
            after_click_settle_chance=0.5,
            rand_move_chance=0.3
        )
        
    def set_default_quantity(self, option:int):
        if not self.is_open: raise ValueError('Bank is not open')
        
        if self.default_quantity == option:
            return
        
        if option in [1,5,10]:
            self.set_quantity_setting(str(option))
        else:
            btn = self.bs.quantity_x_btn
            self.set_quantity_setting('X')
            if option != self.last_custom_quantity:
                self.client.click(
                    btn,click_type=ClickType.RIGHT,
                    after_click_settle_chance=0, rand_move_chance=0
                )
                self.client.choose_right_click_opt('Set custom quantity')
                
                time.sleep(random.uniform(.6,1))
                
                keyboard.write(str(option),delay=.2)
                keyboard.press('enter')
                self.last_custom_quantity = option
        self.default_quantity = option

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

        self.log.info(f'Item {item.name} likelihood: {likelihood:.2f}')
        if likelihood < .6:
            raise ValueError(f'Item {item.name} not found in bank')
        
        # self.client.click(
        #     item_match,click_type=ClickType.RIGHT,
        #     after_click_settle_chance=0,
        #     rand_move_chance=0
        # )

        self.smart_quantity(item_match, amount, 'Withdraw')
        



    @tools.timeit()
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
        self.bs = BankSettings(self.bank_match)
        return self.bank_match

