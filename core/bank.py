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
import re
from typing import List


def _extract_trailing_quantity(text: str) -> int | None:
    """Best-effort extraction of the trailing number from OCR'd hover text.

    Only the trailing digit group is considered, so noisy label characters
    like 'Defau1t Qun1ty' don't bleed into the result. Comma- and
    space-separated thousands are normalised.

    Examples:
        'Default quantity: 13'        -> 13
        'Default quantity: 130,000'   -> 130000
        'defauit quntity: 13'         -> 13
        'Defau1t Qun1ty 120 000'      -> 120000
    """
    if not text:
        return None
    cleaned = text.rstrip().rstrip(' .,:;|/\\')
    # Grouped thousands: "130,000" or "120 000"
    m = re.search(r'(\d{1,3}(?:[, ]\d{3})+)\s*$', cleaned)
    if m:
        return int(re.sub(r'[, ]', '', m.group(1)))
    # Plain trailing digits
    m = re.search(r'(\d+)\s*$', cleaned)
    if m:
        return int(m.group(1))
    return None



# load into memory now for faster loads
BANK_BR = Image.open('data/ui/bank-bottom-right.png')
BANK_TL = Image.open('data/ui/bank-top-left.png')
# bank-top-left.png is cropped from inside the bank window (skipping the title
# bar) because OSRS action/hover text overlays the title row and corrupts a
# top-of-window template. Subtract this offset when computing bank_match.start_y
# so the resulting region still spans the full bank like callers expect.
BANK_TL_Y_OFFSET = 40
BANK_DEPO_INV = Image.open('data/ui/bank-deposit-inv.png')
BANK_SEARCH = Image.open('data/ui/bank-search.png')
BANK_CLOSE = Image.open('data/ui/close-ui-element.png')
BANK_TAB = Image.open('data/ui/bank-tab.png')
BANK_ARROW_UP = Image.open('data/ui/bank-scroll-up.png')
BANK_ARROW_DOWN = BANK_ARROW_UP.rotate(180)
BANK_REARRANGE_SWAP = Image.open('data/ui/bank-rearrange-swap.png')
BANK_REARRANGE_INSERT = Image.open('data/ui/bank-rearrange-insert.png')


class BankSettings:
    """
    Offsets are relative to bank_match. bank_match.start_x/start_y is the
    bank window's top-left corner; bank_match.end_x/end_y is its bottom-right
    corner. The bottom button row sits at end_y - 37 .. end_y - 11.
    """
    def __init__(self, bank_match: tools.MatchResult):
        self._selected_color: tuple[int,int,int] = (126,30,28)

        sx = bank_match.start_x
        ey = bank_match.end_y
        # Bottom button row vertical range. bank_match starts at (0,0) of the
        # bank window and ends at (495, 708) in reference coords; the button
        # row sits at y=668..694 (so end_y - 40 .. end_y - 14).
        y_top = ey - 40
        y_bot = ey - 14

        # Rearrange (Swap/Insert) is a single toggle button; clicking cycles the icon.
        self.rearrange_btn = tools.MatchResult(
            start_x = sx + 18,
            start_y = y_top,
            end_x   = sx + 50,
            end_y   = y_bot,
        )
        # Withdraw (Item/Note) is a single toggle button (parchment icon).
        self.withdraw_btn = tools.MatchResult(
            start_x = sx + 55,
            start_y = y_top,
            end_x   = sx + 87,
            end_y   = y_bot,
        )

        # Quantity row: 1 / 5 / 10 / X / All, ~37px pitch.
        def q_btn(off_x_start: int, off_x_end: int) -> tools.MatchResult:
            return tools.MatchResult(
                start_x = sx + off_x_start,
                start_y = y_top,
                end_x   = sx + off_x_end,
                end_y   = y_bot,
            )
        self.quantity_1_btn   = q_btn( 92, 126)
        self.quantity_5_btn   = q_btn(130, 162)
        self.quantity_10_btn  = q_btn(167, 199)
        self.quantity_x_btn   = q_btn(204, 236)
        self.quantity_all_btn = q_btn(241, 273)

    def get_rearrange_setting(self, sc: Image.Image) -> str:
        """Match swap/insert icon templates against the rearrange button area."""
        btn_img = self.rearrange_btn.crop_in(sc)
        swap_m = tools.find_subimage(btn_img, BANK_REARRANGE_SWAP, min_scale=1, max_scale=1)
        ins_m  = tools.find_subimage(btn_img, BANK_REARRANGE_INSERT, min_scale=1, max_scale=1)
        return 'Swap' if swap_m.confidence > ins_m.confidence else 'Insert'

    def get_withdraw_setting(self, sc: Image.Image) -> str:
        """Note mode lights the parchment button red; otherwise it's grey (Item)."""
        wn_img = self.withdraw_btn.crop_in(sc)
        wn_likelihood = tools.calculate_color_percentage(
            wn_img,
            self._selected_color,
            tolerance=20
        )
        # Any meaningful red coverage means the toggle is active.
        return 'Note' if wn_likelihood > 0.05 else 'Item'

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
            - Rearrange: 'Swap', 'Insert' (both return the same toggle button)
            - Withdraw: 'Item', 'Note' (both return the same toggle button)
            - Quantity: '1', '5', '10', 'X', 'All'
        """
        category = category.lower()
        option = str(option).lower()

        if category == 'rearrange':
            return self.rearrange_btn
        elif category == 'withdraw':
            return self.withdraw_btn
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
        min_confidence:float=0.7,
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
            hover_verify_retry=3,
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
        
    def _read_x_quantity_hover(self) -> int | None:
        """Hover the X quantity button and read its tooltip to learn the
        currently-bound custom quantity. Returns None if no number could be
        extracted (OCR garbage, tooltip not visible, etc.).
        """
        btn = self.bs.quantity_x_btn
        try:
            self.client.move_to(btn, rand_move_chance=0)
            time.sleep(random.uniform(0.6, 0.9))  # let tooltip render
            raw = self.client.hover_text or ''
        except Exception as e:
            self.log.debug(f'X hover read failed: {e}')
            return None
        n = _extract_trailing_quantity(raw)
        self.log.info(f"X hover: raw='{raw}' extracted={n}")
        return n

    def set_default_quantity(self, option:int):
        if not self.is_open: raise ValueError('Bank is not open')

        if self.default_quantity == option:
            return

        if option in [1,5,10]:
            self.set_quantity_setting(str(option))
        else:
            btn = self.bs.quantity_x_btn
            # Best-effort sync of last_custom_quantity by reading the X
            # button's hover tooltip ("Default quantity: <N>"). If it
            # already matches our target we can skip the right-click reset.
            observed = self._read_x_quantity_hover()
            if observed is not None:
                self.last_custom_quantity = observed
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
            start_y=tl.start_y - BANK_TL_Y_OFFSET,
            end_x=br.end_x,
            end_y=br.end_y
        )
        self.bs = BankSettings(self.bank_match)
        return self.bank_match

