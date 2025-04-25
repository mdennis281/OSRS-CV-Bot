import pygetwindow as gw
import pyautogui
import mss
import time
from PIL import Image
import io
from tools import find_subimage, MatchResult, MatchShape, timeit
from mouse_control import click_in_match, move_to
import cv2
import numpy as np
from dataclasses import field
from item_db import ItemLookup, Item
from enum import Enum
import random

class ToolplaneTab(Enum):
    COMBAT = "combat"
    SKILLS = "skills"
    PROGRESS = "progress"
    INVENTORY = "inventory"
    EQUIPMENT = "equipment"
    PRAYER = "prayer"
    SPELLS = "spells"
    GROUPS = "groups"
    FRIENDS = "friends"
    ACCOUNT = "account"
    LOGOUT = "logout"
    SETTINGS = "settings"
    EMOTES = "emotes"
    MUSIC = "music"

class MinimapElement(Enum):
    HEALTH = "health"
    PRAYER = "prayer"
    RUN = "run"
    SPEC = "spec"

class GenericWindow:
    def __init__(self, window_title):
        self.window_title = window_title
        self.window: gw.Win32Window = None
        self.update_window()

    def update_window(self) -> gw.Win32Window:
        """Finds and updates the RuneLite window reference."""
        windows = gw.getWindowsWithTitle(self.window_title)
        self.window = windows[0] if windows else None

    @property
    def is_open(self):
        """Returns True if the RuneLite window is open, False otherwise."""
        self.update_window()
        return self.window is not None

    @property
    def dimensions(self):
        """Returns the (width, height) of the RuneLite window."""
        if self.is_open:
            return (self.window.width, self.window.height)
        return None

    @property
    def coordinates(self):
        """Returns the (x, y) position of the RuneLite window."""
        if self.is_open:
            return (self.window.left, self.window.top)
        return None

    def bring_to_focus(self):
        """Brings the RuneLite window to the foreground."""
        if self.is_open:
            try:
                self.window.activate()
            except:
                self.window.minimize()
                self.window.restore()
        time.sleep(.3)

    def move_off_window(self,offset = 45):
        """Randomly moves the window 5px outside the screen in a random direction."""
        if not self.is_open:
            return

        directions = ["up", "down", "left", "right"]
        direction = np.random.choice(directions)
        

        if direction == "up":
            new_x = random.randint(
                self.window.left,
                self.window.right
            )
            new_y = self.window.top - offset
        elif direction == "down":
            new_x = random.randint(
                self.window.left,
                self.window.left + self.window.width
            )
            new_y = self.window.bottom + offset
        elif direction == "left":
            new_x = self.window.left - offset
            new_y = random.randint(
                self.window.top,
                self.window.top + self.window.height
            )
        elif direction == "right":
            new_x = self.window.right + offset
            new_y = random.randint(
                self.window.top,
                self.window.top + self.window.height
            )

        # Move the window to the new position
        move_to(new_x, new_y)

    @timeit
    def get_screenshot(self, maximize=True) -> Image.Image:
        """Captures and returns a screenshot of the RuneLite window as a PIL image."""
        if maximize:
            self.bring_to_focus()
        if not self.is_open:
            return None
        
        with mss.mss() as sct:
            bbox = (self.window.left, self.window.top, self.window.left + self.window.width, self.window.top + self.window.height)
            sct_img = sct.grab(bbox)
            img = Image.frombytes('RGB', sct_img.size, sct_img.rgb)
            return img

    def save_screenshot(self, filename="runelite_screenshot.png"):
        """Saves a screenshot of the RuneLite window to a file."""
        screenshot = self.get_screenshot()
        if screenshot:
            screenshot.save(filename)
            return filename
        return None
    
    @timeit
    def find_in_window(
            self, img: Image.Image, screenshot: Image=None,
            min_scale: float = 0.9, max_scale: float = 1.1
        ) -> MatchResult:
        """Finds a subimage within the RuneLite window."""
        screenshot = screenshot or self.get_screenshot()
        return find_subimage(screenshot, img, min_scale=min_scale, max_scale=max_scale)
    
    def show_in_window(self, match: MatchResult, screenshot: Image=None, color="red"):
        """Draws a box around the found match in the screenshot."""
        screenshot = screenshot or self.get_screenshot()
        if screenshot:
            img_with_box = match.debug_draw(screenshot, color=color)
            img_with_box.show()

    def click(self, match: MatchResult, click_cnt:int=1, min_click_interval: float = 0.3):
        """Clicks on the center of the matched area."""
        match = match.transform(self.window.left, self.window.top)
        click_in_match(match, click_cnt=click_cnt, min_click_interval=min_click_interval)


        


class RuneLiteClient(GenericWindow):
    def __init__(self,username=''):
        super().__init__(f'RuneLite - {username}')
        self.minimap = MinimapContext()
        self.toolplane = ToolplaneContext()
        self.item_db = ItemLookup()
        self._last_screenshot = None
        self.on_resize()

    @property
    def screenshot(self) -> Image.Image:
        if self._last_screenshot:
            return self._last_screenshot
        return self.get_screenshot()
    @timeit
    def click_minimap(self, element: MinimapElement, click_cnt:int=1):
        self.minimap.find_matches(self.screenshot) # todo: efficiency
        match: MatchResult = getattr(self.minimap, element.value)
        self.click(match, click_cnt=click_cnt)

    
    @timeit    
    def click_toolplane(self, tab: ToolplaneTab,reload_on_tab_change:bool=True):
        self.toolplane.find_matches(self.screenshot)
        match = getattr(self.toolplane, tab.value)

        if self.toolplane.get_active_tab(self.screenshot) != tab.value:
            self.click(match)
            if reload_on_tab_change: 
                # necessary for getting active tab
                self.get_screenshot()

    @timeit
    def get_minimap_stat(self, element: MinimapElement) -> int:
        self.get_screenshot()
        self.minimap.find_matches(self.screenshot)
        match = getattr(self.minimap, element.value)
        stat = self.minimap.get_minimap_stat(match, self.screenshot)
        if stat:
            return int(stat)
        return None
            
    @timeit
    def click_item(
            self,
            item_identifier: str | int,
            tab: ToolplaneTab = ToolplaneTab.INVENTORY,
            click_cnt: int = 1,
            min_confidence=0.7,
            min_click_interval: float = 0.3
    ):
        self.get_screenshot()
        self.click_toolplane(tab)

        if isinstance(item_identifier, str):
            item = self.item_db.get_item_by_name(item_identifier)
        elif isinstance(item_identifier, int):
            item = self.item_db.get_item_by_id(item_identifier)
        
        if not isinstance(item, Item):
            raise ValueError(f'Item : {item_identifier} not found in database.')
        
        match = self.find_in_window(item.icon, self.screenshot)

        print(f"Item: {item.name} Confidence: {match.confidence}")
        
        if match.confidence < min_confidence:
            raise ValueError(f"Item {item.name} not found in window. Confidence: {match.confidence}")
            
        self.click(match, click_cnt=click_cnt, min_click_interval=min_click_interval)






    
    def debug_minimap(self):
        self.get_screenshot()
        self.minimap.find_matches(self.screenshot)
        self.minimap.health.debug_draw(self.screenshot, color=(0, 255, 0))
        self.minimap.prayer.debug_draw(self.screenshot, color=(0, 0, 255))
        self.minimap.run.debug_draw(self.screenshot, color=(255, 0, 0))
        self.minimap.spec.debug_draw(self.screenshot, color=(255, 255, 0))
        find_subimage(self.screenshot, Image.open("ui_icons/map.webp")).debug_draw(self.screenshot, color=(255, 255, 255))
        # health_val = self.minimap.get_minimap_stat(self.minimap.health, self.screenshot)
        # print(f"Health: {health_val}")
        # prayer_val = self.minimap.get_minimap_stat(self.minimap.prayer, self.screenshot)
        # print(f"Prayer: {prayer_val}")
        # run_val = self.minimap.get_minimap_stat(self.minimap.run, self.screenshot)
        # print(f"Run: {run_val}")
        # spec_val = self.minimap.get_minimap_stat(self.minimap.spec, self.screenshot)
        # print(f"Spec: {spec_val}")
        self.screenshot.show()

    def debug_toolplane(self):
        self.get_screenshot()
        self.toolplane.find_matches(self.screenshot)
        active_tab = self.toolplane.get_active_tab(self.screenshot)
        print(f"Active Tab: {active_tab}")
        for variable in vars(self.toolplane):
            match = getattr(self.toolplane, variable)
            if match and isinstance(match, MatchResult):
                color = (0, 255, 0) if variable == active_tab else (255, 0, 0)
                match.debug_draw(self.screenshot, color=color)
                print(f"{variable}: {match}")

        #self.screenshot.show()

    
    def on_resize(self):
        sc = self.get_screenshot()
        self.minimap.find_matches(sc)
        self.toolplane.find_matches(sc)

    def get_screenshot(self, maximize=True) -> Image.Image:
        self._last_screenshot = super().get_screenshot(maximize)
        return self._last_screenshot
        
        

    @property
    def quick_prayer_active(self) -> bool:
        """Checks if the quick prayer is active in the RuneLite window."""
        qp_disabled = Image.open("./ui_icons/quick-prayer-disabled.png")
        qp_enabled = Image.open("./ui_icons/quick-prayer-enabled.png")
        
        disabled_match = self.find_in_window(qp_disabled, self.screenshot)
        enabled_match = self.find_in_window(qp_enabled, self.screenshot)
        
        if enabled_match.confidence > disabled_match.confidence:
            return True
        return False
    

    

class ToolplaneContext:
    combat:    MatchResult = None
    skills:    MatchResult = None
    progress:  MatchResult = None
    inventory: MatchResult = None
    equipment: MatchResult = None
    prayer:    MatchResult = None
    spells:    MatchResult = None
    groups:    MatchResult = None
    friends:   MatchResult = None
    account:   MatchResult = None
    logout:    MatchResult = None
    settings:  MatchResult = None
    emotes:    MatchResult = None
    music:     MatchResult = None


    @timeit
    def find_matches(self, screenshot: Image.Image):
        """Finds and sets the matches for various UI elements."""
        self.combat    = find_subimage(screenshot, Image.open("ui_icons/combat.webp"),    min_scale=0.9, max_scale=1.1)
        self.skills    = find_subimage(screenshot, Image.open("ui_icons/stats.webp"),     min_scale=0.9, max_scale=1.1)
        # self.progress = find_subimage(...)
        self.inventory = find_subimage(screenshot, Image.open("ui_icons/inventory.webp"), min_scale=0.9, max_scale=1.1)
        self.equipment = find_subimage(screenshot, Image.open("ui_icons/equipment.webp"), min_scale=0.9, max_scale=1.1)
        self.prayer    = find_subimage(screenshot, Image.open("ui_icons/prayer.webp"),    min_scale=0.9, max_scale=1.1)
        self.spells    = find_subimage(screenshot, Image.open("ui_icons/spellbook.webp"), min_scale=0.9, max_scale=1.1)
        # self.groups   = find_subimage(...)
        # self.friends  = find_subimage(...)
        self.account   = find_subimage(screenshot, Image.open("ui_icons/account.webp"),   min_scale=0.9, max_scale=1.1)
        self.logout    = find_subimage(screenshot, Image.open("ui_icons/logout.webp"),    min_scale=0.9, max_scale=1.1)
        self.settings  = find_subimage(screenshot, Image.open("ui_icons/settings.webp"),  min_scale=0.9, max_scale=1.1)
        self.emotes    = find_subimage(screenshot, Image.open("ui_icons/emotes.webp"),    min_scale=0.9, max_scale=1.1)
        self.music     = find_subimage(screenshot, Image.open("ui_icons/music.webp"),     min_scale=0.9, max_scale=1.1)

    def _is_tab_active(self,
            screenshot: Image.Image,
            match: MatchResult,
            pad: int = 4,
        ) -> float:
        """
        Returns the fraction of pixels in the padded match box
        that fall into the 'red' HSV range.
        """
        # Crop with padding
        x1 = max(match.start_x - pad, 0)
        y1 = max(match.start_y - pad, 0)
        x2 = min(match.end_x + pad, screenshot.width)
        y2 = min(match.end_y + pad, screenshot.height)
        patch = screenshot.crop((x1, y1, x2, y2)).convert("RGB")
        arr   = np.array(patch)

        # Convert to HSV
        hsv = cv2.cvtColor(arr, cv2.COLOR_RGB2HSV)
        # Two red hue ranges
        lo1, hi1 = np.array([0, 50, 50]),  np.array([10, 255, 255])
        lo2, hi2 = np.array([160, 50, 50]), np.array([180, 255, 255])
        m1 = cv2.inRange(hsv, lo1, hi1)
        m2 = cv2.inRange(hsv, lo2, hi2)
        red_mask = cv2.bitwise_or(m1, m2)

        # Fraction of red pixels
        return red_mask.mean() / 255.0

    def get_active_tab(self, screenshot: Image.Image) -> str | None:
        """
        Returns the name of the active tab (highest red‐ratio),
        or None if no tab exceeds the threshold.
        """
        best_tab = None
        best_score = 0.0
        for variable in vars(self):
            match = getattr(self, variable)
            if not isinstance(match, MatchResult):
                continue
            score = self._is_tab_active(screenshot, match)
            if score > best_score:
                best_score = score
                best_tab = variable

            

        # you can choose to only return if best_score > some threshold
        return best_tab
    

class MinimapContext:
    health: MatchResult = None
    prayer: MatchResult = None
    run: MatchResult = None
    spec: MatchResult = None

    def get_minimap_stat(self,match: MatchResult, screenshot: Image.Image) -> int:
        """Returns the health value from the screenshot."""
        val = match.transform(-22, 11)
        val.end_x = val.start_x + 21
        val.end_y = val.start_y + 13
        val.shape = MatchShape.SQUARE
        

        return val.extract_text(screenshot)
    @timeit
    def find_matches(self, screenshot: Image.Image):
        """Finds and sets the matches for health, prayer, run, and spec."""

        map = find_subimage(screenshot, Image.open("ui_icons/map.webp"))
        map.shape = MatchShape.CIRCLE
        self.health = map.transform(-152, -77)
        self.prayer = map.transform(-152, -43)
        self.run = map.transform(-142, -11)
        self.spec = map.transform(-120, 15)

        # make match mildly smaller
        for variable in vars(self):
            match = getattr(self, variable)
            if isinstance(match, MatchResult):
                match.scale_px(-3)
    
    

# Example usage
if __name__ == "__main__":
    rl_client = RuneLiteClient()
    
    if rl_client.is_open:
        print(f"RuneLite is open at {rl_client.coordinates} with size {rl_client.dimensions}")
        rl_client.bring_to_focus()
        rl_client.save_screenshot()
        print("Screenshot saved.")
    else:
        print("RuneLite is not open.")
