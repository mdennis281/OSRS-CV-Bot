from bots.core import BotConfigMixin
from bots.core.cfg_types import RangeParam, BreakCfgParam, ItemParam, RGBParam
from core.bot import Bot
import random
import time
import keyboard

class BotConfig(BotConfigMixin):
    # Configuration parameters
    food: ItemParam = ItemParam("Raw karambwan")
    range_tile: RGBParam = RGBParam(255, 0, 100)
    bank_tile: RGBParam = RGBParam(0, 255, 100)
    
    max_runtime_minutes: int = 180
    
    break_cfg: BreakCfgParam = BreakCfgParam(
        RangeParam(25, 60),  # break duration range
        0.05  # break chance
    )

class BotExecutor(Bot):
    name: str = "Food Cooker"
    description: str = "Cooks raw food at a range and banks them."
    tier: str = "A"
    instructions: str = """
    Cooks raw food at a specified range.
    
    Setup:
    - Mark the Range tile with the configured color (Default: #FF0064 / 255,0,100)
    - Mark the Bank/Chest tile with the configured color (Default: #00FF64 / 0,255,100)
    - Have Raw Karambwans (or configured food) in bank (visible when bank is opened)
    - Start near the bank/range.
    
    I havent used this one much, but it did run all night last i tried.
    """
    
    def __init__(self, config: BotConfig, user=''):
        super().__init__(user, break_cfg=config.break_cfg)
        self.cfg: BotConfig = config
        self.start_time = time.time()
        
    def start(self):
        self.log.info("Starting Cooking Bot")
        self.loop()
        
    def loop(self):
        while not self.terminate:
            self.timeout_check()
            self.deposit_food()
            self.do_cook()
            self.control.propose_break()

    def timeout_check(self):
        if (time.time() - self.start_time) / 60 > self.cfg.max_runtime_minutes:
            self.log.info("Max runtime reached. Terminating.")
            self.control.terminate = True

    def deposit_food(self):
        self.log.info("Banking...")
        self.client.smart_click_tile(
            self.cfg.bank_tile.value,
            'bank',
            retry_match=5
        )
        while self.client.is_moving(): 
            if self.terminate: return
            time.sleep(0.1)
        self.bank.set_quantity_setting('all')
        self.bank.deposit_inv()
        # Use item ID if available, otherwise name
        food_id = self.cfg.food.id if self.cfg.food.id else self.cfg.food.name
        self.bank.withdraw(food_id, -1)
        
        self.client.move_off_window()
        self.bank.close()

    def do_cook(self):
        self.log.info("Going to cook...")
        self.client.smart_click_tile(
            self.cfg.range_tile.value,
            'cook',
            retry_match=5
        )
        while self.client.is_moving():
            if self.terminate: return
            time.sleep(0.1)
            
        keyboard.press('space')
        
        time.sleep(random.uniform(3, 7))
        self.client.move_off_window()
        
        self.log.info("Cooking...")
        while self.client.is_cooking:
            if self.terminate: return
            # Small sleep to prevent busy waiting
            time.sleep(0.1)
