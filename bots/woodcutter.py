from bots.core import BotConfigMixin
from bots.core.cfg_types import BooleanParam, StringParam, IntParam, FloatParam, RGBParam, RangeParam, BreakCfgParam, RGBListParam, RouteParam, WaypointParam, ItemParam
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

    # Tree configuration
    tree_tiles: RGBListParam = RGBListParam([
        RGBParam(255, 0, 255),  # Magenta by default
        RGBParam(255, 0, 200),  # Another shade
        #RGBParam(255, 0, 150),  # Yet another shade
    ])
    # Retry configuration
    max_retries: IntParam = IntParam(3)  # Maximum number of retries before giving up
    
    # Optional configuration
    chop_click_delay: RangeParam = RangeParam(0.2, 0.5)
    inventory_check_delay: RangeParam = RangeParam(3.0, 5.0)
    
    break_cfg: BreakCfgParam = BreakCfgParam(
        RangeParam(10, 30),  # break duration range in seconds
        FloatParam(0.01)     # break chance
    )

    ###########################################
    # Willows at Draynor Village
    ###########################################
    log_type: ItemParam = ItemParam("Willow logs")  # Default log name
    drop_items: BooleanParam = BooleanParam(False)  # True = drop logs, False = bank logs
    bank_tile: RGBParam = RGBParam(0, 255, 0)  # Green by default, only used when banking
    bank_to_trees: RouteParam = RouteParam([
        # WaypointParam(3094, 3244, 0, 790933, 8),
        WaypointParam(3105, 3240, 0, 790932, 8),
        WaypointParam(3091, 3230, 0, 790932, 5)
    ])  # Empty default route, configure in UI
    inv_full_at: IntParam = IntParam(27)  # Default inventory capacity

    
    
    ###########################################
    # Oaks at east Varrock
    ###########################################
    # log_type: StringParam = StringParam("Oak logs")  # Default log name
    # drop_items: BooleanParam = BooleanParam(False)  # True = drop logs, False = bank logs
    # bank_tile: RGBParam = RGBParam(0, 255, 0)  # Green by default, only used when banking
    # bank_to_trees: RouteParam = RouteParam([
    #     WaypointParam(3253, 3428, 0, 838060, 5),
    #     WaypointParam(3275, 3428, 0, 838060, 5)
    # ])  # Empty default route, configure in UI
    # inv_full_at: IntParam = IntParam(28)  # Default inventory capacity
    
    
class BotExecutor(Bot):
    name: str = "Woodcutter Bot"
    description: str = "A bot that chops trees and banks or drops logs when inventory is full"
    tier: str = "B"
    instructions: str = """
    This bot will chop trees of the specified type and either drop or bank the logs when the inventory is full.
    Banking function will drop reliability since the movement orchestrator is not perfect.
    Dropping should be more reliable but not profitable.
    """
    
    
    def __init__(self, config: BotConfig, user=''):
        super().__init__(user, break_cfg=config.break_cfg)
        self.cfg: BotConfig = config
        self.log = get_logger('WoodcutterBot')
        self.consecutive_failures = 0
        self.tree_index = 0  # Used to cycle through tree tiles
        
        if not self.cfg.drop_items.value and not self.cfg.bank_to_trees.value:
            self.log.warning("Banking enabled but no route specified. Please set bank_to_trees in the config.")
            
        if not self.cfg.drop_items.value:
            self.bank = BankInterface(self.client, self.client.item_db)
        
    def start(self):
        self.log.info(f"Starting Woodcutter Bot for {self.cfg.log_type.name}")
        
        while True:
            try:
                # Check if inventory is full
                if self.check_inventory_full():
                    if self.cfg.drop_items.value:
                        self.log.info("Inventory is full. Dropping logs...")
                        self.drop_logs()
                    else:
                        self.log.info("Inventory is full. Banking logs...")
                        # Travel to bank
                        self.log.info("Traveling to bank...")
                        try:
                            self.mover.execute_route(self.cfg.bank_to_trees.reverse())
                        except Exception as e:
                            self.log.error(f"Failed to travel to bank: {e}")
                            # retry once
                            self.mover.execute_route(self.cfg.bank_to_trees.reverse())
                            
                        # Bank items
                        if not self.bank_logs():
                            self.log.error("Failed to bank logs. Retrying...")
                            continue
                            
                        # Return to trees
                        self.log.info("Returning to trees...")
                        try:
                            self.mover.execute_route(self.cfg.bank_to_trees)
                        except Exception as e:
                            self.log.error(f"Failed to return to trees: {e}")
                            # retry once
                            self.mover.execute_route(self.cfg.bank_to_trees)
                
                # Check if we're woodcutting, if not, click on tree
                if not self.client.is_woodcutting:
                    try:
                        self.log.info("Not woodcutting. Clicking tree...")
                        self.chop_tree()
                    except Exception as e:
                        self.log.warning(f"Did we die or something? walking to trees: {e}")
                        self.mover.execute_route(self.cfg.bank_to_trees)
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
        """Click on a tree tile to start chopping, cycling through available tiles"""
        tree_tiles = self.cfg.tree_tiles.value
        
        if not tree_tiles:
            self.log.error("No tree tile colors specified")
            return False
        
        # Get the next tree tile in the cycle
        current_tree = tree_tiles[self.tree_index % len(tree_tiles)]
        self.tree_index += 1
        
        max_attempts = 2
        for attempt in range(max_attempts):
            try:
                self.client.smart_click_tile(
                    current_tree.value,
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
        """Check if inventory has the specified number of logs"""
        try:
            # Click inventory tab to ensure we can see items
            self.client.click_toolplane(ToolplaneTab.INVENTORY)
            time.sleep(0.5)
            
            # Try to find logs in inventory
            logs = self.client.get_inv_items([self.cfg.log_type.name], min_confidence=0.9)
            
            # Count the logs
            log_count = len(logs)
            self.log.info(f"Found {log_count} logs in inventory")
            
            # Check if we've reached the full inventory threshold
            return log_count >= self.cfg.inv_full_at.value
            
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
            logs = self.client.get_inv_items([self.cfg.log_type.name], min_confidence=0.9)
            
            if not logs:
                self.log.warning(f"No {self.cfg.log_type.name} found in inventory to drop")
                return
            
            self.log.info(f"Dropping {len(logs)} logs")
            
            try:
                keyboard.press('shift')
                # Drop each log
                for log_match in logs:
                    self.client.click(log_match, rand_move_chance=0, after_click_settle_chance=0)
                    time.sleep(random.uniform(0.1, 0.3))
            finally:
                keyboard.release('shift')
            self.log.info("All logs dropped")
            
        except Exception as e:
            raise RuntimeError(f"Failed to drop logs: {e}")
    
    def bank_logs(self):
        """Bank all logs and prepare for the next woodcutting run"""
        self.log.info("Banking logs...")
        
        try:
            # Click on the bank tile
            self.client.smart_click_tile(
                self.cfg.bank_tile.value,
                ['bank', 'banker', 'booth', 'chest'],
                retry_hover=3,
                retry_match=2,
                filter_ui=True
            )
            
            # Wait for character to stop moving
            while self.client.is_moving():
                time.sleep(0.2)
            
            # Wait for bank interface to open
            timeout = 5
            start_time = time.time()
            while not self.bank.is_open:
                if time.time() - start_time > timeout:
                    self.log.warning("Timed out waiting for bank to open")
                    return False
                time.sleep(0.5)
            
            # Deposit all items
            self.bank.deposit_inv()
            time.sleep(random.uniform(0.5, 1.0))
            
            # Close bank
            self.bank.close()
            return True
            
        except Exception as e:
            self.log.error(f"Error banking logs: {e}")
            return False

# For direct execution
if __name__ == "__main__":
    config = BotConfig()
    # Override default values if needed
    # config.log_type.value = "Oak logs"
    
    bot = BotExecutor(config)
    bot.start()
