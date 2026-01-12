from bots.core import BotConfigMixin
from bots.core.cfg_types import (
    RangeParam,
    BreakCfgParam,
    RGBParam,
    ItemParam,
)
from core.bot import Bot
from core.logger import get_logger
from core.control import ScriptControl
from core import tools

import time
import random


control = ScriptControl()
NONFATAL_EXC = (RuntimeError, ValueError, OSError, AttributeError, IndexError)


class BotConfig(BotConfigMixin):
    # Tile color to click (pink/magenta box always visible)
    event_tile: RGBParam = RGBParam.from_tuple((255, 0, 255))  # pink tile (#ff00ff)
    color_tolerance: int = 40

    # Timing
    poll_interval_s: float = 0.25  # main loop cadence
    stall_reclick_s: float = 5.0   # if no gain for this long, re-click tile

    # Inventory
    coin_pouch: ItemParam = ItemParam("Coin pouch")
    open_threshold: int = 84  # open when >= this many
    after_open_wait_s: float = 0.9  # brief settle after click before recount

    # Optional jitter to feel human
    jitter_between_actions: RangeParam = RangeParam(0.12, 0.35)

    # Break configuration
    break_cfg: BreakCfgParam = BreakCfgParam(
        RangeParam(15, 45),
        0.001,
    )


class BotExecutor(Bot):
    name: str = "Tile Wealth Thiever"
    description: str = "Wealthy citizen thiever for grid masters."
    tier: str = "F"
    instructions: str = """
    This was a bot designed for grid master minigame.
    It's pretty trash, you should probably not use it.
    
    It needs some wealthy citizen plugin to work at all. (to highlight the active thievable citizen tile)
    """
    
    def __init__(self, config: BotConfig, user: str = ""):
        super().__init__(user, break_cfg=config.break_cfg)
        self.cfg: BotConfig = config
        self.log = get_logger("TileWealthThiever")

    def start(self):
        self.main_loop()

    # ----- Main loop -----
    def main_loop(self):
        consecutive_failures = 0
        max_failures = 5
        backoff_base = 0.6

        # Initialize state
        last_gain = time.time()
        prev_cnt = self._inv_count(self.cfg.coin_pouch.name)

        # Kick off by clicking the pink tile once
        try:
            box = self._get_event_box()
            if box:
                self._click_event_box(box)
        except NONFATAL_EXC:
            pass

        while True:
            try:
                self.control.propose_break()

                # Check pouch count progression
                cur_cnt = self._inv_count(self.cfg.coin_pouch.name)
                if cur_cnt > prev_cnt:
                    self.log.debug("Coin pouch increased: %d -> %d", prev_cnt, cur_cnt)
                    prev_cnt = cur_cnt
                    last_gain = time.time()

                # If stalled for too long, click the pink tile again
                if (time.time() - last_gain) >= self.cfg.stall_reclick_s:
                    box = self._get_event_box()
                    if box:
                        if self._click_event_box(box):
                            self.log.debug("Re-clicked pink tile due to stall.")
                            last_gain = time.time()
                        else:
                            self.log.debug("Failed to click pink tile on stall; will retry.")
                    else:
                        self.log.debug("Pink tile not found on stall; continuing.")

                # If enough pouches, open once and move cursor off-screen
                if cur_cnt >= self.cfg.open_threshold:
                    before = cur_cnt
                    self._open_pouches_once()
                    # Re-count after settle
                    time.sleep(self.cfg.after_open_wait_s)
                    after = self._inv_count(self.cfg.coin_pouch.name)
                    self.log.info(
                        "Opened coin pouches at >= %d: %d -> %d",
                        self.cfg.open_threshold,
                        before,
                        after,
                    )
                    prev_cnt = after
                    last_gain = time.time()

                # Small pacing jitter
                time.sleep(random.uniform(*self.cfg.jitter_between_actions.value))

                # Success path resets failures
                if consecutive_failures > 0:
                    consecutive_failures = 0

            except NONFATAL_EXC as e:
                consecutive_failures += 1
                if consecutive_failures >= max_failures:
                    self.log.error("Too many errors (%d); cooling off: %s", consecutive_failures, e)
                    time.sleep(6.0 + random.uniform(0.0, 1.0))
                    consecutive_failures = 0
                else:
                    delay = min(8.0, backoff_base * (2 ** (consecutive_failures - 1))) + random.uniform(0, 0.5)
                    self.log.warning(
                        "Error in main loop (attempt %d/%d). Retrying in %.1fs: %s",
                        consecutive_failures,
                        max_failures,
                        delay,
                        e,
                    )
                    time.sleep(delay)

    # ----- Helpers -----
    def _inv_count(self, name: str) -> int:
        try:
            return len(self.client.get_inv_items([name]))
        except NONFATAL_EXC as e:
            self.log.debug("Inventory count failed for %s: %s", name, e)
            return 0

    @control.guard
    def _get_event_box(self):
        """Find the always-visible pink tile box in the filtered screenshot."""
        try:
            return tools.find_color_box(
                self.client.get_filtered_screenshot(),
                self.cfg.event_tile,
                tol=self.cfg.color_tolerance,
            )
        except NONFATAL_EXC:
            return None

    @control.guard
    def _click_event_box(self, box) -> bool:
        try:
            # Directly click the color box region (no hover verification needed)
            self.client.click(box, click_cnt=1)
            # Small settle move to avoid hover overlays
            self.client.move_to(self.client.window_match)
            return True
        except NONFATAL_EXC as e:
            self.log.debug("Failed to click pink tile: %s", e)
            return False

    @control.guard
    def _open_pouches_once(self):
        """Single-click the coin pouch stack, then move cursor off the window.

        Note: This repo exposes move_off_window(); using that as the off-screen move.
        """
        pouch = self.cfg.coin_pouch.name
        try:
            items = self.client.get_inv_items([pouch], x_sort=True, y_sort=True)
            if not items:
                return
            self.client.click(items[0], click_cnt=1)
        except NONFATAL_EXC as e:
            self.log.debug("Failed to click coin pouch once: %s", e)
        finally:
            # Move cursor off screen/window area to allow game actions to proceed
            try:
                mover = getattr(self.client, "move_off_screen", None) or getattr(self.client, "move_off_window", None)
                if mover is not None:
                    mover()
            except NONFATAL_EXC as e:
                self.log.debug("move_off_window failed: %s", e)
