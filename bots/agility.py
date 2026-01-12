from bots.core import BotConfigMixin
from bots.core.cfg_types import BooleanParam, StringParam, IntParam, FloatParam, RGBParam, RangeParam, BreakCfgParam, StringListParam
from core.bot import Bot
from core.logger import get_logger
from core.control import ScriptControl, ScriptTerminationException
from core import tools

import time
import random

control = ScriptControl()


class BotConfig(BotConfigMixin):

    # Tile colors (R, G, B)
    next_tile: RGBParam = RGBParam(0, 255, 100)
    stop_tile: RGBParam = RGBParam(255, 0, 50)
    grace_tile: RGBParam = RGBParam(255, 0, 255)
    wait_tile: RGBParam = RGBParam(255, 135, 0)

    # Matching / behavior
    color_tolerance: IntParam = IntParam(40)
    action_keywords: StringListParam = StringListParam([
        'jump', 'climb', 'vault', 'gap', 'cross', 
        'rope', 'wall', '-up', 'grab', 'leap',
        'cross', 'monkey', '-on', 'hurdle'
    ])

    fail_max: IntParam = IntParam(10)
    wait_check_limit: IntParam = IntParam(5)

    # Random AFK breaks similar to legacy script
    sleep_chance: FloatParam = FloatParam(0.005)
    sleep_range: RangeParam = RangeParam(25, 60)

    # Safety limit
    max_time_min: IntParam = IntParam(180)

    # Break configuration
    break_cfg: BreakCfgParam = BreakCfgParam(
        RangeParam(15, 45),  # break duration range in seconds
        FloatParam(0.01)     # break chance
    )


class BotExecutor(Bot):
    name: str = "Rooftop Agility"
    tier: str = "A"
    description: str = "Traverses rooftop agility courses, clicking next obstacles and looting marks of grace."
    instructions: str = """
    Needs plugin: Rooftop Agility Improved
    
    Ensure the following settings have no transparency in the colors:
    - Obstacles:
        - Next obstacle tile (green)
        - Stop tile (red)
    - Mark of graces:
        - Mark of grace tile (pink/magenta)
        - Show stop obstacles (checked)
        
    Obviously the colors are configurable.
    
    Ensure camera is oriented in a way so all "next" obstacles are visible on screen.
    
    Thousands of laps completed in:
    - Canafis
    - Pollnivneach
    - Seers' village
    
    Some rooftops are a bit buggy because of issues with the plugin.
    """
    
    def __init__(self, config: BotConfig, user: str = ""):
        super().__init__(user, break_cfg=config.break_cfg)
        self.cfg: BotConfig = config
        self.log = get_logger("RooftopAgility")

    def start(self):
        try:
            self.main_loop()
        except ScriptTerminationException as e:
            self.log.info(f"Script termination requested: {e}")
        except Exception as e:
            self.log.error(f"Fatal error: {e}")
            raise

    @control.guard
    def main_loop(self):
        start = time.time()
        fails = 0
        wait_cnt = 0

        while True:
            # Course-specific waiting tile – throttle actions when in a waiting state
            if self._get_color_tile(self.cfg.wait_tile.value):
                self.log.debug('Still waiting...')
                time.sleep(1)
                wait_cnt += 1
                if wait_cnt > self.cfg.wait_check_limit.value:
                    wait_cnt = 0
                    continue
            else:
                wait_cnt = 0

            # Safety timeout
            self._timeout_check(start)

            # Propose framework-driven break
            self.control.propose_break()

            # Attempt next obstacle
            if self._click_tile(self.cfg.next_tile.value, self.cfg.action_keywords.value):
                fails = 0
                self._maybe_sleep()
                continue
            else:
                fails += 1
                if fails % 2 == 0:
                    self.client.move_off_window()
                if fails > self.cfg.fail_max.value:
                    self.log.error('Too many failures in a row; stopping agility loop.')
                    return
                time.sleep(1)

            # Try to pick up mark of grace opportunistically
            self._click_tile(self.cfg.grace_tile.value, ['take', 'grace'])

    # --- Internals ---
    def _get_color_tile(self, tile_color, tol=None):
        tol = tol if tol is not None else self.cfg.color_tolerance.value
        try:
            return tools.find_color_box(self.client.get_filtered_screenshot(), tile_color, tol=tol)
        except Exception as e:
            self.log.debug(f"Error getting color tile {tile_color}: {e}")
            return None

    @control.guard
    def _click_tile(self, tile_color, action_keywords):
        box = self._get_color_tile(tile_color)
        if not box:
            return False
        try:
            self.client.smart_click_match(
                box, action_keywords,
                retry_hover=3,
                center_point=True,
                center_point_variance=10
            )
            self.client.move_to(self.client.window_match)
        except Exception as e:
            self.log.debug(f"Failed to click {action_keywords} on tile {tile_color}, {e}")
            return False

        while self.client.is_moving():
            continue
        return True

    def _timeout_check(self, start):
        runtime = time.time() - start
        if runtime / 60 > self.cfg.max_time_min.value:
            raise RuntimeError('MAX TIME LIMIT EXCEEDED')

    def _maybe_sleep(self):
        if random.random() < self.cfg.sleep_chance.value:
            t = int(self.cfg.sleep_range.choose())
            self.log.info(f"Sleeping for {t} seconds")
            self.client.move_off_window()
            time.sleep(t)