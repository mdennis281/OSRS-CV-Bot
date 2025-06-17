from bots.core import BotConfigMixin
from bots.core.cfg_types import StringParam, IntParam, RGBParam, RGBListParam, RouteParam, BreakCfgParam, RangeParam, FloatParam, WaypointParam
from core.bot import Bot
from core.bank import BankInterface
from core.region_match import MatchResult
from core.osrs_client import ToolplaneTab
from core.control import ScriptTerminationException

from PIL import Image
import random
import time
import keyboard
from core.logger import get_logger
import sys

class BotConfig(BotConfigMixin):
    # Configuration parameters
    name: str = "Mining Bot"
    description: str = "A bot that mines ores and banks them"

    # Bank and mining configuration
    bank_tile: RGBParam = RGBParam(0, 255, 0)  # Yellow by default
    ore_type: StringParam = StringParam("Iron ore")  # Default ore type
    inv_full_at: IntParam = IntParam(27)  # Default inventory capacity (28 slots)
    ore_options: RGBListParam = RGBListParam([
        #RGBParam(255, 0, 0),     # Red
        #RGBParam(255, 0, 50),    # Pink-Red
        RGBParam(255, 0, 100),    # Darker Pink
        RGBParam(255, 0, 150),    # Darker Pink-Red
    ])
    bank_to_mine: RouteParam = RouteParam([
        WaypointParam(3253, 3424, 0, 831916, 5),
        WaypointParam(3286, 3430, 0, 840108, 5),
        WaypointParam(3293, 3406, 0, 842153, 5),
        WaypointParam(3294, 3374, 0, 842149, 5),
        WaypointParam(3286, 3366, 0, 840100, 5)
    ])
    
    # Optional configuration
    max_retries: IntParam = IntParam(30)  # Maximum retry attempts
    mine_click_delay: RangeParam = RangeParam(0.2, 0.5)  # Delay between mining clicks
    
    # Break configuration
    break_cfg: BreakCfgParam = BreakCfgParam(
        RangeParam(15, 45),  # break duration range in seconds
        FloatParam(0.01)     # break chance
    )

class BotExecutor(Bot):
    def __init__(self, config: BotConfig, user=''):
        super().__init__(user, break_cfg=config.break_cfg)
        self.cfg: BotConfig = config
        self.log = get_logger('MiningBot')
        self.bank = BankInterface(self.client, self.client.item_db)
        self.ore_index = 0  # Used to cycle through ore tiles
        self.consecutive_failures = 0
        
        if not self.cfg.bank_to_mine:
            self.log.error("No route specified. Please set bank_to_mine in the config.")
            raise ValueError("bank_to_mine route must be specified")
    
    def start(self):
        self.log.info(f"Starting Mining Bot for {self.cfg.ore_type.value}")
        
        try:
            while True:
                try:
                    # Start at the bank, then travel to mine
                    if not self.bank_items():
                        self.log.error("Failed to bank items. Retrying...")
                        self.consecutive_failures += 1
                        if self.consecutive_failures > self.cfg.max_retries.value:
                            raise RuntimeError("Too many consecutive banking failures")
                        continue
                    
                    # Travel to the mining site
                    self.log.info("Traveling to mine...")
                    try:
                        self.mover.execute_route(self.cfg.bank_to_mine)
                    except Exception as e:
                        self.log.error(f"Failed to travel to mine: {e}")
                        # restart once
                        self.mover.execute_route(self.cfg.bank_to_mine)
                    
                    # Mine until inventory is full
                    if not self.mine_until_full():
                        self.log.error("Failed to complete mining cycle. Retrying...")
                        continue
                    
                    # Return to bank
                    self.log.info("Returning to bank...")
                    try:
                        self.mover.execute_route(self.cfg.bank_to_mine.reverse())
                    except Exception as e:
                        self.log.error(f"Failed to return to bank: {e}")
                        # restart once
                        self.mover.execute_route(self.cfg.bank_to_mine.reverse())
                    
                    # Reset consecutive failures on successful cycle
                    self.consecutive_failures = 0
                    
                    # Check if we should propose a break
                    self.control.propose_break()
                
                except Exception as e:
                    if isinstance(e, ScriptTerminationException):
                        raise
                    
                    self.consecutive_failures += 1
                    self.log.error(f"Error in mining process: {e}")
                    
                    if self.consecutive_failures > self.cfg.max_retries.value:
                        self.log.critical(f"Failed {self.consecutive_failures} times in a row. Exiting.")
                        sys.exit(1)
                    else:
                        self.log.warning(f"Retry attempt {self.consecutive_failures}/{self.cfg.max_retries.value}")
                        time.sleep(3)  # Wait a bit before retrying
        
        except ScriptTerminationException as e:
            self.log.info(f"Script termination requested: {e}")
            self.log.info("Exiting Mining Bot")
        except Exception as e:
            self.log.error(f"Fatal error: {e}")
            raise
    
    def bank_items(self):
        """Bank all mined ores and prepare for the next mining run"""
        self.log.info("Banking items...")
        
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
            self.log.error(f"Error banking items: {e}")
            return False
    
    def mine_until_full(self):
        """Mine ore until inventory has the specified number of ores"""
        self.log.info(f"Mining until inventory has {self.cfg.inv_full_at.value} {self.cfg.ore_type.value}")
        
        failure_count = 0
        
        while self.get_ore_count() < self.cfg.inv_full_at.value:
            # Check for termination request
            if self.control.terminate:
                raise ScriptTerminationException()
            
            # Check for and drop any gems
            self.drop_gems()
            
            # Check if we're already mining
            if self.client.is_mining:
                self.log.debug("Currently mining...")
                time.sleep(1)
                continue
            
            # Try to click on an ore rock
            if self.mine_ore():
                self.log.debug("Successfully clicked on ore rock")
                failure_count = 0  # Reset failure counter on success
                
                # Wait for mining to start
                time.sleep(self.cfg.mine_click_delay.choose())
            else:
                failure_count += 1
                self.log.warning(f"Failed to find ore rock ({failure_count}/{self.cfg.max_retries.value})")
                
                if failure_count >= self.cfg.max_retries.value:
                    self.log.error("Too many failures. Giving up mining cycle.")
                    return False
                
                time.sleep(1)  # Wait before retrying
        
        self.log.info(f"Inventory full with {self.get_ore_count()} {self.cfg.ore_type.value}")
        return True
    
    def drop_gems(self):
        """Drop all types of gems found while mining"""
        try:
            # Make sure inventory tab is active
            self.client.click_toolplane(ToolplaneTab.INVENTORY)
            time.sleep(0.5)
            
            # Comprehensive list of all possible gems from mining
            gem_types = [
                "Uncut sapphire", 
                "Uncut emerald", 
                "Uncut ruby", 
                "Uncut diamond",
                "Uncut dragonstone",
                "Uncut onyx",
                "Uncut zenyte",
                "Uncut opal",
                "Uncut jade",
                "Uncut red topaz"
            ]
            
            gems = self.client.get_inv_items(gem_types, min_confidence=0.9)
            
            if gems:
                self.log.info(f"Found {len(gems)} gems to drop")
                
                # Hold shift while clicking each gem
                try:
                    keyboard.press('shift')
                    time.sleep(0.2)
                    
                    for gem in gems:
                        self.client.click(gem, rand_move_chance=0, after_click_settle_chance=0)
                        time.sleep(random.uniform(0.1, 0.3))
                    
                finally:
                    keyboard.release('shift')
                
                return True
            else:
                return False
                
        except Exception as e:
            self.log.warning(f"Error dropping gems: {e}")
            return False
    
    def mine_ore(self):
        """Click on an ore rock to start mining"""
        # Cycle through the ore tile colors
        ore_tiles = self.cfg.ore_options.value
        
        if not ore_tiles:
            self.log.error("No ore tile colors specified")
            return False
        
        current_ore = ore_tiles[self.ore_index % len(ore_tiles)]
        self.ore_index += 1
        
        try:
            self.client.smart_click_tile(
                current_ore.value,
                [ self.cfg.ore_type.value.split(' ')[0]],
                retry_hover=1,
                retry_match=1,
                filter_ui=True
            )
            
            # Wait for character to stop moving
            while self.client.is_moving():
                time.sleep(0.2)
            
            return True
        except Exception as e:
            self.log.error(f"Error mining ore: {e}")
            return False
    
    def get_ore_count(self):
        """Count the number of ores in the inventory"""
        try:
            # Make sure inventory tab is active
            self.client.click_toolplane(ToolplaneTab.INVENTORY)
            time.sleep(0.3)
            
            # Get all instances of the specified ore type in inventory
            ore_items = self.client.get_inv_items([self.cfg.ore_type.value], min_confidence=0.9)
            count = len(ore_items)
            
            self.log.debug(f"Found {count} {self.cfg.ore_type.value} in inventory")
            return count
        except Exception as e:
            self.log.warning(f"Error checking inventory: {e}")
            return 0
