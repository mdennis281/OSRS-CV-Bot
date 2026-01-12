from bots.core import BotConfigMixin
from bots.core.cfg_types import BooleanParam, StringParam, IntParam, FloatParam, RGBParam, RangeParam, BreakCfgParam, ItemParam
from core.bot import Bot
from core.control import ScriptControl, ScriptTerminationException
from core.osrs_client import MinimapElement, ToolplaneTab
from core.logger import get_logger
import core.minigames.nmz_pot_reader as nmz_pot_reader
from core import tools

import random
import time
import math

control = ScriptControl()

# a little over 5 because racing condition
OVERLOAD_LEN_MIN = 5.1

class BotConfig(BotConfigMixin):
    # Configuration parameters

    # Main feature toggles
    manage_health: BooleanParam = BooleanParam(True)
    manage_absorption: BooleanParam = BooleanParam(True)
    manage_overload: BooleanParam = BooleanParam(True)
    prayer_flick: BooleanParam = BooleanParam(True)
    afk_mode: BooleanParam = BooleanParam(True)

    wait_between_ideal: RangeParam = RangeParam(50,60)  # Wait time between actions in seconds
    wait_sigma: FloatParam = IntParam(15)  # Signal strength for waiting

    # Prayer flicking configuration
    flick_forget_chance: FloatParam = FloatParam(0.1)  # Chance to forget flicking (0.0-1.0)
    prayer_flick_delay: RangeParam = RangeParam(40, 50)  # Sleep range between flicks in seconds

    # Health management
    target_health: IntParam = IntParam(1)  # Target health level to maintain
    rock_cake: ItemParam = ItemParam("Dwarven rock cake")
    rock_cake_confidence: FloatParam = FloatParam(0.94)
    rock_cake_click_interval: FloatParam = FloatParam(0.6)
    max_rock_cake_clicks: IntParam = IntParam(8)

    # Absorption management
    min_absorption: IntParam = IntParam(800)  # Minimum absorption before drinking more
    absorption_potion: ItemParam = ItemParam("Absorption (4)")
    absorption_confidence: FloatParam = FloatParam(0.94)
    
    # Overload potions (by ID)
    overload_potions: list[ItemParam] = [
        ItemParam(11730),  # Overload (1)
        ItemParam(11731),  # Overload (2)  
        ItemParam(11732),  # Overload (3)
        ItemParam(11733)   # Overload (4)
    ]
    absorption_click_interval: FloatParam = FloatParam(1.0)
    absorption_clicks_per_dose: IntParam = IntParam(4)

    # Error handling
    max_consecutive_errors: IntParam = IntParam(5)
    error_retry_delay: FloatParam = FloatParam(1.0)

    # Break configuration
    break_cfg: BreakCfgParam = BreakCfgParam(
        RangeParam(30, 300),  # break duration range in seconds
        FloatParam(0.01)     # break chance
    )
    chance_move_off_window: FloatParam = FloatParam(0.65)  # Chance to move off window during AFK mode

class BotExecutor(Bot):
    name: str = "NMZ Bot"
    description: str = "A bot that manages NMZ prayer flicking, health, and absorption/overload potions"
    tier: str = "S"
    instructions: str = """
    Start nmz with whatever method/kit (rumble works best)
    bring rock cake and absorption (+ overload) pots
    IF BRINGING OVERLOADS, DO NOT DRINK THEM YOURSELF BEFOREHAND
    You can drink absorption pots beforehand
    Turn on auto retaliate.
    Set quick prayer to the red heart (2x regen rate)
    
    I like going into the corner, making the camera face the wall since sometimes the minimap clicker
    can misclick and make you walk.
    
    Start the bot. It should keep you alive.
    Gotten all combat skills to 99 on multiple accounts with this bot.
    """
    
    def __init__(self, config: BotConfig, user=''):
        super().__init__(user, break_cfg=config.break_cfg)
        self.cfg: BotConfig = config
        self.log = get_logger('NMZ')
        self.error_count = 0
        self.last_overload = 0
        
    def start(self):
        self.log.info("Starting NMZ Prayer Flick Runner")
        
        # Check if RuneLite is open
        if not self.client.is_open:
            self.log.error("RuneLite is not open.")
            return
        
        try:
            self.main_loop()
        except ScriptTerminationException as e:
            self.log.info(f"Script termination requested: {e}")
        except Exception as e:
            self.log.error(f"Fatal error: {e}")
            raise
        finally:
            self.log.info("Exiting NMZ Runner")

    @control.guard
    def main_loop(self):
        """Main execution loop"""
        while True:
            # Check if we should take a break first
            self.control.propose_break()
            
            # Decide whether to flick or forget
            if self.cfg.prayer_flick.value and random.random() < self.cfg.flick_forget_chance.value:
                self.log.debug("Forgetting to flick this cycle...")
            else:
                try:
                    self.flick_routine()
                    self.error_count = 0
                    
                except Exception as e:
                    self.log.error(f"Error in flick routine: {e}")
                    self.error_count += 1
                    
                    if self.error_count >= self.cfg.max_consecutive_errors.value:
                        self.log.error("Too many consecutive errors, terminating...")
                        raise ScriptTerminationException("Max consecutive errors reached")
                    
                    # Move off window to recover from potential UI issues
                    if self.cfg.afk_mode.value:
                        self.client.move_off_window()
                    
                    time.sleep(self.cfg.error_retry_delay.value)

            # Wait for next cycle
            sleep_time = random.normalvariate(
                self.cfg.wait_between_ideal.choose(),
                self.cfg.wait_sigma.value
            )
            self.wait_interruptible(sleep_time)

    @control.guard
    def flick_routine(self):
        """Main flicking routine that handles prayer, health, and absorption"""
        actions = []
        
        if self.cfg.manage_overload.value:
            # this needs to be done before handle health
            self.handle_overload()

        if self.cfg.prayer_flick.value:
            actions.append(self.handle_prayer_flick)
        
        if self.cfg.manage_health.value:
            actions.append(self.handle_health)
        
        if self.cfg.manage_absorption.value:
            actions.append(self.handle_absorption)

        # Shuffle the actions to execute them in random order
        random.shuffle(actions)

        for action in actions:
            action()

        # Ensure prayer is in correct state
        if self.cfg.prayer_flick.value:
            self.ensure_prayer_state(False)

        # Move off window if in AFK mode
        if self.cfg.afk_mode.value:
            # not every time
            if random.random() < self.cfg.chance_move_off_window.value:
                self.client.move_off_window()


    @control.guard
    def handle_prayer_flick(self):
        """Handle prayer flicking by clicking prayer icon twice"""
        try:
            prayer = self.client.get_minimap_stat(MinimapElement.PRAYER)
            
            if prayer and prayer > 0:
                self.log.debug(f"Prayer points: {prayer}, flicking...")
                self.client.click_minimap(
                    MinimapElement.PRAYER, 
                    click_cnt=2
                )
            else:
                self.log.warning("No prayer points detected or prayer stat unavailable")
                
        except Exception as e:
            self.log.error(f"Error handling prayer flick: {e}")
            raise

    @control.guard
    def handle_health(self, match: tools.MatchResult = None):
        """Manage health by using rock cake to maintain target health level"""
        try:
            health = self.client.get_minimap_stat(MinimapElement.HEALTH)
            
            if not health:
                self.log.warning("Could not read health stat")
                return
            
            if health > 50 and self.cfg.manage_overload.value:
                self.log.info('Health is quite high.. did overload not work?')
                self.handle_overload()
                health = self.client.get_minimap_stat(MinimapElement.HEALTH)
                
            if health > self.cfg.target_health.value:
                
                    
                self.log.info(f"Health is {health}, using rock cake to reduce to {self.cfg.target_health.value}")
                
                clicks_needed = min(
                    health - self.cfg.target_health.value,
                    self.cfg.max_rock_cake_clicks.value + random.randint(-2,2)
                )
                
                try:
                    if not match:
                        match = self.client.find_item(
                            self.cfg.rock_cake.name,
                            min_confidence=self.cfg.rock_cake_confidence.value
                        )
                    self.client.click(
                        match,
                        click_cnt=clicks_needed,
                        min_click_interval=self.cfg.rock_cake_click_interval.value,
                    )
                    
                    # Wait for health to update
                    time.sleep(0.5)
                    
                    # Recursively check if we need more clicks
                    self.handle_health(match)
                    
                except ValueError:
                    self.log.warning(f"Rock cake '{self.cfg.rock_cake.name}' not found in inventory")
                    
        except Exception as e:
            self.log.error(f"Error handling health: {e}")
            raise

    

    @control.guard
    def handle_absorption(self):
        """Manage absorption points by drinking absorption potions when needed"""
        try:
            # Read current absorption value using OCR
            current_absorption = self.get_absorption_value()
            self.log.debug(f"Current absorption: {current_absorption}")
            
            if current_absorption < self.cfg.min_absorption.value:
                pots_needed = math.ceil(
                    (self.cfg.min_absorption.value - current_absorption) / 200
                )
                
                self.log.info(f"Absorption low ({current_absorption}), drinking {pots_needed} potions")
                
                for i in range(pots_needed):
                    if self.control.terminate:
                        return
                        
                    try:
                        self.client.click_item(
                            self.cfg.absorption_potion.name,
                            min_confidence=self.cfg.absorption_confidence.value,
                            min_click_interval=self.cfg.absorption_click_interval.value,
                            click_cnt=self.cfg.absorption_clicks_per_dose.value,
                        )
                        
                        self.log.debug(f"Drank absorption potion {i+1}/{pots_needed}")
                        
                    except ValueError:
                        self.log.warning(f"Absorption potion '{self.cfg.absorption_potion.name}' not found")
                        break
                        
        except Exception as e:
            self.log.error(f"Error handling absorption: {e}")
            raise

    def get_absorption_value(self):
        """Get current absorption value using OCR"""
        try:
            return nmz_pot_reader.absorption_value(self.client.get_screenshot())
        except ValueError as e:
            raise RuntimeError(f"Failed to read absorption value: {e}. Are you in NMZ?")

    @control.guard
    def ensure_prayer_state(self, desired_state: bool = False):
        """Ensure prayer is in the correct state (default: off)"""
        try:
            time.sleep(0.5)  # Allow time for UI to settle
            current_state = self.client.quick_prayer_active
            
            if current_state != desired_state:
                self.log.debug(f"Prayer state incorrect (current: {current_state}, desired: {desired_state}), correcting...")
                self.client.click_minimap(MinimapElement.PRAYER)
                
        except Exception as e:
            self.log.error(f"Error ensuring prayer state: {e}")
            raise
        
    @control.guard
    def get_smallest_overload(self):
        """Get the smallest overload potion from the inventory"""
        
        self.client.click_toolplane(ToolplaneTab.INVENTORY)
        
        overload_ids = [item.id for item in self.cfg.overload_potions]
        overloads = self.client.get_inv_items(
            overload_ids,
            min_confidence=0.98,
            do_sort=False
        )
        self.log.debug(f"Found overload potions: {overloads}")
        if overloads:
            # Return the first one found, which should be the smallest
            return overloads[0]
        return None

    @control.guard
    def handle_overload(self):
        """Manage overload effects by drinking overload potions when needed"""
        try:
            now = time.time()
            time_since_last = (now - self.last_overload) / 60
            if time_since_last < 4:
                if self.client.get_minimap_stat(MinimapElement.HEALTH) < 51:
                    return
                self.log.info('Health is above 50 but overload timeout hasn\'t expired.')
                time_since_last = OVERLOAD_LEN_MIN
            overload = self.get_smallest_overload()
            if not overload:
                self.log.warning("No overload potion found in inventory, disabling")
                self.cfg.manage_overload.value = False
                return

            # if less than 1 minute until overload exp, wait here
            if time_since_last < OVERLOAD_LEN_MIN:
                self.log.info("Overload potion is about to expire, waiting...")
                time_until_overload_exp = int((OVERLOAD_LEN_MIN - time_since_last) * 60) + 1
                time.sleep(time_until_overload_exp)
            
            if self.client.get_minimap_stat(MinimapElement.HEALTH) < 51:
                self.log.info("Health is below 51, not drinking overload")
                return
            
            
            self.log.info('Drinking Overload')
            self.client.click(overload)
            self.last_overload = time.time()
            time.sleep(10) # takes a while to get health down

        except Exception as e:
            self.log.error(f"Error handling overload: {e}")
            raise

    def wait_interruptible(self, duration: float):
        """Wait for a duration while checking for termination signals"""
        self.log.debug(f"Waiting for {int(duration)} seconds")
        end_time = time.time() + duration
        
        while time.time() < end_time:
            if self.control.terminate:
                raise ScriptTerminationException("Termination requested during wait")
            time.sleep(1)


# For direct execution
if __name__ == "__main__":
    config = BotConfig()
    bot = BotExecutor(config)
    bot.start()
