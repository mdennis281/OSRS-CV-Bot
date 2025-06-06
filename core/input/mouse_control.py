"""
human_mouse.py  –  v1.1
"""
from __future__ import annotations
if __name__ == "__main__":
    import os,sys
    sys.path.append(
        os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "../.."
            )
        )
    )
import ctypes, math, random, time
import pyautogui, keyboard
from core.tools import MatchResult          # your class
from enum import Enum
from typing import Tuple

class ClickType(Enum):
    LEFT = 1
    RIGHT = 2
    MIDDLE = 3

# ── global knobs ───────────────────────────────────────────
user32              = ctypes.windll.user32
terminate           = False          # Esc listener toggles this
movement_multiplier = 0.45           # lower = faster (was 0.5)
is_simulation = False

# ── helpers ────────────────────────────────────────────────
def _euclidean(p1, p2):    return math.hypot(p2[0]-p1[0], p2[1]-p1[1])
def _lerp(a,b,t):          return a + (b-a)*t
def _bezier(p0,p1,p2,t):
    return (_lerp(_lerp(p0[0],p1[0],t), _lerp(p1[0],p2[0],t), t),
            _lerp(_lerp(p0[1],p1[1],t), _lerp(p1[1],p2[1],t), t))
def _smooth_steps(total, n):
    return [total*(3*(i/n)**2 - 2*(i/n)**3) for i in range(1,n+1)]
def _block(on=True):       user32.BlockInput(bool(on))

def _get_direction(p1: Tuple[int, int],
                  p2: Tuple[int, int]):
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    angle_rad = math.atan2(dy, dx)         # range (-π, π]
    angle_deg = math.degrees(angle_rad)    # range (-180, 180]
    return (angle_deg + 360) % 360         # → range [0, 360)
# ───────────────────────────────────────────────────────────────
#  Angle helpers  (screen-coords convention: 0° = →, 90° = ↓)
# ───────────────────────────────────────────────────────────────
def _norm(a: float) -> float:
    """Normalise angle to [0, 360)."""
    return a % 360

def _angle_diff(a: float, b: float) -> float:
    """
    Smallest signed difference a→b (deg, –180‥+180].
    Positive ⇒ b is clockwise from a.
    """
    d = (b - a + 180) % 360 - 180
    return d if d != -180 else 180

def _polar_to_xy(angle_deg: float, r: float) -> Tuple[float, float]:
    """Convert polar (screen coords) → Δx, Δy (y grows downward)."""
    rad = math.radians(angle_deg)
    return r * math.cos(rad), r * math.sin(rad)


def _constrain_travel(p1: Tuple[float, float],
                     p2: Tuple[float, float],
                     tp: Tuple[float, float],
                     max_variance: float = 45
                     ) -> Tuple[float, float]:
    """
    Constrain the step p1→p2 so its heading is no farther than
    `max_variance` degrees from the direction toward the long-term
    target point `tp`.

    Parameters
    ----------
    p1 : (x, y)
        Current position.
    p2 : (x, y)
        Proposed next position.
    tp : (x, y)
        Final target point we ultimately want to reach.
    max_variance : float, default 45
        Allowed deviation (±) from the `p1→tp` heading.

    Returns
    -------
    (x, y)
        New next position, keeping the same step length as p1→p2
        but adjusted to satisfy the angle constraint.
    """
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    dist   = math.hypot(dx, dy)
    if dist == 0:
        return p2                       # no movement → nothing to adjust

    cur_dir = _norm(math.degrees(math.atan2(dy, dx)))
    tgt_dir = _norm(math.degrees(math.atan2(tp[1] - p1[1], tp[0] - p1[0])))
    delta   = _angle_diff(tgt_dir, cur_dir)

    # Inside the cone? keep original p2
    if abs(delta) <= max_variance:
        return p2

    # Clamp to the closest boundary of the cone centred on target heading
    new_dir = tgt_dir + (max_variance if delta > 0 else -max_variance)
    new_dx, new_dy = _polar_to_xy(_norm(new_dir), dist)
    return p1[0] + new_dx, p1[1] + new_dy

# ── click helpers (unchanged API) ──────────────────────────
def click(
        x=-1, y=-1, 
        click_type=ClickType.LEFT,
        click_cnt=1, min_click_interval=.3):
    def _do_click():
        time.sleep(random.uniform(.05, .15))
        duration = random.uniform(.05, .25)
        if click_type == ClickType.LEFT:
            pyautogui.click(duration=duration)
        elif click_type == ClickType.RIGHT:
            pyautogui.rightClick(duration=duration)
        elif click_type == ClickType.MIDDLE:
            pyautogui.middleClick(duration=duration)

    _block(True)
    try:
        is_already_there = pyautogui.position() == (x,y)
        if x >= 0 and y >= 0 and not is_already_there:
            move_to(x, y)

        _do_click()
        for _ in range(click_cnt-1):
            time.sleep(random.uniform(min_click_interval, min_click_interval*1.4))
            _do_click()
    finally:
        _block(False)

    
    
    

    

def move_to_match(match: MatchResult, **kw):
    _block(True)
    try:  move_to(*match.get_point_within(), **kw)
    finally:  _block(False)

def click_in_match(
        match: MatchResult, click_cnt=1, 
        min_click_interval=.3, click_type=ClickType.LEFT
    ):
    
    x, y = match.get_point_within()
    click(x, y, click_type, click_cnt, min_click_interval)



# ────────────────────────────────────────────────────────────────
#  Human-like MOVE TO  (overshoot + distance-weighted wobble)
# ────────────────────────────────────────────────────────────────
def move_to(
    tx: int,
    ty: int,
    overshoot_prob: float = .40,
    wobble_prob:   float = .8,
    pause_prob:    float = .18,
    curve_prob:    float = .6,
    overshoot_ratio=(.04, .1),
    wobble_px=(-1, -1),  # (-1,-1)  → auto-random pair
    curve_ratio=(.01,.25),

    pause_max_ms=250,
    speed: float | None = None,
    max_direction_change=30 # max change from point to point
):
    """Smooth cursor travel with human quirks."""
    if terminate:
        return

    if wobble_px == (-1, -1):          # randomise wobble magnitude once/run
        lo = random.randint(2, 8)
        wobble_px = (lo, lo + random.randint(2, 8))

    sx, sy = pyautogui.position()
    dist0  = _euclidean((sx, sy), (tx, ty))
    if dist0 < 1:
        return

    # ── pick way-points  ───────────────
    
    waypoints: list[tuple[int, int]] = []
    # ── curve
    if random.random() < curve_prob and dist0 > 40:
        midpoint = ((sx + tx) / 2, (sy + ty) / 2)
        # determine how much off the midpoint the curve should be
        change = (
            random.randint(int(curve_ratio[0]*dist0), int(curve_ratio[1]*dist0)),
            random.randint(int(curve_ratio[0]*dist0), int(curve_ratio[1]*dist0))
        )
        curvepoint = (
            int( midpoint[0] + random.choice([change[0], -change[0]]) ),
            int( midpoint[1] + random.choice([change[1], -change[1]]) ),
        )
        waypoints.append(curvepoint)

    # ── overshoot
    if random.random() < overshoot_prob and dist0 > 40:
        ux, uy = (tx - sx) / dist0, (ty - sy) / dist0
        o_dist = dist0 * random.uniform(*overshoot_ratio)
        waypoints.append((int(tx + ux * o_dist), int(ty + uy * o_dist)))
    waypoints.append((tx, ty))                       # always the real target
    last_leg = len(waypoints) - 1                   # index of final leg

    _block(True)
    try:
        prev = (sx, sy)
        for leg_idx, wp in enumerate(waypoints):
            
            def _execute_step(prev, duration, min_steps=6):
                step_start = time.time()
                seg = _euclidean(prev, wp)
                if seg < 1: return
                
                # More steps for smoother movement - increase minimum steps
                # and make steps proportional to both distance and duration
                min_steps = max(8, min_steps)
                steps = max(min_steps, int(seg / 8))
                
                # Ensure we have enough steps for the given duration
                # At least 20 steps per second for smoothness
                min_steps_for_duration = max(min_steps, int(duration * 20))
                steps = max(steps, min_steps_for_duration)
                
                # Calculate timestamps with improved easing
                t_stamps = _smooth_steps(duration, steps)
                
                # Ensure minimum step time to prevent jumpy movements
                min_step_time = 0.01  # 10ms minimum between steps
                if not is_simulation and steps > 1:
                    avg_step_time = duration / steps
                    if avg_step_time < min_step_time:
                        # Recalculate with fewer steps if moving too fast
                        steps = max(min_steps, int(duration / min_step_time))
                        t_stamps = _smooth_steps(duration, steps)

                # distance decay uses this segment's full length
                seg_total = seg

                # Create more natural control point for Bezier curve
                # Avoid extreme control point values that cause sharp curves
                ctrl_range = min(15, seg * 0.2)  # Scale control point range with distance
                ctrl = (
                    _lerp(prev[0], wp[0], .33) + random.uniform(-ctrl_range, ctrl_range),
                    _lerp(prev[1], wp[1], .33) + random.uniform(-ctrl_range, ctrl_range),
                )
                
                # Track the last position to detect large jumps
                last_pos = prev
                start = time.perf_counter()
                
                for i, tgt_t in enumerate(t_stamps, 1):
                    if terminate:
                        return

                    frac = i / steps
                    x, y = _bezier(prev, ctrl, wp, frac)
                    
                    # Calculate wobble with improved probability decay
                    # More predictable wobble effect
                    remaining_dist = _euclidean((x, y), wp) / seg_total
                    wobble_chance = wobble_prob * (remaining_dist ** 1.7)
                    wobble = random.random() < wobble_chance

                    # tighten wobble on the *very last* leg
                    if leg_idx == last_leg:
                        wobble = wobble and (random.random() < .15)
                        wob_px = (1, 4)
                    else:
                        wob_px = wobble_px

                    if wobble:
                        dx, dy = wp[0] - prev[0], wp[1] - prev[1]
                        if dx or dy:
                            perp = (-dy, dx)
                            norm = math.hypot(*perp) or 1.0
                            perp = (perp[0] / norm, perp[1] / norm)
                            a, b = perp
                            perp = (random.choice([-a, a]), random.choice([-b, b]))
                            # Scale wobble with remaining distance for smoother effect
                            mag = random.randint(*wob_px) * (1 - frac)
                            x, y = x + perp[0] * mag, y + perp[1] * mag
                    
                    # Apply direction constraints more smoothly
                    x, y = _constrain_travel(
                        pyautogui.position(), (x, y), wp,
                        max_direction_change
                    )
                    
                    # Prevent large jumps - limit maximum pixel movement per step
                    if not is_simulation:
                        curr_pos = pyautogui.position()
                        step_dist = _euclidean(curr_pos, (x, y))
                        max_step_dist = 30  # Maximum pixels per step
                        
                        if step_dist > max_step_dist:
                            # Scale down the movement to avoid jumps
                            ratio = max_step_dist / step_dist
                            x = curr_pos[0] + (x - curr_pos[0]) * ratio
                            y = curr_pos[1] + (y - curr_pos[1]) * ratio
                    
                    x = max(1, int(x))
                    y = max(1, int(y))
                    
                    # Move to the new position
                    pyautogui.moveTo(x, y, _pause=0)
                    last_pos = (x, y)
                    
                    # Handle wobble without recursion to avoid timing issues
                    if wobble and i < steps:
                        # Instead of recursively calling, just continue with adjusted timing
                        continue
                        
                    # occasional micro-pause
                    if not is_simulation:
                        if (
                            pause_prob > 0
                            and leg_idx == 0
                            and .45 < frac < .55
                            and random.random() < .10
                        ):
                            time.sleep(random.uniform(.03, pause_max_ms / 1000))
                        
                        # Improved timing control
                        elapsed = time.perf_counter() - start
                        sleep_time = max(0, tgt_t - elapsed)
                        
                        # Ensure we don't sleep too long (system might be busy)
                        if sleep_time > 0.1:  # Cap very long sleeps
                            sleep_time = min(sleep_time, 0.1)
                            
                        time.sleep(sleep_time)

            # ── timing baseline (cubic ease) ─────────────────────────────────
            step_distance = _euclidean(prev, wp)

            # Ensure minimum movement time regardless of distance
            min_duration = 0.1  # Never move faster than this many seconds
            
            if speed is not None:
                # speed = pixels per second → duration = dist / speed
                base_dur = step_distance / speed
            else:
                # Improved duration calculation with better lower bounds
                base_dur = (step_distance / 700) * movement_multiplier
                base_dur = max(0.05, min(base_dur, 0.5))  # Increased minimum from 0.03 to 0.05
                
            # Ensure minimum duration for very short movements
            base_dur = max(min_duration, base_dur)
            
            # Add slight randomness but keep it consistent
            base_dur *= random.uniform(0.97, 1.03)  # Reduced variation range
            
            # run
            _execute_step(prev, base_dur)
            prev = wp
            
    finally:
        _block(False)

# ────────────────────────────────────────────────────────────────
#  RANDOM DOUBLE-CLICK  (unchanged)
# ────────────────────────────────────────────────────────────────
def random_double_click(x, y, variance=5, **move_kw):
    if terminate:
        return
    _block(True)
    try:
        pyautogui.mouseUp()
        tx = x + random.randint(-variance, variance)
        ty = y + random.randint(-variance, variance)
        move_to(tx, ty, **move_kw)     # primary travel
        pyautogui.click()
        time.sleep(random.uniform(.12, .35))
        move_to(tx, ty, overshoot_prob=0)  # settle
        pyautogui.click()
    finally:
        _block(False)

# ────────────────────────────────────────────────────────────────
#  LIGHTWEIGHT VISUAL SIMULATOR  (run with  `--sim`)
# ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse, sys
    parser = argparse.ArgumentParser()
    parser.add_argument("--sim", action="store_true", help="run visual path demo")
    args = parser.parse_args()

    if not args.sim:
        sys.exit(0)

    is_simulation = True

    # --- sim deps kept optional so production imports stay lean -----
    from PIL import Image, ImageDraw, ImageColor
    import numpy as np

    W = H = 1000
    STARTS = [
        (int(W//20), int(W//20)),
        (H-int(H//20), int(W//20)),
        (int(H//20), W-int(W//20)),
        (H-int(H//20), W-int(W//20)),
        
        (int(H//20), int(W//2)),
        (H-int(H//20), int(W//2)),
        (int(W/2), int(W//20)),
        (int(W/2), H-int(W//20))
    ]
    TARGET = (W // 2, H // 2)

    def simulate(sim_cnt=1):
        global pyautogui
        img = Image.new("RGB", (W, H), (30, 30, 30))
        draw = ImageDraw.Draw(img)
        draw.rectangle([TARGET[0] - 7, TARGET[1] - 7, TARGET[0] + 7, TARGET[1] + 7],
                    outline="white", width=2)
        
        # stub-pyautogui for off-screen drawing
        class _StubAG:
            _pos = (0,0)
            _color = (255,0,0)
            @classmethod
            def position(cls):
                return tuple(cls._pos)
            @classmethod
            def moveTo(cls, x, y, _pause=0):
                draw.line([cls._pos, (x, y)], fill=cls._color, width=1)
                #draw.rectangle([(x-1,y-1),(x+1,y+1)],"blue")
                cls._pos = [x, y]
        pyautogui = _StubAG  # type: ignore
        for start in STARTS:
            
            draw.rectangle([start[0] - 10, start[1] - 10, start[0] + 10, start[1] + 10],
                    fill="cyan")
            for seed in range(sim_cnt):
                pyautogui._pos = start
                # random.seed(seed); np.random.seed(seed)

                move_to(
                    *TARGET,
                    pause_prob=0,
                    overshoot_prob=.4
                )

        img.show()          # opens default viewer; close it to end sim
    
    simulate(1)
    # simulate(10)
    # simulate(100)
    # simulate(1000)