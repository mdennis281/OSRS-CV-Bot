from bots.core import BotConfigMixin
from bots.core.cfg_types import BooleanParam, StringParam, IntParam, FloatParam, RGBParam, RangeParam, BreakCfgParam, ItemParam
from core.bot import Bot

from core import tools
from core.region_match import MatchResult
from core.osrs_client import ToolplaneTab

import random
import time
import pyautogui
from core.logger import get_logger

class BotConfig(BotConfigMixin):
    # Configuration parameters

    item1: ItemParam = ItemParam("Mithril dart tip")
    item2: ItemParam = ItemParam("Feather")
    
    # Min confidence for item recognition
    item1_confidence: FloatParam = FloatParam(0.8)
    item2_confidence: FloatParam = FloatParam(0.8)
    
    # Wait time after pressing spacebar before next cycle
    craft_wait_time: RangeParam = RangeParam(10.0, 14.0)
    
    # Delay between clicking items
    click_delay: RangeParam = RangeParam(0.3, 0.7)
    
    # Break configuration
    break_cfg: BreakCfgParam = BreakCfgParam(
        RangeParam(30, 90),  # break duration range in seconds
        FloatParam(0.02)     # break chance
    )

class BotExecutor(Bot):
    name: str = "Dart Fletcher Bot"
    description: str = "A bot that fletches darts by clicking dart tips and feathers, then pressing spacebar."
    tier: str = "S"
    instructions: str = """
    This bot fletches darts by clicking on dart tips and feathers in the inventory, then pressing spacebar to start crafting.
    
    Pretty basic, but it definitely gets the job done.
    """

    def __init__(self, config: BotConfig, user=''):
        super().__init__(user, break_cfg=config.break_cfg)
        self.cfg: BotConfig = config
        self.log = get_logger('DartFletcher')
        
        self.initial_item1_count = 0
        self.initial_item2_count = 0
        self.current_item1_count = 0
        self.current_item2_count = 0
        self.darts_crafted = 0
        
    def start(self):
        self.log.info("Starting Dart Fletcher Bot")
        
        # Get initial counts
        self.get_initial_counts()
        
        if self.initial_item1_count == 0 or self.initial_item2_count == 0:
            self.log.error(f"Missing required items: {self.cfg.item1.name}={self.initial_item1_count}, {self.cfg.item2.name}={self.initial_item2_count}")
            return
            
        self.log.info(f"Starting with {self.initial_item1_count} {self.cfg.item1.name} and {self.initial_item2_count} {self.cfg.item2.name}")
        
        # Main loop
        self.loop()

    def loop(self):
        """Main crafting loop"""
        while True:
            # Check if we still have materials
            if not self.check_materials():
                self.log.info("No more materials available. Stopping.")
                break
            
            # Ensure we're on inventory tab
            self.ensure_inventory_tab()
            
            # Randomly choose which item to click first
            if random.choice([True, False]):
                self.click_items_in_order(self.cfg.item1.name, self.cfg.item2.name)
            else:
                self.click_items_in_order(self.cfg.item2.name, self.cfg.item1.name)
            
            # Press spacebar to start crafting
            self.press_spacebar()
            
            # Wait for crafting to complete
            craft_time = self.cfg.craft_wait_time.choose()
            self.log.info(f"Waiting {craft_time:.1f}s for crafting to complete")
            time.sleep(craft_time)
            
            # Update counts and stats
            self.update_counts()
            
            # Propose break
            self.control.propose_break()

    def get_initial_counts(self):
        """Get initial item counts"""
        try:
            self.initial_item1_count = self.client.get_item_cnt(self.cfg.item1.name, min_confidence=self.cfg.item1_confidence.value)
            self.initial_item2_count = self.client.get_item_cnt(self.cfg.item2.name, min_confidence=self.cfg.item2_confidence.value)
            self.current_item1_count = self.initial_item1_count
            self.current_item2_count = self.initial_item2_count
        except Exception as e:
            self.log.error(f"Failed to get initial item counts: {e}")
            self.initial_item1_count = 0
            self.initial_item2_count = 0

    def check_materials(self, is_retry = False):
        """Check if we still have materials to craft"""
        try:
            self.current_item1_count = self.client.get_item_cnt(self.cfg.item1.name, min_confidence=self.cfg.item1_confidence.value)
            self.current_item2_count = self.client.get_item_cnt(self.cfg.item2.name, min_confidence=self.cfg.item2_confidence.value)
            
            return self.current_item1_count > 0 and self.current_item2_count > 0
        except Exception as e:
            self.log.warning(f"Failed to check material counts: {e}")
            if not is_retry:
                self.log.info('Trying to recover from error...')
                self.client.click_toolplane(ToolplaneTab.SKILLS)
                time.sleep(random.uniform(5,10))
                self.client.click_toolplane(ToolplaneTab.INVENTORY)
                self.check_materials(is_retry=True)
            return False

    def ensure_inventory_tab(self):
        """Ensure we're on the inventory tab"""
        try:
            current_tab = self.client.toolplane.get_active_tab(self.client.get_screenshot())
            if current_tab != ToolplaneTab.INVENTORY:
                self.client.click_toolplane(ToolplaneTab.INVENTORY)
                time.sleep(0.5)
        except Exception as e:
            self.log.warning(f"Failed to check/switch to inventory tab: {e}")

    def click_items_in_order(self, first_item: str, second_item: str):
        """Click two items in the specified order"""
        try:
            # Determine confidence for each item
            first_confidence = self.cfg.item1_confidence.value if first_item == self.cfg.item1.name else self.cfg.item2_confidence.value
            second_confidence = self.cfg.item2_confidence.value if second_item == self.cfg.item2.name else self.cfg.item1_confidence.value
            

            # Find and click first item
            first_item_match = self.client.find_item(first_item, min_confidence=first_confidence)
            if not first_item_match:
                raise RuntimeError(f"Could not find {first_item} in inventory")
            
            self.client.smart_click_match(
                first_item_match, 
                hover_texts=['use'] + first_item.split(' '),
            )
            self.log.info(f"Clicked {first_item}")
            
            # Small delay between clicks
            time.sleep(self.cfg.click_delay.choose())
            
            # Find and click second item
            second_item_match = self.client.find_item(second_item, min_confidence=second_confidence)
            if not second_item_match:
                raise RuntimeError(f"Could not find {second_item} in inventory")
            
            self.client.smart_click_match(
                second_item_match, 
                hover_texts=['use'] + second_item.split(' '),
            )
            
            self.log.info(f"Clicked {second_item}")
            
        except Exception as e:
            self.log.error(f"Failed to click items: {e}")
            raise

    def press_spacebar(self):
        """Press spacebar to confirm crafting"""
        time.sleep(random.normalvariate(.8, .2))
        try:
            pyautogui.press('space')
            self.log.info("Pressed spacebar")
            time.sleep(0.5)  # Small delay after spacebar
        except Exception as e:
            self.log.error(f"Failed to press spacebar: {e}")

    def update_counts(self):
        """Update item counts and calculate darts crafted"""
        try:
            old_item1_count = self.current_item1_count
            old_item2_count = self.current_item2_count
            
            self.current_item1_count = self.client.get_item_cnt(self.cfg.item1.name, min_confidence=self.cfg.item1_confidence.value)
            self.current_item2_count = self.client.get_item_cnt(self.cfg.item2.name, min_confidence=self.cfg.item2_confidence.value)
            
            # Calculate items used in this cycle
            item1_used = old_item1_count - self.current_item1_count
            item2_used = old_item2_count - self.current_item2_count
            
            # Darts crafted is the minimum of items used (should be equal for successful crafting)
            if item1_used > 0 and item2_used > 0:
                darts_this_cycle = min(item1_used, item2_used)
                self.darts_crafted += darts_this_cycle
                
                self.log.info(f"Crafted {darts_this_cycle} darts this cycle. Total: {self.darts_crafted}")
                self.log.info(f"Remaining: {self.current_item1_count} {self.cfg.item1.name}, {self.current_item2_count} {self.cfg.item2.name}")
            
        except Exception as e:
            self.log.warning(f"Failed to update counts: {e}")
