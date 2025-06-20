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
        [ 'aaa', 'mmm', 'mma', 'aam', 'ala' ] # 'mmm', 'mma',
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
        self.fill_ingredients()
        self.loop()
        
    
    def loop(self):
        while True:
            orders = self.mixer.get_orders()
            
            for order in orders:
                try:
                    self.log.info(f"Filling vial: {order.ingredients}")
                    self.mixer.fill_potion(order.ingredients)
                    while self.client.is_moving(): continue
                    order.in_inventory = True
                except MissingIngredientError as e:
                    self.log.error(f"Missing ingredient for {order.ingredients}, attempting to refill.")
                    if not self.fill_ingredients():
                        raise e
                    self.log.info(f"Reattempting to fill vial: {order.ingredients}")
                    self.mixer.fill_potion(order.ingredients)
                    while self.client.is_moving(): continue
                    order.in_inventory = True
                



            self.mix_digweed()

            try:
                for order in orders:
                    self.log.info(f"Executing action: {order}")
                    # if the potion disappeared
                    if order.ingredients not in self.mixer.inv_unfinished_potions():
                        self.log.critical(f"Potion {order.ingredients} not found in inventory. did a station not finish?")
                        return
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
        self.client.move_off_window()
        
    
    def click_conveyor(self):
        err_cnt = 0
        finished_pots = len(self.mixer.inv_finished_potions())
        while finished_pots:
            self.client.smart_click_tile(
                self.cfg.conveyor_tile.value, 
                ['fufil', 'order', 'conveyor', 'belt']
            )
            while self.client.is_moving(): continue
            tmp = self.mixer.inv_finished_potions()
            if len(tmp) == finished_pots:
                self.log.warning(f'Finished pots {finished_pots} did not change, retrying...')
                err_cnt += 1
                if err_cnt > 5:
                    raise RuntimeError('Unable to fufill orders. Too many retries.')
            elif len(tmp) < finished_pots:
                self.log.info(f'Finished pots changed from {finished_pots} to {len(tmp)}')
                finished_pots = len(tmp)
                err_cnt = 0
            else:
                self.log.error(f'Finished pots increased from {finished_pots} to {len(tmp)}. WTF?')
                raise RuntimeError('Finished pots increased, something went wrong.')
            

                

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
        
        
            

        
    

    
                

        
    




