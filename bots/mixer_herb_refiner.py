from bots.core import BotConfigMixin
from bots.core.cfg_types import BooleanParam, StringParam, IntParam, FloatParam, RGBParam, RangeParam, BreakCfgParam, ItemParam
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

# TODO: 
    #  - handle level up during refining

class BotConfig(BotConfigMixin):
    
    # Configuration parameters


    bank_tile: RGBParam = RGBParam(255, 255, 0)  # Yellow
    refiner_tile: RGBParam = RGBParam(0, 255, 0)  # Green
    #herb_option: ItemParam = ItemParam("Grimy lantadyme")  # aga
    #herb_option: ItemParam = ItemParam("Grimy kwuarm") # lye
    #herb_option: ItemParam = ItemParam("Grimy tarromin")  # mox
    #herb_option: ItemParam = ItemParam("Grimy harralander")  # mox
    herb_option: ItemParam = ItemParam("Grimy toadflax")  # mox

    # Optional configuration
    deposit_delay: RangeParam = RangeParam(0.5, 1.5)
    withdraw_delay: RangeParam = RangeParam(0.5, 1.5)
    
    # Monitoring configuration
    stall_timeout: IntParam = IntParam(5)  # Time in seconds to wait before checking for stalled processing
    process_timeout: IntParam = IntParam(60)  # Total timeout for the entire herb processing
    
    # Retry configuration
    max_retries: IntParam = IntParam(2)  # Maximum number of retries before giving up
    
    break_cfg: BreakCfgParam = BreakCfgParam(
        RangeParam(15, 45),  # break duration range in seconds
        FloatParam(0.01)     # break chance
    )

class BotExecutor(Bot):
    name: str = "Mixer Herb Refiner"
    description: str = "A bot that withdraws herbs from the bank, cleans them if grimy, and refines them."
    tier: str = "A"
    instructions: str = """
    This bot automates the process of withdrawing herbs from the bank, cleaning them if they are grimy,
    and refining them using the Mixer Herb Refiner.
    Expected to be used alongside the Mastering Mixology bot, or manually idc.
    It needs tiles set on the bank chest and the refiner.
    Bank pin must already be entered.
    """
    
    def __init__(self, config: BotConfig, user=''):
        super().__init__(user, break_cfg=config.break_cfg)
        self.cfg: BotConfig = config
        self.log = get_logger('MixerHerbRefiner')
        self.bank = BankInterface(self.client, self.client.item_db)
        self.consecutive_failures = 0
        
    def start(self):
        self.log.info(f"Starting Mixer Herb Refiner with herb: {self.cfg.herb_option.name}")
        while True:
            try:
                self.open_bank_and_withdraw()
                if "grimy" in self.cfg.herb_option.name.lower():
                    self.clean_herbs()
                self.refine_herbs()
                # Reset consecutive failures counter on successful cycle
                self.consecutive_failures = 0
            except Exception as e:
                self.consecutive_failures += 1
                self.log.error(f"Error in herb refining process: {e}")
                
                if self.consecutive_failures > self.cfg.max_retries.value:
                    self.log.critical(f"Failed {self.consecutive_failures} times in a row. Exiting.")
                    sys.exit(1)
                else:
                    self.log.warning(f"Retry attempt {self.consecutive_failures}/{self.cfg.max_retries.value}")
                    time.sleep(3)  # Wait a bit before retrying
    
    def open_bank_and_withdraw(self):
        """Open the bank and withdraw a full inventory of herbs"""
        # Click on bank tile
        self.log.info(f"Clicking bank tile...")
        max_attempts = 2
        for attempt in range(max_attempts):
            try:
                self.client.smart_click_tile(
                    self.cfg.bank_tile.value, 
                    ['bank', 'banker', 'booth', 'chest'],
                    retry_hover=5
                )
                break
            except Exception as e:
                if attempt == max_attempts - 1:
                    raise RuntimeError(f"Failed to click bank tile after {max_attempts} attempts: {e}")
                self.log.warning(f"Failed to click bank tile (attempt {attempt+1}/{max_attempts}): {e}")
                time.sleep(1)
        
        # Wait until character stops moving and bank is open
        while self.client.is_moving():
            time.sleep(0.2)
        
        # Make sure bank is open
        attempts = 0
        max_bank_attempts = 5
        while not self.bank.is_open and attempts < max_bank_attempts:
            attempts += 1
            time.sleep(0.5)
        
        if not self.bank.is_open:
            raise RuntimeError("Failed to open bank after multiple attempts")
        
        # Deposit inventory if there are items
        self.log.info("Depositing inventory...")
        self.bank.deposit_inv()
        time.sleep(self.cfg.deposit_delay.choose())
        
        # Withdraw herbs
        self.log.info(f"Withdrawing {self.cfg.herb_option.name}...")
        try:
            self.bank.withdraw(self.cfg.herb_option.name, amount=-1)  # -1 means all
            time.sleep(self.cfg.withdraw_delay.choose())
        except Exception as e:
            self.bank.close()
            raise RuntimeError(f"Failed to withdraw herbs: {e}")
        
        # Close bank
        self.log.info("Closing bank...")
        self.bank.close()
    
    def clean_herbs(self):
        """Clean all grimy herbs in inventory"""
        self.log.info("Cleaning herbs...")
        
        herb_name = self.cfg.herb_option.name
        # Remove "Grimy" for searching cleaned herbs
        clean_herb_name = herb_name.replace("Grimy ", "")
        
        # Get all grimy herbs in inventory
        max_attempts = 2
        for attempt in range(max_attempts):
            try:
                grimy_herbs = self.client.get_inv_items(
                    [herb_name], min_confidence=0.9,
                    y_sort=False,x_sort=False
                )
                break
            except Exception as e:
                if attempt == max_attempts - 1:
                    raise RuntimeError(f"Failed to find herbs in inventory: {e}")
                self.log.warning(f"Failed to find herbs (attempt {attempt+1}/{max_attempts}): {e}")
                time.sleep(1)
        
        if not grimy_herbs:
            self.log.warning(f"No {herb_name} found in inventory")
            raise RuntimeError(f"No {herb_name} found in inventory after bank withdrawal")
        
        # Click each herb to clean it
        self.log.info(f"Found {len(grimy_herbs)} {herb_name} to clean")
        click_failures = 0
        for herb in grimy_herbs:
            try:
                self.client.click(herb, rand_move_chance=0.0, after_click_settle_chance=0)
            except Exception as e:
                click_failures += 1
                self.log.warning(f"Failed to click herb: {e}")
                if click_failures > 5:  # Allow some click failures
                    raise RuntimeError("Too many failures clicking herbs")
        
        # Make sure herbs are cleaned by checking inventory
        time.sleep(0.5)  # Wait for cleaning animation
        try:
            clean_herbs = self.client.get_inv_items([clean_herb_name], min_confidence=0.9)
            self.log.info(f"Cleaned herbs: {len(clean_herbs)}")
            
            if not clean_herbs and not click_failures:
                self.log.warning("Herbs were clicked but none were cleaned")
        except Exception as e:
            self.log.error(f"Error verifying cleaned herbs: {e}")
    
    def get_herb_count(self, include_grimy=True):
        """Count herbs in inventory, both clean and grimy if specified."""
        herb_name = self.cfg.herb_option.name
        clean_herb_name = herb_name.replace("Grimy ", "")
        
        try:
            count = 0
            
            # Check for clean herbs
            clean_herbs = self.client.get_inv_items([clean_herb_name], min_confidence=0.98)
            count += len(clean_herbs)
            
            # Check for grimy herbs if requested
            if include_grimy and "grimy" in herb_name.lower():
                grimy_herbs = self.client.get_inv_items([herb_name], min_confidence=0.98)
                count += len(grimy_herbs)
                
            return count, clean_herbs, grimy_herbs if include_grimy and "grimy" in herb_name.lower() else []
        except Exception as e:
            self.log.warning(f"Error counting herbs: {e}")
            return 0, [], []
    
    def check_and_clean_remaining_grimy(self):
        """Check inventory for any remaining grimy herbs and clean them."""
        herb_name = self.cfg.herb_option.name
        if "grimy" not in herb_name.lower():
            return False  # Not a grimy herb type
            
        try:
            # Find any remaining grimy herbs
            grimy_herbs = self.client.get_inv_items([herb_name], min_confidence=0.9)
            if not grimy_herbs:
                return False  # No grimy herbs found
                
            self.log.info(f"Found {len(grimy_herbs)} remaining grimy herbs to clean")
            for herb in grimy_herbs:
                try:
                    self.client.click(herb, rand_move_chance=0.0, after_click_settle_chance=0)
                except Exception as e:
                    self.log.warning(f"Failed to click herb: {e}")
                    
            time.sleep(0.5)  # Wait for cleaning animation
            
            # Verify cleaning was successful
            remaining_grimy = self.client.get_inv_items([herb_name], min_confidence=0.9)
            return len(remaining_grimy) == 0
        except Exception as e:
            self.log.warning(f"Error checking for remaining grimy herbs: {e}")
            return False

    def refine_herbs(self):
        """Click the refiner tile and wait until herbs are processed with improved monitoring."""
        herb_name = self.cfg.herb_option.name
        clean_herb_name = herb_name.replace("Grimy ", "") if "grimy" in herb_name.lower() else herb_name
        
        # Get initial herb count
        initial_count, _, _ = self.get_herb_count()
        if initial_count == 0:
            self.log.warning("No herbs found to refine")
            return
            
        self.log.info(f"Starting refining with {initial_count} herbs")
        
        # Click refiner tile
        self.click_refiner()
        
        # Wait until character stops moving
        while self.client.is_moving():
            time.sleep(0.2)
        
        # Monitor herb processing with progress checks
        start_time = time.time()
        last_count = initial_count
        last_progress_time = start_time
        
        while time.time() - start_time < self.cfg.process_timeout.value:
            # Get current herb count
            current_count, clean_herbs, grimy_herbs = self.get_herb_count()
            
            # If all herbs are processed, we're done
            if current_count == 0:
                self.log.info("All herbs processed successfully")
                return
                
            # Check if progress has stalled
            if current_count == last_count and time.time() - last_progress_time > self.cfg.stall_timeout.value:
                self.log.warning(f"Processing stalled at {current_count} herbs remaining")
                
                # Check if we have any grimy herbs that need cleaning
                if grimy_herbs:
                    self.log.info(f"Found {len(grimy_herbs)} grimy herbs that need cleaning")
                    self.check_and_clean_remaining_grimy()
                    
                    # Try refining again
                    self.log.info("Clicking refiner again after cleaning herbs")
                    self.click_refiner()
                    while self.client.is_moving():
                        time.sleep(0.2)
                else:
                    # If no grimy herbs but still stalled, try clicking refiner again
                    self.log.info("No grimy herbs found but processing stalled. Clicking refiner again.")
                    self.click_refiner()
                    while self.client.is_moving():
                        time.sleep(0.2)
                
                # Reset progress timer
                last_progress_time = time.time()
            
            # If count decreased, update progress tracking
            elif current_count < last_count:
                self.log.info(f"Processing herbs: {current_count}/{initial_count} remaining")
                last_count = current_count
                last_progress_time = time.time()
                
            time.sleep(0.5)
        
        # If we get here, we've timed out
        remaining, _, _ = self.get_herb_count()
        if remaining > 0:
            raise RuntimeError(f"Timed out waiting for herbs to be processed. {remaining} herbs remaining.")
        else:
            self.log.info("All herbs processed")

    def click_refiner(self):
        """Helper method to click the refiner tile."""
        self.log.info("Clicking refiner tile...")
        max_attempts = 2
        for attempt in range(max_attempts):
            try:
                self.client.smart_click_tile(
                    self.cfg.refiner_tile.value,
                    ['refiner', 'operate'],
                    retry_hover=5
                )
                return True
            except Exception as e:
                if attempt == max_attempts - 1:
                    raise RuntimeError(f"Failed to click refiner tile after {max_attempts} attempts: {e}")
                self.log.warning(f"Failed to click refiner (attempt {attempt+1}/{max_attempts}): {e}")
                time.sleep(1)
        return False
