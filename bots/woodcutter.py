from bots.core import BotConfigMixin
from bots.core.cfg_types import BooleanParam, StringParam, IntParam, FloatParam, RGBParam, RangeParam, BreakCfgParam
from core.bot import Bot
from core.bank import BankInterface

from core import tools
from core.region_match import MatchResult
from core.osrs_client import ToolplaneTab
from core.control import ScriptControl

from PIL import Image
import random
import time
import pyautogui
from core.logger import get_logger
import sys
import keyboard

class BotConfig(BotConfigMixin):
    # Configuration parameters
    name: str = "Woodcutter Bot"
    description: str = "A bot that chops trees and drops logs when inventory is full"

    tree_tile: RGBParam = RGBParam(255, 0, 255)  # Magenta by default
    log_type: StringParam = StringParam("Blisterwood logs")  # Default log name
    
    # Retry configuration
    max_retries: IntParam = IntParam(3)  # Maximum number of retries before giving up
    
    # Optional configuration
    chop_click_delay: RangeParam = RangeParam(0.2, 0.5)
    inventory_check_delay: RangeParam = RangeParam(3.0, 5.0)
    
    break_cfg: BreakCfgParam = BreakCfgParam(
        RangeParam(10, 30),  # break duration range in seconds
        FloatParam(0.01)     # break chance
    )

class BotExecutor(Bot):
    def __init__(self, config: BotConfig, user=''):
        super().__init__(user, break_cfg=config.break_cfg)
        self.cfg: BotConfig = config
        self.log = get_logger('WoodcutterBot')
        self.consecutive_failures = 0
        
    def start(self):
        self.log.info(f"Starting Woodcutter Bot for {self.cfg.log_type.value}")
        
        while True:
            try:
                # Check if inventory is full
                if self.check_inventory_full():
                    self.log.info("Inventory is full. Dropping logs...")
                    self.drop_logs()
                
                # Check if we're woodcutting, if not, click on tree
                if not self.client.is_woodcutting:
                    self.log.info("Not woodcutting. Clicking tree...")
                    self.chop_tree()
                
                # Wait a bit before checking status again
                time.sleep(self.cfg.inventory_check_delay.choose())
                
                # Reset consecutive failures counter on successful cycle
                self.consecutive_failures = 0

                # Check if we should propose a break
                self.control.propose_break()
                
            except Exception as e:
                self.consecutive_failures += 1
                self.log.error(f"Error in woodcutting process: {e}")
                
                if self.consecutive_failures > self.cfg.max_retries.value:
                    self.log.critical(f"Failed {self.consecutive_failures} times in a row. Exiting.")
                    sys.exit(1)
                else:
                    self.log.warning(f"Retry attempt {self.consecutive_failures}/{self.cfg.max_retries.value}")
                    time.sleep(3)  # Wait a bit before retrying
    
    def chop_tree(self):
        """Click on the tree tile to start chopping"""
        max_attempts = 2
        for attempt in range(max_attempts):
            try:
                self.client.smart_click_tile(
                    self.cfg.tree_tile.value,
                    ['chop', 'tree'],
                    retry_hover=5
                )
                time.sleep(self.cfg.chop_click_delay.choose())
                break
            except Exception as e:
                if attempt == max_attempts - 1:
                    raise RuntimeError(f"Failed to click tree tile after {max_attempts} attempts: {e}")
                self.log.warning(f"Failed to click tree tile (attempt {attempt+1}/{max_attempts}): {e}")
                time.sleep(1)
        
        # Wait until character stops moving
        start_time = time.time()
        timeout = 15  # Timeout after 15 seconds
        
        while time.time() - start_time < timeout:
            if not self.client.is_moving():
                break
            time.sleep(0.2)
    
    def check_inventory_full(self):
        """Check if inventory is full by looking for logs"""
        try:
            # Click inventory tab to ensure we can see items
            self.client.click_toolplane(ToolplaneTab.INVENTORY)
            time.sleep(0.5)
            
            # Try to find logs in inventory
            logs = self.client.get_inv_items([self.cfg.log_type.value], min_confidence=0.9)
            
            # Count the logs - if we have 28, inventory is full
            self.log.info(f"Found {len(logs)} logs in inventory")
            return len(logs) >= 28
            
        except Exception as e:
            self.log.warning(f"Error checking inventory: {e}")
            return False
    
    def drop_logs(self):
        """Drop all logs from inventory"""
        try:
            # Make sure inventory tab is open
            self.client.click_toolplane(ToolplaneTab.INVENTORY)
            time.sleep(0.5)
            
            # Find all logs in inventory
            logs = self.client.get_inv_items([self.cfg.log_type.value], min_confidence=0.9)
            
            if not logs:
                self.log.warning(f"No {self.cfg.log_type.value} found in inventory to drop")
                return
            
            self.log.info(f"Dropping {len(logs)} logs")
            
            try:
                keyboard.press('shift')
                # Drop each log
                for log_match in logs:
                    # Right-click on the log

                    self.client.click(log_match, rand_move_chance=0, after_click_settle_chance=0)  # 2 for right-click
                    
            finally:
                keyboard.release('shift')
            self.log.info("All logs dropped")
            
        except Exception as e:
            raise RuntimeError(f"Failed to drop logs: {e}")

# For direct execution
if __name__ == "__main__":
    config = BotConfig()
    # Override default values if needed
    # config.log_type.value = "Oak logs"
    
    bot = BotExecutor(config)
    bot.start()
