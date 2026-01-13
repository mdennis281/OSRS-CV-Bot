from bots.core import BotConfigMixin
from bots.core.cfg_types import RangeParam, BreakCfgParam, RGBParam, ItemParam
from core.bot import Bot
from core.bank import BankInterface

from core import tools
from core.region_match import MatchResult
from core.osrs_client import ToolplaneTab
from core.control import ScriptControl, ScriptTerminationException

from PIL import Image
import random
import time
import pyautogui
from core.logger import get_logger
import sys
import keyboard

control = ScriptControl()

"""
[
{"regionId":14936,"regionX":50,"regionY":41,"z":0,"color":"#FFFF0000"},
{"regionId":14936,"regionX":50,"regionY":40,"z":0,"color":"#FFFF0028"},
{"regionId":14936,"regionX":50,"regionY":39,"z":0,"color":"#FFFF0050"},
{"regionId":14936,"regionX":50,"regionY":38,"z":0,"color":"#FFFF0078"},
{"regionId":14936,"regionX":43,"regionY":45,"z":0,"color":"#FFFF00FF"},
{"regionId":14936,"regionX":36,"regionY":27,"z":0,"color":"#FF6432C8"},
{"regionId":14936,"regionX":47,"regionY":32,"z":0,"color":"#FF006464"},
{"regionId":14936,"regionX":43,"regionY":42,"z":0,"color":"#FFFF7000"},
{"regionId":14936,"regionX":43,"regionY":41,"z":0,"color":"#FF6CFFFF"}
]
"""

class BotConfig(BotConfigMixin):
    # Configuration parameters

    # Ore vein tile colors
    vein_tile_1: RGBParam = RGBParam.from_tuple((255, 0, 0))
    vein_tile_2: RGBParam = RGBParam.from_tuple((255, 0, 40))
    vein_tile_3: RGBParam = RGBParam.from_tuple((255, 0, 80))
    vein_tile_4: RGBParam = RGBParam.from_tuple((255, 0, 120))

    sack_size: int = 189  # Maximum pay-dirt in hopper
    
    # Items
    paydirt_item: ItemParam = ItemParam("Pay-dirt")
    gem_types: list[ItemParam] = [
        ItemParam("Uncut emerald"),
        ItemParam("Uncut ruby"), 
        ItemParam("Uncut sapphire"),
        ItemParam("Uncut diamond")
    ]
    
    # Other action tiles
    hopper_tile: RGBParam = RGBParam.from_tuple((255, 0, 255))
    down_ladder_tile: RGBParam = RGBParam.from_tuple((255, 112, 0))  # Orange - TOP of ladder
    sack_tile: RGBParam = RGBParam.from_tuple((100, 50, 200))
    bank_tile: RGBParam = RGBParam.from_tuple((0, 100, 100))
    up_ladder_tile: RGBParam = RGBParam.from_tuple((108, 255, 255))  # Cyan - BOTTOM of ladder
    
    # Retry configuration
    max_retries: int = 5
    fail_retry_delay: float = 1.5
    
    # Break configuration
    break_cfg: BreakCfgParam = BreakCfgParam(
        RangeParam(15, 45),  # break duration range in seconds
        0.01     # break chance
    )

class BotExecutor(Bot):
    name: str = "Motherload Miner Bot"
    description: str = "A bot that mines in the Motherload Mine, deposits ore, collects processed ore, and banks it"
    tier: str = "C"
    instructions: str = """
    This bot is designed to work after the 2nd floor is unlocked, alongside the upstairs hopper.
    It will mine pay-dirt, deposit it in the hopper, collect processed ore from the sack downstairs, and bank it.
    
    It needs to be babysat, has trouble determining if it's upstairs or downstairs sometimes.
    
    Tiles I use:
    [
    {"regionId":14936,"regionX":50,"regionY":41,"z":0,"color":"#FFFF0000"},
    {"regionId":14936,"regionX":50,"regionY":40,"z":0,"color":"#FFFF0028"},
    {"regionId":14936,"regionX":50,"regionY":39,"z":0,"color":"#FFFF0050"},
    {"regionId":14936,"regionX":50,"regionY":38,"z":0,"color":"#FFFF0078"},
    {"regionId":14936,"regionX":43,"regionY":45,"z":0,"color":"#FFFF00FF"},
    {"regionId":14936,"regionX":36,"regionY":27,"z":0,"color":"#FF6432C8"},
    {"regionId":14936,"regionX":47,"regionY":32,"z":0,"color":"#FF006464"},
    {"regionId":14936,"regionX":43,"regionY":42,"z":0,"color":"#FFFF7000"},
    {"regionId":14936,"regionX":43,"regionY":41,"z":0,"color":"#FF6CFFFF"}
    ]
    """
    
    def __init__(self, config: BotConfig, user=''):
        super().__init__(user, break_cfg=config.break_cfg)
        self.cfg: BotConfig = config
        self.log = get_logger('MotherloadMinerBot')
        self.vein_index = 0  # Used to cycle through veins
        self.upstairs = None  # Track if we're upstairs or downstairs
        self.hopper_count = 0  # Track how much paydirt is in the hopper
        self.terminate = False  # Flag to control script termination
        self.loop_cnt = int(config.sack_size / 27)  # Number of times to loop through mining and banking
        
    def start(self):
        self.log.info("Starting Motherload Miner Bot")
        
        try:
            # Determine initial position and go upstairs if needed
            self.detect_location()
            
            if not self.upstairs:
                self.log.info("Currently downstairs. Climbing up to start mining.")
                if not self.climb_up_ladder():
                    raise RuntimeError("Failed to climb up ladder to start mining.")
            
            # Main mining loop
            while not self.terminate:
                
                # Mine and deposit cycle (repeat X times)
                for cycle in range(self.loop_cnt):
                    self.log.info(f"Starting mining cycle {cycle+1}/{self.loop_cnt}")
                    if not self.mine_until_full():
                        self.log.warning("Failed to complete mining cycle. Trying to recover...")
                        if not self.detect_location() or not self.upstairs:
                            self.log.error("Unable to continue mining. Restarting mining cycle.")
                            break
                    
                    if not self.deposit_paydirt():
                        self.log.warning("Failed to deposit pay-dirt. Trying to recover...")
                        if not self.detect_location() or not self.upstairs:
                            self.log.error("Unable to deposit pay-dirt. Restarting mining cycle.")
                            break
                
                # After X cycles, go down to collect and bank
                if not self.climb_down_ladder():
                    self.log.error("Failed to climb down ladder. Retrying...")
                    if not self.detect_location() or self.upstairs:
                        self.log.error("Unable to proceed to banking area. Restarting...")
                        continue
                
                # Search sack, bank, climb up - repeat X times
                for cycle in range(self.loop_cnt):
                    self.log.info(f"Starting banking cycle {cycle+1}/{self.loop_cnt}")
                    if not self.search_sack():
                        raise RuntimeError("Failed to search sack for processed ore")
                    
                    if not self.bank_ore():
                        self.log.warning("Failed to bank ore. Trying to recover...")
                        raise RuntimeError("Banking failed")
                    
                if not self.climb_up_ladder():
                    self.log.warning("Failed to climb up ladder. Trying to recover...")
                    if not self.detect_location() or not self.upstairs:
                        self.log.error("Unable to climb up ladder. Restarting banking cycle.")
                        break
                
                # Check if we should take a break
                self.control.propose_break()
                
        except ScriptTerminationException as e:
            self.log.info(f"Script termination requested: {e}")
            self.log.info("Exiting Motherload Miner Bot")
            self.terminate = True
    
    def detect_location(self):
        """Detect if we are upstairs (mining area) or downstairs (banking area)"""
        self.log.info("Detecting current location...")
        
        try:
            tile = tools.find_color_box(
                self.client.get_filtered_screenshot(),
                self.cfg.down_ladder_tile,
                tol=40
            )
            for x in range(3):
                self.client.move_to(
                    tile,
                    rand_move_chance=0.1,
                )
                for t in self.client.get_hover_texts():
                    if 'ladder' in t.lower() or 'climb' in t.lower():
                        self.upstairs = True
                        return True
            self.upstairs = False
            return False
        except Exception as e:
            self.log.error(f"Error detecting location: {e}")
            self.upstairs = False
            return False
    
    @control.guard
    def drop_gems(self):
        """Drop any uncut gems in the inventory"""
        try:
            # Make sure inventory tab is active
            self.client.click_toolplane(ToolplaneTab.INVENTORY)
            time.sleep(0.5)
            
            # Check for gems
            gem_names = [gem.name for gem in self.cfg.gem_types]
            gems = self.client.get_inv_items(gem_names, min_confidence=0.98)
            
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
        
    @control.guard
    def mine_until_full(self):
        """Mine ore veins until inventory is full (27 Pay-dirt)"""
        self.log.info("Mining until inventory is full")
        
        fail_count = 0
        while not self.is_inventory_full():
            self.control.propose_break()
            # Check if the hopper is full
            if self.hopper_count >= self.cfg.sack_size:
                self.log.warning("Hopper is full (%d/%d). Cannot mine until emptied.", self.hopper_count, self.cfg.sack_size)
                return False
                
            # Check for and drop any gems
            self.drop_gems()
            
            if self.client.is_mining:
                self.log.debug("Currently mining...")
                time.sleep(1)
                continue
                
            self.log.info("Not mining, attempting to mine ore...")
            if self.mine_ore():
                self.log.debug("Successfully clicked on ore vein")
                fail_count = 0  # Reset fail counter on success
                time.sleep(1)
            else:
                fail_count += 1
                self.log.warning("Failed to find ore vein (%d/%d)", fail_count, self.cfg.max_retries)
                if fail_count >= self.cfg.max_retries:
                    self.log.error("Too many failures. Giving up mining cycle.")
                    self.deposit_paydirt()
                    self.climb_down_ladder()
                    return False
                time.sleep(self.cfg.fail_retry_delay)
        
        return True
    @control.guard
    def mine_ore(self):
        """Attempt to mine an ore vein by cycling through different tile colors"""
        # List of tile colors to try
        vein_tiles = [
            self.cfg.vein_tile_1,
            self.cfg.vein_tile_2,
            self.cfg.vein_tile_3,
            self.cfg.vein_tile_4
        ]
        
        # Cycle through the veins
        current_vein = vein_tiles[self.vein_index]
        self.vein_index = (self.vein_index + 1) % len(vein_tiles)
        
        try:
            self.client.smart_click_tile(
                current_vein,
                ['mine', 'ore', 'vein'],
                retry_hover=3,
                retry_match=2
            )
            
            # Wait for character to stop moving
            while self.client.is_moving(): 
                continue
                
            return True
        except Exception as e:
            self.log.error("Error mining ore: %s", e)
            return False
    
    def is_inventory_full(self):
        """Check if inventory has 27 or more Pay-dirt"""
        try:
            # Make sure inventory tab is active
            self.client.click_toolplane(ToolplaneTab.INVENTORY)
            time.sleep(0.5)
            
            # Get all Pay-dirt in inventory
            pay_dirt = self.client.get_inv_items([self.cfg.paydirt_item.name], min_confidence=0.9)
            count = len(pay_dirt)
            
            self.log.debug("Found %d Pay-dirt in inventory", count)
            return count >= 27
        except Exception as e:
            self.log.warning("Error checking inventory: %s", e)
            return False
    @control.guard
    def deposit_paydirt(self):
        """Deposit Pay-dirt in the hopper"""
        self.log.info("Depositing Pay-dirt in hopper")
        
        try:
            # Count the pay-dirt we're about to deposit
            self.client.click_toolplane(ToolplaneTab.INVENTORY)
            time.sleep(0.5)
            pay_dirt = self.client.get_inv_items([self.cfg.paydirt_item.name], min_confidence=0.9)
            count = len(pay_dirt)
            
            # Check if depositing would exceed hopper capacity
            if self.hopper_count + count > self.cfg.sack_size:
                self.log.warning("Hopper nearly full (%d/%d). Depositing would exceed capacity.", self.hopper_count, self.cfg.sack_size)
                return False
            
            # Click on the hopper
            self.client.smart_click_tile(
                self.cfg.hopper_tile,
                ['deposit', 'hopper'],
                retry_hover=3,
                retry_match=2
            )
            
            # Wait for character to stop moving
            while self.client.is_moving(): 
                continue
                
            time.sleep(2)  # Wait for deposit animation
            
            # Update hopper count
            self.hopper_count += count
            self.log.info("Deposited %d pay-dirt. Hopper now at %d/%d", count, self.hopper_count, self.cfg.sack_size)
            
            return True
        except Exception as e:
            self.log.error("Error depositing Pay-dirt: %s", e)
            return False
    @control.guard
    def climb_down_ladder(self):
        """Climb down the ladder to the collection area"""
        self.log.info("Climbing down ladder")
        
        if not self.upstairs:
            self.log.warning("Already downstairs. Skipping climb down.")
            return True
        
        try:
            # Click on the down ladder (orange)
            self.client.smart_click_tile(
                self.cfg.down_ladder_tile,
                ['climb', 'ladder'],
                retry_hover=3,
                retry_match=3
            )
            
            # Wait for character to stop moving
            while self.client.is_moving(): 
                continue
                
            time.sleep(1)  # Give time for the climbing animation
            self.upstairs = False
            
            return True
        except Exception as e:
            self.log.error("Error climbing down ladder: %s", e)
            return False
    @control.guard
    def search_sack(self):
        """Search the sack to collect processed ore"""
        self.log.info("Searching sack for processed ore")
        
        if self.upstairs:
            self.log.warning("Currently upstairs. Cannot search sack from here.")
            return False
        
        try:
            # Click on the sack
            self.client.smart_click_tile(
                self.cfg.sack_tile,
                ['search', 'sack'],
                retry_hover=3,
                retry_match=10
            )
            
            # Wait for character to stop moving
            while self.client.is_moving(): 
                continue
                
            time.sleep(2)  # Wait for search animation
            
            # Reset hopper count since we've emptied the sack
            self.hopper_count = 0
            self.log.info("Emptied sack. Hopper count reset to 0/%d", self.cfg.sack_size)
            
            return True
        except Exception as e:
            self.log.error("Error searching sack: %s", e)
            return False
    @control.guard
    def bank_ore(self):
        """Bank the processed ore"""
        self.log.info("Banking processed ore")
        
        if self.upstairs:
            self.log.warning("Currently upstairs. Cannot bank from here.")
            return False
        
        try:
            # Click on the bank
            self.client.smart_click_tile(
                self.cfg.bank_tile,
                ['bank', 'deposit'],
                retry_hover=3,
                retry_match=10
            )
            
            # Wait for character to stop moving
            while self.client.is_moving(): 
                continue
            
            # Wait for bank to open
            for _ in range(10):
                if self.control.terminate: 
                    return False
                    
                try:
                    deposit = self.client.find_in_window(
                        Image.open('data/ui/bank-deposit-inv.png'), 
                        min_confidence=0.9
                    )
                    exit = self.client.find_in_window(
                        Image.open('data/ui/close-ui-element.png'), 
                        min_confidence=0.9
                    )
                except Exception as e:
                    self.log.error("%s", e)
                    self.log.warning("Deposit button not found, retrying...")
                    continue
                    
                # Click deposit button
                self.client.click(deposit)
                time.sleep(random.uniform(.3, 2))
                
                # Close bank
                self.client.click(exit)
                return True
            
            self.log.error("Failed to open bank interface after multiple attempts")    
            return False
                
        except Exception as e:
            self.log.error("Error banking ore: %s", e)
            return False
    @control.guard
    def climb_up_ladder(self):
        """Climb up the ladder back to the mining area"""
        self.log.info("Climbing up ladder")
        
        if self.upstairs:
            self.log.warning("Already upstairs. Skipping climb up.")
            return True
        
        for attempt in range(self.cfg.max_retries):
            try:
                # Click on the up ladder (cyan)
                self.client.smart_click_tile(
                    self.cfg.up_ladder_tile,
                    ['climb', 'ladder'],
                    retry_hover=3,
                    retry_match=3
                )
                
                # Wait for character to stop moving
                while self.client.is_moving(): 
                    continue
                
                time.sleep(1)  # Give time for the climbing animation
                self.upstairs = True
                
                return True
            except Exception as e:
                self.log.warning("Error climbing up ladder (attempt %d/%d): %s", attempt+1, self.cfg.max_retries, e)
                time.sleep(self.cfg.fail_retry_delay)
                
        self.log.error("Failed to climb up ladder after all retries")
        return False

# For direct execution
if __name__ == "__main__":
    config = BotConfig()
    bot = BotExecutor(config)
    bot.start()
