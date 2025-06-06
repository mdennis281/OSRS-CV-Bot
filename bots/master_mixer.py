from bots.core import BotConfigMixin
from bots.core.cfg_types import BooleanParam, StringParam, IntParam, FloatParam, RGBParam, RangeParam, BreakCfgParam,StringListParam
from core.bot import Bot

from core import tools
from core.region_match import MatchResult
from core.osrs_client import ToolplaneTab
from core.minigames.mastering_mixology import MasteringMixology, MissingIngredientError
from core.logger import get_logger


from PIL import Image
import random
import time
import pyautogui

class BotConfig(BotConfigMixin):
    # Configuration parameters
    name: str = "Mastering Mixology Bot"
    description: str = "A bot that plays Mastering Mixology"


    mixer_tile: RGBParam = RGBParam(255, 110, 50)
    station_tile: RGBParam = RGBParam(153, 255, 221)
    quick_action_tile: RGBParam = RGBParam(255, 0, 255)
    conveyor_tile: RGBParam = RGBParam(125, 0, 255)
    digweed_tile: RGBParam = RGBParam(0, 255, 255)
    hopper_tile: RGBParam = RGBParam(255, 0 , 40)
    ingredient_exclude: StringListParam = StringListParam(
        [ 'aaa'] # 'mmm', 'mma',
    )
    digweed_potions: StringListParam = StringListParam(
        ['Liplack liquor']
    )


    break_cfg: BreakCfgParam = BreakCfgParam(
        RangeParam(15, 45),  # break duration range in seconds
        FloatParam(0.01)  # break chance
    )


    

class BotExecutor(Bot):
    def __init__(self, config: BotConfig, user=''):
        super().__init__(user, break_cfg=config.break_cfg)
        self.cfg: BotConfig = config
        self.log = get_logger('MixologyBot')

        self.mixer = MasteringMixology(
            self, 
            mixer_tile=self.cfg.mixer_tile,
            station_tile=self.cfg.station_tile,
            quick_action_tile=self.cfg.quick_action_tile,
            digweed_tile=self.cfg.digweed_tile,
            ingredient_exclude=self.cfg.ingredient_exclude.value,
        )
    
    def start(self):
        #self.fill_ingredients()
        self.loop()
        
    
    def loop(self):
        while True:
            orders = self.mixer.get_orders()
           
            try:
                for order in orders:
                    self.log.info(f"Filling vial: {order.ingredients}")
                    self.mixer.fill_potion(order.ingredients)
                    while self.client.is_moving(): continue
            except MissingIngredientError as e:
                if not self.fill_ingredients():
                    raise e



            self.mix_digweed()

            try:
                for order in orders:
                    self.log.info(f"Executing action: {order}")
                    self.mixer.do_action_station(order)
            except Exception as e:
                self.log.error(f"Error with stations: {e}")
                # put any unordered ingredients back on conveyor
                self.click_conveyor()
            self.click_conveyor()
            
    def mix_digweed(self):
        digweed = self.client.get_inv_items(['Digweed'])
        if not digweed:
            return
        
        pots = self.client.get_inv_items(
            self.cfg.digweed_potions.value,
            min_confidence=.9
        )

        if not pots:
            return
        
        self.log.info(f'Mixing digweed with approved potion.')
        self.client.click(digweed[0])
        self.client.click(pots[0])
        
    
    def click_conveyor(self):
        self.client.smart_click_tile(
                self.cfg.conveyor_tile.value, 
                ['fufil', 'order', 'conveyor', 'belt']
            )
        while self.client.is_moving(): continue

    def fill_ingredients(self) -> bool:
        ingredients = ['Mox paste', 'Lye paste', 'Aga paste']
        inv = self.client.get_inv_items(ingredients, min_confidence=0.9)
        if len(inv) < 3:
            return False
        
        self.log.info("Filling ingredients...")
        self.client.smart_click_tile(
            self.cfg.hopper_tile.value, 
            ['deposit', 'hopper']
        )
        while self.client.is_moving(): continue
        return True
        
        
            

        
    

    
                

        
    




