from bots.core import BotConfigMixin
from bots.core.cfg_types import RangeParam, BreakCfgParam
from core.bot import Bot
from core.logger import get_logger
from core.control import ScriptControl

import time
import random
import pyautogui
import keyboard


control = ScriptControl()


class BotConfig(BotConfigMixin):
    # How often to take focus and jiggle camera (in minutes)
    focus_interval_min: RangeParam = RangeParam(4.0, 9.0)

    # How long to move the camera each time (seconds)
    jiggle_duration_s: RangeParam = RangeParam(2.0, 4.0)

    # Between-direction micro-sleeps while jiggling (seconds)
    jiggle_step_sleep_s: RangeParam = RangeParam(0.08, 0.25)

    # Use mouse right-drag for camera movement (alongside arrow keys)
    use_mouse_drag: bool = True

    # Chance to scroll the mouse wheel (camera zoom) during a jiggle
    scroll_chance: float = 0.35
    scroll_min: int = -3
    scroll_max: int = 3

    # Bounded retry behavior
    focus_retries: int = 3
    max_failures: int = 5

    # Break configuration
    break_cfg: BreakCfgParam = BreakCfgParam(
        RangeParam(15, 45),
        0.005,
    )


class BotExecutor(Bot):
    name: str = "Focus Camera"
    description: str = (
        "Takes focus every X minutes and moves the camera randomly for a short time."
    )
    instructions: str = """
    This bot helps keep your RuneLite client active by periodically bringing it into focus.
    I havent messed with this one much. It does keep you logged in, but it's kinda sketchy.
    """
    tier: str = "C"

    def __init__(self, config: BotConfig, user: str = ""):
        super().__init__(user, break_cfg=config.break_cfg)
        self.cfg: BotConfig = config
        self.log = get_logger("FocusCamera")

    def start(self):
        self.main_loop()

    def _choose_interval_s(self) -> float:
        lo, hi = self.cfg.focus_interval_min.value
        return random.uniform(lo, hi) * 60.0

    # ----- main loop -----
    def main_loop(self):
        next_at = time.time()  # fire once immediately
        failures = 0
        while True:
            self.control.propose_break()

            now = time.time()
            if now < next_at:
                # short sleeps so we remain responsive to breaks
                time.sleep(min(1.0, next_at - now))
                continue

            try:
                self._focus_and_jiggle()
                failures = 0
            except (RuntimeError, OSError, pyautogui.FailSafeException) as e:
                failures += 1
                self.log.warning("Focus/jiggle step failed (%d): %s", failures, e)
                if failures >= self.cfg.max_failures:
                    self.log.error("Too many errors performing jiggle; cooling off for 10s")
                    time.sleep(10.0 + random.uniform(0.0, 1.0))
                    failures = 0

            # schedule next run
            next_at = time.time() + self._choose_interval_s()

    # ----- actions -----
    @control.guard
    def _bring_to_focus(self) -> bool:
        # best-effort to update and focus RL window
        for attempt in range(1, self.cfg.focus_retries + 1):
            try:
                if not self.client.is_open:
                    self.client.update_window()
                if self.client.is_open:
                    self.client.bring_to_focus()
                    # small settle to let focus fully apply
                    time.sleep(0.15)
                    return True
            except (RuntimeError, OSError, pyautogui.FailSafeException) as e:
                self.log.debug("Focus attempt %d failed: %s", attempt, e)
            time.sleep(0.25 + random.uniform(0.0, 0.25))
        return False

    def _focus_and_jiggle(self):
        if not self._bring_to_focus():
            raise RuntimeError("Unable to focus RuneLite window")

        dur_lo, dur_hi = self.cfg.jiggle_duration_s.value
        duration = random.uniform(dur_lo, dur_hi)
        end_at = time.time() + duration

        # Start with a quick mouse move to center to avoid edges
        try:
            cx = self.client.window.left + self.client.window.width // 2
            cy = self.client.window.top + self.client.window.height // 2
            pyautogui.moveTo(cx, cy, _pause=0)
        except (pyautogui.FailSafeException, OSError, RuntimeError):
            pass

        # randomly decide which method to prefer per jiggle window
        prefer_mouse = self.cfg.use_mouse_drag and (random.random() < 0.7)

        while time.time() < end_at:
            self.control.propose_break()

            # blend mouse-drag rotations and arrow-key taps
            if prefer_mouse and self.cfg.use_mouse_drag and random.random() < 0.7:
                self._mouse_drag_chunk(max_time=min(0.9, end_at - time.time()))
            else:
                self._arrow_key_chunk(max_time=min(0.9, end_at - time.time()))

            # occasional zoom scroll
            if random.random() < self.cfg.scroll_chance:
                dz = random.randint(self.cfg.scroll_min, self.cfg.scroll_max)
                if dz == 0:
                    dz = 1
                try:
                    pyautogui.scroll(dz)
                except (pyautogui.FailSafeException, OSError, RuntimeError):
                    pass

            # small rest between actions
            lo, hi = self.cfg.jiggle_step_sleep_s.value
            time.sleep(random.uniform(lo, hi))

        # finish by nudging off the window slightly
        self.client.move_off_window()

    @control.guard
    def _mouse_drag_chunk(self, max_time: float = 0.6):
        if max_time <= 0.05:
            return

    # compute a few random points near the center
        cx = self.client.window.left + self.client.window.width // 2
        cy = self.client.window.top + self.client.window.height // 2

        # ensure cursor is within window before dragging
        try:
            pyautogui.moveTo(cx, cy, _pause=0)
        except (pyautogui.FailSafeException, OSError, RuntimeError):
            return

        start = time.time()
        pressed = False
        try:
            pyautogui.mouseDown(button="right")
            pressed = True
            while (time.time() - start) < max_time:
                # random small radius motions produce gentle camera swings
                radius = random.randint(40, 140)
                tx = int(cx + radius * 0.7 * random.random() * (1 if random.random() < 0.5 else -1))
                ty = int(cy + radius * 0.7 * random.random() * (1 if random.random() < 0.5 else -1))
                # Use our humanized move; supply window-relative tuple
                self.client.move_to((tx - self.client.window.left, ty - self.client.window.top))
                # quick micro-sleep inside the drag
                time.sleep(random.uniform(0.03, 0.08))
        finally:
            if pressed:
                try:
                    pyautogui.mouseUp(button="right")
                except (pyautogui.FailSafeException, OSError, RuntimeError):
                    pass

    @control.guard
    def _arrow_key_chunk(self, max_time: float = 0.6):
        if max_time <= 0.05:
            return
        keys = ["left", "right", "up", "down"]
        deadline = time.time() + max_time
        while time.time() < deadline:
            key = random.choice(keys)
            hold = random.uniform(0.12, min(0.7, deadline - time.time()))
            try:
                keyboard.press(key)
                time.sleep(hold)
            finally:
                try:
                    keyboard.release(key)
                except (OSError, RuntimeError, ValueError):
                    pass
            # quick pause between key presses
            time.sleep(random.uniform(0.03, 0.12))
