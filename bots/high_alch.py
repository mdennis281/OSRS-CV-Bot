from bots.core import BotConfigMixin
from bots.core.cfg_types import RangeParam, BreakCfgParam, ItemParam
from core.bot import Bot

from core.osrs_client import ToolplaneTab


from PIL import Image
import random
import time
import pyautogui

class BotConfig(BotConfigMixin):
    # Configuration parameters

    alch_item: ItemParam = ItemParam(1396)  # Default to water battlestaff (noted)
    nature_rune: ItemParam = ItemParam("Nature rune")
    chance_change_point: float = 0.08

    # makes it more human-like
    tab_check_range = RangeParam(.5,1.75)
    break_cfg: BreakCfgParam = BreakCfgParam(
        RangeParam(30, 75),  # break duration range in seconds
        0.01  # break chance
    )



class BotExecutor(Bot):
    name: str = "High Alch Bot"
    description: str = "A bot that performs high alchemy on a chosen item."
    tier: str = "S"
    instructions: str = """
    This bot will cast high alchemy on a specified item in the inventory.
    Ensure item selected is noted, it's designed to click a single slot.
    Expects nature runes in inventory, and fire staff of some kind equipped."""
    
    
    def __init__(self, config: BotConfig, user=''):
        super().__init__(user, break_cfg=config.break_cfg)
        self.cfg: BotConfig = config
        
        self.overlap = None
        self.overlap_point = None
        self.alch_count = 0
        
    def start(self):
        nattys, items = self.init()
        self.alch_count = min(nattys, items)
        self.log.info(f'Found {nattys} nature runes and {items} items to alch. Alching {self.alch_count} times.')
        
        self.find_overlap(self.cfg.alch_item.id)
        self.get_overlap_point()
        self.loop()

    def loop(self):
        for i in range(self.alch_count):
            while self.get_active_tab() != 'spells':
                time.sleep(self.cfg.tab_check_range.choose())
            
            self.client.click(
                self.overlap_point, click_cnt=2, 
                rand_move_chance=0, 
                after_click_settle_chance=0
            )

            self.control.propose_break()

            if random.random() < self.cfg.chance_change_point:
                self.get_overlap_point()

            alched = self.alch_count - (i + 1)
            if not alched % 10:
                self.log.info(f'Remaining items: {alched}')

    def init(self):
        natty_count = self.client.get_item_cnt(self.cfg.nature_rune.name, min_confidence=.9)
        item_count = self.client.get_item_cnt(self.cfg.alch_item.id, min_confidence=.9)
        return natty_count, item_count
    
    def get_active_tab(self) -> ToolplaneTab:
        tab = self.client.toolplane.get_active_tab(self.client.get_screenshot())
        return tab
    
    def get_overlap_point(self):
        try:
            
            self.overlap_point = self.overlap.get_point_within()
            self.log.info('New Overlap point: %s', self.overlap_point)
        except AttributeError as exc:
            raise RuntimeError('Make sure the item and high alch are on top of each other') from exc
        
    
    def find_overlap(self, identifier):
        item_match = self.client.find_item(identifier, min_confidence=.9)

        self.client.click_toolplane(ToolplaneTab.SPELLS)

        alch_img = Image.open('data/spells/high-level-alchemy.png')


        alch_match = self.client.find_in_window(
            alch_img,
            sub_match=self.client.sectors.toolplane,
            min_scale=.5
        )
        self.log.info(f'Found alch match: {alch_match}')

        self.overlap = alch_match.find_overlap(item_match)

        if not self.overlap:
            self.client.click_toolplane(ToolplaneTab.INVENTORY)
            try:
                self.client.move_to(item_match)
                pyautogui.mouseDown(button='left')
                self.client.move_to(
                    alch_match.get_center(),
                    rand_move_chance=0,
                )
            finally:
                time.sleep(0.25)
                pyautogui.mouseUp(button='left')
            # risk for endless loop but idc rn
            self.find_overlap(identifier) 

                

        
    




