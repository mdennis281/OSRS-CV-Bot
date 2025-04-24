"""
human_mouse.py  –  v1.1
"""
from __future__ import annotations
import ctypes, math, random, time
import pyautogui, keyboard
from tools import MatchResult          # your class

# ── global knobs ───────────────────────────────────────────
user32              = ctypes.windll.user32
terminate           = False          # Esc listener toggles this
movement_multiplier = 0.35           # lower = faster (was 0.5)

# ── helpers ────────────────────────────────────────────────
def _euclidean(p1, p2):    return math.hypot(p2[0]-p1[0], p2[1]-p1[1])
def _lerp(a,b,t):          return a + (b-a)*t
def _bezier(p0,p1,p2,t):
    return (_lerp(_lerp(p0[0],p1[0],t), _lerp(p1[0],p2[0],t), t),
            _lerp(_lerp(p0[1],p1[1],t), _lerp(p1[1],p2[1],t), t))
def _smooth_steps(total, n):
    return [total*(3*(i/n)**2 - 2*(i/n)**3) for i in range(1,n+1)]
def _block(on=True):       user32.BlockInput(bool(on))

# ── click helpers (unchanged API) ──────────────────────────
def click(x=-1, y=-1):
    if x >= 0 and y >= 0:
        move_to(x, y)
    pyautogui.click()

def move_to_match(match: MatchResult, **kw):
    _block(True)
    try:  move_to(*match.get_point_within(), **kw)
    finally:  _block(False)

def click_in_match(match: MatchResult, click_cnt=1, min_click_interval=.3, **kw):
    _block(True)
    try:
        x, y = match.get_point_within()
        click(x, y)
        for _ in range(click_cnt-1):
            time.sleep(random.uniform(min_click_interval, min_click_interval*1.4))
            click(x, y)
    finally:  _block(False)

# ── ⭐ human-like move_to() ⭐ ───────────────────────────────
def move_to(
    tx: int, ty: int,
    *,
    overshoot_prob=.65, wobble_prob=.70, pause_prob=.18,
    overshoot_ratio=(.07, .18), wobble_px=(1, 8), pause_max_ms=250,
    speed: float | None = None,
):
    """ Cursor travel with optional human quirks. """
    if terminate: return
    sx, sy       = pyautogui.position()
    dist         = _euclidean((sx, sy), (tx, ty))
    if dist == 0:   # already there
        return

    # which quirks fire?
    do_os  = random.random() < overshoot_prob and dist > 40
    do_pau = random.random() < pause_prob     and dist > 80

    # timing
    base_dur = (dist / 700) * (movement_multiplier if speed is None else speed)
    base_dur *= random.uniform(.85, 1.15)
    base_dur  = max(.04, base_dur)

    # way-points
    waypoints = []
    if do_os:
        dx, dy  = tx - sx, ty - sy
        ux, uy  = dx/dist, dy/dist
        odist   = dist * random.uniform(*overshoot_ratio)
        waypoints += [(int(tx+ux*odist), int(ty+uy*odist)), (tx, ty)]
    else:
        waypoints.append((tx, ty))

    _block(True)
    try:
        prev = (sx, sy)
        for wp in waypoints:
            seg = _euclidean(prev, wp)
            steps = max(6, int(seg/12))
            t_stamps = _smooth_steps(base_dur*(seg/dist), steps)

            ctrl = (_lerp(prev[0], wp[0], .33)+random.randint(-15,15),
                    _lerp(prev[1], wp[1], .33)+random.randint(-15,15))

            for i, tgt_t in enumerate(t_stamps, 1):
                if terminate: return
                frac = i/steps
                x, y = _bezier(prev, ctrl, wp, frac)

                # wobble
                if random.random() < wobble_prob:
                    dx, dy = wp[0]-prev[0], wp[1]-prev[1]
                    if dx or dy:
                        perp = (-dy, dx); norm = math.hypot(*perp)
                        perp = (perp[0]/norm, perp[1]/norm)
                        mag  = random.randint(*wobble_px) * (1-frac)
                        x, y = x+perp[0]*mag, y+perp[1]*mag

                # dont allow sub-zero
                if x < 0: x = 0
                if y < 0: y = 0

                pyautogui.moveTo(int(x), int(y), _pause=0)

                # micro-pause
                if do_pau and .45 < frac < .55 and random.random() < .1:
                    time.sleep(random.uniform(.03, pause_max_ms/1000))

                # ease timing
                if i==1: start = time.perf_counter()
                else:
                    sleep = max(0, tgt_t - (time.perf_counter()-start))
                    time.sleep(sleep)
            prev = wp
    finally:
        _block(False)

# ── ✔  random double click (restored) ──────────────────────
def random_double_click(x, y, variance=5, **move_kw):
    if terminate: return
    _block(True)
    try:
        pyautogui.mouseUp()                       # drop any drag
        tx = x + random.randint(-abs(variance),  abs(variance))
        ty = y + random.randint(-abs(variance),  abs(variance))
        move_to(tx, ty, **move_kw)               # first travel
        pyautogui.click()
        time.sleep(random.uniform(.12, .35))
        move_to(tx, ty, overshoot_prob=0)        # re-settle
        pyautogui.click()
    finally:
        _block(False)

