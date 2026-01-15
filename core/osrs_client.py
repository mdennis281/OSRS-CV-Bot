import mss
import time
from PIL import Image
import io
from core.tools import (
    find_subimage, MatchResult, MatchShape, timeit, write_text_to_image,
    find_color_box, seconds_to_hms, find_subimages
)
from core.input.mouse_control import click_in_match, move_to, ClickType, click
from core import ocr
from typing import Tuple, List, Optional, Dict, Any
import threading
import cv2
import numpy as np
from dataclasses import field
from core.item_db import ItemLookup, Item
from enum import Enum
import random
from pathlib import Path
import keyboard
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_EXCEPTION, TimeoutError, as_completed

from core import tools
from core.control import ScriptControl, ScriptTerminationException
import os
import sys
import pyautogui
from core.window_manager import WindowManager
from PIL import ImageFilter
from core.ocr.custom import read_location_numbers
from core.logger import get_logger

# Constants
MAXTHREAD = os.cpu_count()
control = ScriptControl()
POSITION_STATE = Image.open('data/ui/player-position-state.png')
ACTION_HOVER = Image.open('data/ui/action-hover.png')

# Centralized randomness configuration for user interaction behavior
@dataclass
class InteractionRandomness:
    """Default/random behavior tuning for mouse movement and clicks.

    Attributes:
        rand_move_chance: Probability to make a small random move before an action.
        after_click_settle_chance: Probability to pause briefly after a click.
        after_click_settle_sleep: Range (min,max) seconds for post-click settle sleep.
        off_window_offset: Default pixel offset used by move_off_window.
    """
    rand_move_chance: float = 0.1
    after_click_settle_chance: float = 0.1
    after_click_settle_sleep: tuple[float, float] = (0.2, 0.6)
    off_window_offset: int = 45

    def settle_sleep(self) -> float:
        return random.uniform(self.after_click_settle_sleep[0], self.after_click_settle_sleep[1])

# Enums for toolplane tabs and minimap elements
class ToolplaneTab(Enum):
    """Represents the tabs in the RuneLite toolplane."""
    COMBAT = "combat"
    SKILLS = "skills"
    PROGRESS = "progress"
    INVENTORY = "inventory"
    EQUIPMENT = "equipment"
    PRAYER = "prayer"
    SPELLS = "spells"
    GROUPS = "friends"
    ACCOUNT = "account"
    LOGOUT = "logout"
    SETTINGS = "settings"
    EMOTES = "emotes"
    MUSIC = "music"

class MinimapElement(Enum):
    """Represents elements in the RuneLite minimap."""
    HEALTH = "health"
    PRAYER = "prayer"
    RUN = "run"
    SPEC = "spec"

class GenericWindow:
    """Represents a generic window with functionality to interact with it."""
    def __init__(self, window_title: str, randomness: InteractionRandomness | None = None):
        """
        Initialize the GenericWindow instance.

        Args:
            window_title (str): The title of the window to interact with.
            randomness (InteractionRandomness | None): Optional behavior config to
                tune default random movement/click behavior.
        """
        self.log = get_logger('GenericWindow')
        self.window_title = window_title
        self.window = None
        self._last_screenshot: Image.Image = None
        self.window_manager = WindowManager.create()
        self.update_window()
        # Default/random behavior settings
        self.randomness: InteractionRandomness = randomness or InteractionRandomness()

    def update_window(self):
        """
        Finds and updates the window reference.

        Returns:
            The updated window reference.
        """
        windows = self.window_manager.get_windows_with_title(self.window_title)
        if not self.window and windows:
            self.log.debug(f'Window found with title: {windows[0].title}')
            self.log.debug(f'Window dimensions: {windows[0].width}x{windows[0].height} at ({windows[0].left}, {windows[0].top})')
        self.window = windows[0] if windows else None
        return self.window

    def start_resize_watch_polling(self, on_resize=None, interval=0.5):
        """
        Starts a thread to monitor window resizing.

        Args:
            on_resize (callable, optional): Callback function for resize events.
            interval (float, optional): Polling interval in seconds.

        Returns:
            threading.Event: Event to stop the polling.
        """
        def _get_window_position():
            return [
                (self.window.width, self.window.height),
                (self.window.left, self.window.top)
            ]
        def _loop():
            last = _get_window_position()
            while not stop_evt.is_set():
                if control.terminate:
                    self.log.info('Term signaled, stopping resize watch polling.')
                    break
                if self.is_open:
                    position = _get_window_position()
                    if position != last:
                        last = position
                        try:
                            if on_resize:
                                on_resize()
                            else:
                                self.on_resize()
                        except ScriptTerminationException:
                            break
                stop_evt.wait(interval)

        stop_evt = threading.Event()
        threading.Thread(target=_loop, daemon=True).start()
        return stop_evt  # Caller can call .set() to stop

    @control.guard
    def on_resize(self):
        """
        Default resize handler. Can be overridden by subclasses.
        """
        self.log.info('On resize called, but no handler defined.')

    @property
    def screenshot(self) -> Image.Image:
        """
        Returns the last cached screenshot or captures a new one.

        Returns:
            Image.Image: The screenshot of the window.
        """
        if self._last_screenshot:
            return self._last_screenshot
        return self.get_screenshot()

    @property
    def is_open(self) -> bool:
        """
        Checks if the RuneLite window is open.

        Returns:
            bool: True if the window is open, False otherwise.
        """
        #self.update_window()
        return self.window is not None

    @property
    def dimensions(self) -> Tuple[int, int]:
        """
        Gets the dimensions of the RuneLite window.

        Returns:
            Tuple[int, int]: The width and height of the window.
        """
        if not self.is_open:
            self.bring_to_focus()
        return (self.window.width, self.window.height)

    @property
    def coordinates(self) -> Tuple[int, int]:
        """
        Gets the coordinates of the RuneLite window.

        Returns:
            Tuple[int, int]: The x and y position of the window.
        """
        if not self.is_open:
            self.bring_to_focus()
        return (self.window.left, self.window.top)

    @property
    def window_match(self) -> MatchResult:
        """
        Gets the match result for the window's bounding box.

        Returns:
            MatchResult: The match result for the window.
        """
        x1, y1 = self.coordinates
        w, h = self.dimensions
        x2, y2 = (x1 + w, y1 + h)
        return MatchResult(
            x1, y1, x2, y2,
            1, 1,
            MatchShape.RECT
        )

    @control.guard
    def bring_to_focus(self):
        """
        Brings the RuneLite window to the foreground using platform-specific window manager.
        """
        if self.is_open:
            # Use the platform-specific implementation from the window manager
            self.window.bring_to_focus()

    def move_off_window(self, offset: int | None = None):
        """
        Randomly moves the window slightly outside the screen in a random direction.

        Args:
            offset (int | None): Offset in pixels for the movement. If None, uses
                InteractionRandomness.off_window_offset.
        """
        if not self.is_open:
            return

        if offset is None:
            offset = self.randomness.off_window_offset

        directions = ["up", "down", "left", "right"]
        direction = np.random.choice(directions)

        if direction == "up":
            new_x = random.randint(self.window.left, self.window.right)
            new_y = self.window.top - offset
        elif direction == "down":
            new_x = random.randint(self.window.left, self.window.left + self.window.width)
            new_y = self.window.bottom + offset
        elif direction == "left":
            new_x = self.window.left - offset
            new_y = random.randint(self.window.top, self.window.top + self.window.height)
        elif direction == "right":
            new_x = self.window.right + offset
            new_y = random.randint(self.window.top, self.window.top + self.window.height)

        # Move the window to the new position
        try:
            move_to(new_x, new_y)
        except pyautogui.FailSafeException as e:
            self.log.warning(f'Failed to move off window!! {e}')

    @timeit
    @control.guard
    def get_screenshot(self, maximize=True) -> Image.Image:
        """
        Captures and returns a screenshot of the RuneLite window.

        Args:
            maximize (bool, optional): Whether to bring the window to focus before capturing.

        Returns:
            Image.Image: The screenshot of the window.
        """
        if maximize:
            self.bring_to_focus()
        if not self.is_open:
            raise RuntimeError(f'Window {self.window_title} is not open.')

        with mss.mss(with_cursor=True) as sct:
            bbox = (self.window.left, self.window.top, self.window.left + self.window.width, self.window.top + self.window.height)
            sct_img = sct.grab(bbox)
            img = Image.frombytes('RGB', sct_img.size, sct_img.rgb)

        self._last_screenshot = img
        return self._last_screenshot

    def save_screenshot(self, filename="runelite_screenshot.png") -> str | None:
        """
        Saves a screenshot of the RuneLite window to a file.

        Args:
            filename (str, optional): The filename to save the screenshot.

        Returns:
            str | None: The filename if saved successfully, None otherwise.
        """
        screenshot = self.get_screenshot()
        if screenshot:
            screenshot.save(filename)
            return filename
        return None
    
    @timeit
    def find_in_window(
            self, img: Image.Image, screenshot: Image.Image=None,
            min_scale: float = 0.9, max_scale: float = 1.1,
            min_confidence: float = 0.7, sub_match: MatchResult = None
        ) -> MatchResult:
        """Finds a subimage within the RuneLite window."""
        screenshot = screenshot or self.get_screenshot()

        if sub_match: 
            screenshot = sub_match.crop_in(screenshot)

        ans = find_subimage(
            screenshot, img, 
            min_scale=min_scale, max_scale=max_scale,
        )
        if min_confidence > ans.confidence:
            raise ValueError(f'Match did not meet minimum confidence {ans.confidence}')
        
        if sub_match:
            ans = ans.transform(
                sub_match.start_x, sub_match.start_y
            )
        
        return ans
    
    def show_in_window(self, match: MatchResult, screenshot: Image=None, color="red"):
        """Draws a box around the found match in the screenshot."""
        screenshot = screenshot or self.get_screenshot()
        if screenshot:
            img_with_box = match.debug_draw(screenshot, color=color)
            img_with_box.show()

    def find_img_in_window(self, img: Image.Image, sub_match: MatchResult = None, confidence=.95):
        sc = self.get_screenshot()
        if sub_match:
            sc = sub_match.crop_in(sc)
        match: MatchResult = find_subimage(sc,img,min_scale=1,max_scale=1)
        if confidence > match.confidence:
            raise ValueError(f'Match did not meet confidence threshold {match.confidence}')

        if sub_match:
            match.transform(sub_match.start_x,sub_match.start_y)
        
        return match
        

    
    @control.guard
    def move_to(self,match: MatchResult | Tuple[int], 
                rand_move_chance: float | None = None,
                translated=False, parent_sectors: List[MatchResult]=[]):
        
        

        if isinstance(match, MatchResult):
            for sector in parent_sectors:
                match = match.transform(sector.start_x,sector.start_y)
            x,y = match.get_point_within()
        else:
            x,y = match
            x,y = match
        # todo: sector support???
        if not translated:
            x += self.window.left
            y += self.window.top

        # move the mouse around a bit
        chance = self.randomness.rand_move_chance if rand_move_chance is None else rand_move_chance
        if random.random() < chance:
            self.move_to(self.window_match,translated=True)
            
        move_to(x,y)


    def click(
            self, match: MatchResult | Tuple[int], 
            click_cnt:int=1, min_click_interval: float = 0.3, 
            click_type=ClickType.LEFT, parent_sectors: List[MatchResult]=[],
            rand_move_chance: float | None = None, after_click_settle_chance: float | None = None):
        """Clicks on the center of the matched area."""

        # subimage in subimage, revert back to sc match

        self.bring_to_focus()

        if isinstance(match, tuple):
            x,y = match
            # todo: sector support???
            x += self.window.left
            y += self.window.top
            
        else:
            for sector in parent_sectors:
                match = match.transform(sector.start_x,sector.start_y)
        
            match = match.transform(self.window.left, self.window.top)
            x,y = match.get_point_within()


        # Resolve configured defaults
        rand_move_chance = self.randomness.rand_move_chance if rand_move_chance is None else rand_move_chance
        after_click_settle_chance = (
            self.randomness.after_click_settle_chance if after_click_settle_chance is None else after_click_settle_chance
        )

        self.move_to((x,y),rand_move_chance, translated=True) 
        click(
            -1,-1,
            click_type=click_type,
            click_cnt=click_cnt, 
            min_click_interval=min_click_interval,
        )
        if random.random() < after_click_settle_chance:
            time.sleep(self.randomness.settle_sleep())
            self.move_to(self.window_match)
            


        


class RuneLiteClient(GenericWindow):
    def __init__(self,username='', randomness: InteractionRandomness | None = None):
        start_time = time.time()
        super().__init__(f'RuneLite - {username}', randomness=randomness)
        self.log = get_logger('RLClient')
        self.log.info('Initializing RuneLite client...')
        
        self.minimap = MinimapContext()
        self.toolplane = ToolplaneContext()
        self.item_db = ItemLookup()
        self.sectors: UISectors = UISectors()

        self.ui_type: UIType = self.get_ui_type()
        self.log.info(f'UI Type detected: {self.ui_type.value}')
        self.log.debug('Finding UI sectors...')
        
        self.on_resize()
        self.start_resize_watch_polling()
        elapsed = seconds_to_hms(time.time() - start_time)
        self.log.info(f'Client initialized successfully in {elapsed}')
        

    
    @timeit
    def click_minimap(self, element: MinimapElement, click_cnt:int=1):
        match: MatchResult = getattr(self.minimap, element.value)
        self.click(
            match, click_cnt=click_cnt,
            after_click_settle_chance=1
        )

    
    @timeit    
    def click_toolplane(self, tab: ToolplaneTab,reload_on_tab_change:bool=True):
        match = getattr(self.toolplane, tab.value)

        if self.toolplane.get_active_tab(self.screenshot) != tab.value:
            self.click(match)
            time.sleep(random.uniform(.05, .1))
            if reload_on_tab_change: 
                # necessary for getting active tab
                self.get_screenshot()

    def mouse_position(self) -> Tuple[int, int]:
        """
        Returns the current mouse position relative to the RuneLite window.
        """
        x, y = pyautogui.position()
        return (x - self.window.left, y - self.window.top)

    @timeit
    def get_minimap_stat(self, element: MinimapElement) -> int:
        self.get_screenshot()
        match = getattr(self.minimap, element.value)
        try:
            stat = self.minimap.get_minimap_stat(match, self.screenshot)
        except ocr.OcrError as e:
            sc = self.get_screenshot()
            sc = self.debug_minimap(sc)

            write_text_to_image(
                sc,
                f"Error: {e}",
                color="red",
                font_size=20
            ).show()
            raise e
        if stat:
            return int(stat)
        return None
    
    def find_item(
            self,
            item_identifier: str | int,
            tab: ToolplaneTab = ToolplaneTab.INVENTORY,
            min_confidence=0.97,
            screenshot: Image.Image = None,
            crop: Tuple[int,int,int,int] = None # left top right bottom
        ) -> MatchResult:
        self.click_toolplane(tab)
        sc = screenshot or self.get_screenshot()

        if isinstance(item_identifier, str):
            item = self.item_db.get_item_by_name(item_identifier)
        elif isinstance(item_identifier, int):
            item = self.item_db.get_item_by_id(item_identifier)
        
        icon = item.icon

        if crop:
            icon = icon.crop((
                crop[0],
                crop[1],
                icon.width-crop[2],
                icon.height-crop[3]
            ))
            #icon.show()

        

        if not isinstance(item, Item):
            raise ValueError(f'Item : {item_identifier} not found in database.')
        
        item_name = item.name
        if item.noted: item_name += ' (noted)'

        sc = self.sectors.toolplane.crop_in(sc)
        match = self.find_in_window(
            item.icon, sc, min_scale=1,max_scale=1
        )

        self.log.debug(f"Found {item_name} with confidence: {round(match.confidence*100,2)}%")
        
        if match.confidence < min_confidence:
            raise ValueError(f"Item {item_name} not found in window. Confidence: {match.confidence}")
        plane = self.sectors.toolplane
        match = match.transform(plane.start_x,plane.start_y)

        return match
    
    
    def smart_find_item(
        self,
        item_identifier: str | int | None = None,
        item: Item | None = None,
        parent_match: MatchResult | None = None,
        ignore_count: bool = False,
        hover_verify: bool = False,
        hover_verify_retry = 3,
        min_confidence = .95,
        raise_on_missing = False
    ):
        """
        Robust item finding tool
        
        Args:
            item_identifier: Lookup query in item db
            parent_match: filter to search within (optional)
            ignore_count: crop off the top pixels of the item searching for
            hover_verify: verify the item we are looking for by hovering over it
            hover_verify_retry: number of items to try verifying
            min_confidence: min CV confidence threshold
            raise_on_missing: raise if item is missing
        """
        if not item_identifier and not item:
            raise ValueError('item_identifier or item must be defined')
        if not item:
            item = self.item_db.get_item(item_identifier)
        
        if not isinstance(item,Item):
            raise ValueError(f'Item: {item_identifier} is not resolved.')
        sc = self.get_screenshot()
        count_pixels = 13
        
        if parent_match:
            sc = parent_match.crop_in(sc)
            
        ico = item.icon
        if ignore_count:
            ico = ico.crop(
                (0,count_pixels,ico.width,ico.height)
            )
        matches_to_find = hover_verify_retry if hover_verify else 1
        options = tools.find_subimages(
            parent=sc, template=ico,
            min_confidence=min_confidence,
            max_count=matches_to_find
        )
        

        ans: MatchResult | None = None

        for opt in options:
            if hover_verify:
                self.move_to(opt,parent_sectors=[parent_match])
                time.sleep(.25)
                text = self.get_action_hover()
                score = tools.text_similarity(text,item.name)
                if score > .7:
                    ans = opt
                    break
                self.log.debug(f'Missed similarity threshold - {item.name} | {text} || {score}')
                self.move_off_window()
                
            else:
                ans = opt
                break
        
        if not ans: 
            if raise_on_missing:
                raise ValueError(f'Cant find item {item.name}')
            else:
                return None

        if parent_match:
            ans = ans.transform(
                parent_match.start_x,
                parent_match.start_y
            )
        if ignore_count:
            ans.start_x -= count_pixels
        
        return ans
            
        

    def get_item_cnt(
            self,
            item_identifier: str | int,
            tab: ToolplaneTab = ToolplaneTab.INVENTORY,
            min_confidence=0.97
        ):
        """the count of the item in a single slot"""
        self.get_screenshot()
        top_crop = 13
        match = self.find_item(
            item_identifier,
            tab,
            min_confidence,
            crop=(0,top_crop,0,0) # crop top off
        )
        match.start_y = match.start_y - 5
        match.start_x = match.start_x - 3
        match.end_y = match.start_y + 15
        match.end_x = match.start_x + 35

        sc = match.crop_in(self.screenshot)
        num_img = tools.mask_colors(sc, [
            (255, 255, 0), # < 100k
            # TODO: actually handle these
            # (255,255,255), # > 100k
            # (0, 255, 128)  # > 10M
        ], tolerance=5)

        try:
            return ocr.get_number(
                num_img,
                ocr.FontChoice.RUNESCAPE_PLAIN_11,
            )
        except Exception as e:
            self.log.error(f'Failed to get count for item: {item_identifier} - {str(e)}')
            match.debug_draw(self.screenshot).show()
            return 0
         
    
            
    @timeit
    def click_item(
            self,
            item_identifier: str | int,
            tab: ToolplaneTab = ToolplaneTab.INVENTORY,
            click_cnt: int = 1,
            min_confidence=0.97,
            min_click_interval: float = 0.3,
            crop: Tuple[int] = None,
            center: bool = False
    ):
        
        match = self.find_item(
            item_identifier,
            tab,
            min_confidence,
            crop=crop
        )
        
        if center: match = match.get_center()
            
        self.click(
            match, click_cnt=click_cnt, 
            min_click_interval=min_click_interval,
        )

    def get_right_click_menu(self, sc:Image.Image=None) -> MatchResult:
        sc = sc or self.get_screenshot()
        right_click_header = Image.open('data/ui/right-click-header.png')
        right_click_menu_end = Image.open('data/ui/right-click-menu-end.png')
        top_left = self.find_in_window(
            right_click_header,
            sc,
            min_scale=1,
            max_scale=1
        )
        bottom_right = self.find_in_window(
            right_click_menu_end,
            sc,
            min_scale=1,
            max_scale=1
        )
        menu_match = MatchResult(
            start_x=top_left.start_x,
            start_y=top_left.start_y,
            end_x=bottom_right.end_x,
            end_y=bottom_right.end_y,
        )
        return menu_match


    def choose_right_click_opt(
            self,
            option: str
    ):
        sc = self.get_screenshot()
        menu_match = self.get_right_click_menu(sc)

        menu = menu_match.crop_in(sc)
        menu = tools.mask_above_color_value(menu, 150)
        

        ocr_match = ocr.find_string_bounds(
            menu,
            option,
            lang=ocr.FontChoice.RUNESCAPE_BOLD_12.value
        )
        match = MatchResult(
            ocr_match['x1'],
            ocr_match['y1'],
            ocr_match['x2'],
            ocr_match['y2'],
            confidence=ocr_match['confidence']
        )
        match = match.transform(
            menu_match.start_x,
            menu_match.start_y
        )
        
        self.click(match,rand_move_chance=0)
        

    
    def debug_minimap(self,screenshot: Image.Image = None):
        if not screenshot:
            screenshot = self.get_screenshot()
            
        self.minimap.health.debug_draw(self.screenshot, color=(0, 255, 0))
        self.minimap.prayer.debug_draw(self.screenshot, color=(0, 0, 255))
        self.minimap.run.debug_draw(self.screenshot, color=(255, 0, 0))
        self.minimap.spec.debug_draw(self.screenshot, color=(255, 255, 0))
        find_subimage(self.screenshot, Image.open("data/ui/map.webp")).debug_draw(self.screenshot, color=(255, 255, 255))
        self.minimap.get_minimap_match(self.minimap.health,screenshot).debug_draw(self.screenshot,color=(255,255,255))
        self.minimap.get_minimap_match(self.minimap.run,screenshot).debug_draw(self.screenshot,color=(255,255,255))
        # health_val = self.minimap.get_minimap_stat(self.minimap.health, self.screenshot)
        # # print(f"Health: {health_val}")
        # prayer_val = self.minimap.get_minimap_stat(self.minimap.prayer, self.screenshot)
        # # print(f"Prayer: {prayer_val}")
        # run_val = self.minimap.get_minimap_stat(self.minimap.run, self.screenshot)
        # print(f"Run: {run_val}")
        # spec_val = self.minimap.get_minimap_stat(self.minimap.spec, self.screenshot)
        return screenshot
        # print(f"Spec: {spec_val}")
        #self.screenshot.show()

    def debug_toolplane(self):
        self.get_screenshot()
        active_tab = self.toolplane.get_active_tab(self.screenshot)
        print(f"Active Tab: {active_tab}")
        for variable in vars(self.toolplane):
            match = getattr(self.toolplane, variable)
            if match and isinstance(match, MatchResult):
                color = (0, 255, 0) if variable == active_tab else (255, 0, 0)
                match.debug_draw(self.screenshot, color=color)
                print(f"{variable}: {match}")

        #self.screenshot.show()

    def get_hover_image(self) -> Image.Image:
        logo = Image.open('data/ui/rl-window-logo.png')
        match = self.find_in_window(
            logo,min_scale=1,max_scale=1,min_confidence=0.95
        )
        match = match.transform(0,25)
        match.end_x = match.start_x + 350
        return match.crop_in(self.get_screenshot())


    def get_hover_text(self):
        """not gonna lie, this kinda sucks"""
        hover_info = self.get_hover_image()
        ans = ''
        if hover_info:
            ans = ocr.execute(
                hover_info,
                font=ocr.FontChoice.RUNESCAPE_BOLD_12,
                psm=ocr.TessPsm.SINGLE_LINE,
                raise_on_blank=False
            )
        return ans
    
    @property
    def is_mining(self) -> bool:
        try:
            return self.get_skilling_state('mine')
        except:
            return False
    @property
    def is_fishing(self) -> bool:
        try:
            return self.get_skilling_state('fish')
        except:
            return False
    @property
    def is_cooking(self) -> bool:
        try:
            return self.get_skilling_state('cook')
        except Exception as e:
            return False
    @property
    def is_woodcutting(self) -> bool:
        try:
            return self.get_skilling_state('logs')
        except Exception as e:
            return False
    @property
    def makin_cannonballs(self) -> bool:
        try: 
             return self.get_skilling_state('ball')
        except Exception as e:
            self.log.error(f"Error checking cannonball state: {str(e)}")
            try:
                m = self.find_item('Steel bar', min_confidence=0.95)
                if m and m.confidence > 0.95:
                    return True
            except Exception as e:
                self.log.error(f"Error checking for steel bar: {str(e)}")

        return False
    
    def get_skilling_state(self, substring: str) -> bool:
        state_box = Image.open('data/ui/skilling-state.png')
        sc = self.get_screenshot()
        matches = find_subimages(
            sc,state_box,
            min_scale=1, max_scale=1,
            min_confidence=0.98
            )
        skill_match = None
        for match in matches:
            skill_img = tools.mask_colors(
                match.crop_in(sc),
                [[255,255,255], # white
                [255,0,0], # red
                [0,255,0]] # green
            )
            text = ocr.execute(
                skill_img,
                font=ocr.FontChoice.RUNESCAPE_PLAIN_12,
                psm=ocr.TessPsm.SPARSE_TEXT,
                raise_on_blank=False,
            )

            if substring.lower() in text.lower():
                skill_match = match
                
                break
        
        if skill_match is None:
            raise ValueError(f"Could not find skilling state for substring: {substring}")
        
        img = skill_match.crop_in(sc)
        # find red pixel in the image
        red_pixel = np.array(img) == [255, 0, 0]
        green_pixel = np.array(img) == [0, 255, 0]
        
        # if more green than red, return True
        if np.any(red_pixel) or np.any(green_pixel):
            if np.sum(green_pixel) > np.sum(red_pixel):
                return True
            else:
                return False

        raise ValueError(f"Could not determine skilling state for substring: {substring}. No red or green pixels found in {img.size} image.")
        
    @control.guard
    def is_moving(self, sleep_between=.8, retry_cnt=2) -> bool:
        """
        Checks if the player is moving by comparing the 
        player's position at two different times.
        """
        # Use a list to store position results from threads
        positions: List[PlayerPosition] = [None, None]
        
        def get_pos_and_store(index):
            positions[index] = self.get_position(retry_cnt)
        
        # Get first position
        t1 = threading.Thread(target=get_pos_and_store, args=(0,))
        t2 = threading.Thread(target=get_pos_and_store, args=(1,))
        t1.start()
        
        time.sleep(sleep_between)
        
        
        t2.start()
        
        t1.join()
        t2.join()
        
        # Ensure we got valid position data
        if None in positions or not all(hasattr(p, 'tile') for p in positions if p is not None):
            return False
            
        # Compare positions to determine movement
        return positions[0].tile != positions[1].tile
    
    @timeit
    def get_position(self,retry_cnt=0) -> 'PlayerPosition':
        def do_ocr(match: MatchResult, sc: Image.Image) -> str:
            return read_location_numbers(match.crop_in(sc))
        sc = self.get_screenshot()
        position_container = POSITION_STATE
        match = self.find_in_window(
            position_container,sc,
            min_scale=1,max_scale=1
        )

        
        
        if match.confidence < 0.98:
            if retry_cnt > 0:
                time.sleep(1)
                self.log.info(f"Retrying position detection: {retry_cnt} attempts remaining")
                return self.get_position(retry_cnt=retry_cnt-1)
            raise RuntimeError('Missing plugin: "World Location" please install & enable "Grid Location" with "Grid Info Type" == "UniqueID"')
    
        
        sc = match.crop_in(sc)
        sc = tools.mask_colors(sc,[(255,255,255)])
        
        def process_ocr(match: MatchResult):
            return do_ocr(match, sc)

        matches = {
            "tile": MatchResult(40, 6, 128, 21),
            "chunk": MatchResult(75, 22, 127, 37),
            "region": MatchResult(85, 38, 127, 53),
        }

        with ThreadPoolExecutor(max_workers=len(matches)) as executor:
            results = {key: executor.submit(process_ocr, match) for key, match in matches.items()}

        tile_val = results["tile"].result()
        if not tile_val and retry_cnt > 0:
            time.sleep(1)
            self.log.warning(f"Failed to read tile position, retrying: {retry_cnt} attempts left")
            return self.get_position(retry_cnt=retry_cnt-1)
        tile_ans = tuple(int(t.strip()) for t in tile_val.split(',') if t.isdigit())

        chunk_val = results["chunk"].result()
        if not chunk_val and retry_cnt > 0:
            time.sleep(1)
            self.log.warning(f"Failed to read chunk position, retrying: {retry_cnt} attempts left")
            return self.get_position(retry_cnt=retry_cnt-1)
        chunk_ans = int(chunk_val.strip())

        region_val = results["region"].result()
        if not region_val and retry_cnt > 0:
            time.sleep(1)
            self.log.warning(f"Failed to read region position, retrying: {retry_cnt} attempts left")
            return self.get_position(retry_cnt=retry_cnt-1)
        region_ans = int(region_val.strip())

        return PlayerPosition(
            tile=tile_ans, 
            chunk=chunk_ans, 
            region=region_ans
        )
        

    def get_inv_items(self, 
            items: List[str | int],min_confidence=0.97,
            x_sort: bool = None,
            y_sort: bool = None,
            do_sort: bool = True,
            verify_tab: bool = True
        ) -> List[MatchResult]:
        if verify_tab:
            self.click_toolplane(ToolplaneTab.INVENTORY)
        sc = self.get_screenshot()
        tp = self.sectors.toolplane
        sc = tp.crop_in(sc)
        matches: List[tools.MatchResult] = []
        for item in items:
            itm = self.item_db.get_item(item)
            if not itm:
                raise RuntimeError(f"Item '{item}' not found in database.")
                
            item_icon = itm.icon
            if not item_icon:
                self.log.warning(f"Item icon for '{item}' not found.")
                continue
            matches += tools.find_subimages(
                sc, item_icon, min_confidence=min_confidence
            )
        if not matches:
            return []

        if do_sort:
            if x_sort is None: x_sort = random.choice([True, False])
            if y_sort is None: y_sort = random.choice([True, False])
            matches.sort(
                key=lambda x: x.start_x,
                reverse=x_sort
            )
            matches.sort(
                key=lambda x: x.start_y,
                reverse=y_sort
            )
        matches = [m.transform(tp.start_x,tp.start_y) for m in matches]
        return matches

    def follow_tile(
            self,
            tile_color: Tuple[int, int, int] = (255, 0, 50),
            filter_ui:bool = True, # if True, will filter out UI elements
            filter_out: List[MatchResult] = None
    ):
        stop = threading.Event()
        def _loop_find():
            while not stop.is_set():
                sc = self.get_filtered_screenshot() if filter_ui else self.get_screenshot()
                t = None
                if filter_out:
                    for match in filter_out:
                        sc = match.remove_from(sc)
                try:
                    m = tools.find_color_box(
                        sc,
                        tile_color,
                        tol=40,
                    )
                    
                    x,y = m.get_center()
                    x = int(x + self.window.left)
                    y = int(y + self.window.top)
                    if t:
                        t.join()
                    t = threading.Thread(target=move_to,args=(x,y,0,0,0))
                    t.start()
                except Exception as e:
                    self.log.error(f"Error following tile: {str(e)}")
            
        t = threading.Thread(target=_loop_find, daemon=True)
        t.start()
        while self.is_moving():
            continue
        time.sleep(0.2)  # Give it a moment to settle
        stop.set()


    def smart_click_tile(
            self,
            tile_color, # (255,0,50)
            hover_text, # 'furnace'
            retry_hover=3,
            retry_match=3,
            filter_ui: bool = False, # if True, will filter out UI elements
            filter_out: List[MatchResult] = None,
        ):
        for mult in range(retry_match):
            time.sleep(3*mult) # 0 on first try
            sc = self.get_screenshot(filter_ui)
            if filter_out:
                for match in filter_out:
                    sc = match.remove_from(sc)
            if mult + 1 >= retry_match and retry_match > 1:
                self.move_off_window()
            try:
                match = find_color_box(
                    sc,tile_color,
                    tol=40+(10*mult)
                )
                self.smart_click_match(
                    match,
                    hover_text,
                    retry_hover,
                    center_point=True if mult == 0 else False
                )
                return
            except Exception as e:
                if (mult+1) == retry_match:
                    raise e
            
    def smart_click_match(
            self,
            match: MatchResult,
            hover_texts:str | List[str], # 'furnace' | ['furnace','smelt']
            retry_hover=3,
            click_cnt=1,
            click_type=ClickType.LEFT,
            center_point=False,
            center_point_variance=2, #pixels
            parent_sectors: List[MatchResult] = []
        ):
        for sector in parent_sectors:
                match = match.transform(sector.start_x,sector.start_y)

        for _ in range(retry_hover):
            if center_point:
                point = match.get_center()
                point = (
                    point[0] + random.randint(-center_point_variance, center_point_variance),
                    point[1] + random.randint(-center_point_variance, center_point_variance)
                )
            else:  
                point = match.get_point_within()
            self.move_to(point,rand_move_chance=0)
            time.sleep(random.uniform(0.1, 0.2))

            answers = self.get_hover_texts()
            self.log.debug(f"Hover texts detected: {answers}")
            if isinstance(hover_texts, str):
                hover_texts = [hover_texts]
            for hover_text in hover_texts:
                for ans in answers:
                    if hover_text.lower() in ans.lower():
                        click(-1,-1,click_type=click_type,click_cnt=click_cnt)
                        return
        raise RuntimeError(f'[SmartClick] cant find match {hover_texts}. Hover text: "{ans}"')

    @control.guard
    def get_hover_texts(self):
        if sys.platform.startswith('linux'):
            # TODO linux bullshit
            return [self.get_action_hover() or '']
        

        
        def safe(fn, label):
            try:
                return fn() or ''
            except Exception as e:
                self.log.error("[%s] %s", label, e, exc_info=True)
                return ''

        ex = ThreadPoolExecutor(max_workers=2, thread_name_prefix="hover")
        futures = [
            ex.submit(safe, self.get_hover_text,     "hover_text"),
            ex.submit(safe, self.get_action_hover,   "action_hover"),
        ]
        try:
            done, not_done = wait(futures, timeout=5, return_when=FIRST_EXCEPTION)

            # collect whatever finished
            results = [f.result() for f in done]

            # anything still running after 5 s is probably wedged
            for f in not_done:
                f.cancel()

            # pad so we always return two strings
            while len(results) < 2:
                results.append('')
            return results

        except TimeoutError:
            self.log.warning("Timed-out waiting for hover text")
            return ['', '']

        finally:
            # don’t block—just shoot lingering threads
            ex.shutdown(wait=False, cancel_futures=True)

    def compare_hover_match(self, target: str) -> float:
        """
        Compares the hover text with a target string.

        Args:
            target (str): The target string to compare against.

        Returns:
            bool: True if the hover text matches the target, False otherwise.
        """
        hover_text = self.get_hover_texts()
        max_match = 0
        for text in hover_text:
            match = tools.text_similarity(text, target)
            if match > max_match:
                max_match = match
        return max_match
    
    @control.guard
    def on_resize(self):
        """
        Handles the window resize event by recalculating UI sectors and components.
        """
        self.log.debug("Window resize detected - recalculating UI elements")
        sc = self.get_screenshot()

        match_jobs = [
            (self.minimap.find_matches, (sc,), {}),
            (self.toolplane.find_matches, (sc,), {}),
            (self.sectors.find_matches, (sc, self.ui_type), {}),
            # (other_component.find_matches, (sc, ...), {}),
        ]

        with ThreadPoolExecutor(max_workers=min(MAXTHREAD, len(match_jobs))) as pool:
            futures = [pool.submit(fn, *args, **kwargs) for fn, args, kwargs in match_jobs]
            for f in futures:
                f.result()

    def get_ui_type(self) -> 'UIType':
        modern_toolplane = Image.open('data/ui/toolplane-modern.png')
        classic_coolplane = Image.open('data/ui/toolplane-classic.png')

        modern = self.find_in_window(modern_toolplane,self.screenshot)
        classic = self.find_in_window(classic_coolplane,self.screenshot)

        return UIType.CLASSIC if classic.confidence > modern.confidence else UIType.MODERN
    
    def get_filtered_screenshot(
            self,
            toolplane: bool = True,
            chat: bool = True,
            minimap: bool = True,
            sidebar: bool = True
        ) -> Image.Image:
        sc = self.get_screenshot()
        if toolplane:
            sc = self.sectors.toolplane.remove_from(sc)
            for variable in vars(self.toolplane):
                match = getattr(self.toolplane, variable)
                if isinstance(match, MatchResult):
                    sc = match.remove_from(sc)
        if chat:
            m = self.sectors.chat.copy()
            m.end_y = m.end_y + 25
            sc = m.remove_from(sc)
        if minimap:
            m = self.minimap.map.scale_px(30)
            m = m.transform(-20,20)
            sc = m.remove_from(sc)
        if sidebar:
            end_tp = self.sectors.toolplane.end_x
            sc = sc.crop((0,0,end_tp+5,sc.height))
        return sc

    def get_screenshot(self, filtered=False) -> Image.Image:
        if filtered:
            return self.get_filtered_screenshot()
        self._last_screenshot = super().get_screenshot(True)
        return self._last_screenshot
    
    def find_chat_text(self,text):
        chat = self.sectors.chat

        sc = self.get_screenshot()
        sc = chat.crop_in(sc)

        
        ocr_match = ocr.find_string_bounds(
            sc,text,
            lang=ocr.FontChoice.RUNESCAPE_PLAIN_12.value
        )
        match = MatchResult(
            ocr_match['x1'],
            ocr_match['y1'],
            ocr_match['x2'],
            ocr_match['y2'],
            confidence=ocr_match['confidence']
        )
        return match.transform(chat.start_x,chat.start_y)
    
    def get_chat_text(self) -> str:
        chat = self.sectors.chat

        sc = self.get_screenshot()
        sc = chat.crop_in(sc)

        return ocr.execute(
            sc,
            font=ocr.FontChoice.RUNESCAPE_PLAIN_12,
            psm=ocr.TessPsm.SPARSE_TEXT,
            raise_on_blank=False,
            preprocess=True
        )
        
    @property
    def hover_text(self) -> str:
        """Get the current hover text from the game interface.
        tries action hover, falls back to normal hover text if needed.

        Returns:
            str: The hover text currently displayed.
        """
        ans = None
        try:
            ans = self.get_action_hover()
        except:
            pass
        
        if not ans:
            ans = self.get_hover_text()
        return ans or ''
    
    @control.guard
    def get_action_hover(self) -> str:
        """
        Gets the hover text from the action bar below the cursor.
        """
        try:
            h_start = ACTION_HOVER.crop((
                0, 0, 
                10, ACTION_HOVER.height
            ))
            h_end = ACTION_HOVER.crop((
                ACTION_HOVER.width - 10, 0, 
                ACTION_HOVER.width, ACTION_HOVER.height
            ))

            c_x, c_y = self.mouse_position()
            sc = self.get_screenshot()

            hover_box = MatchResult(
                c_x - 45, c_y - 20, 
                c_x + 20, c_y + 45
            )

            start = self.find_in_window(
                h_start,
                sub_match=hover_box,
                min_scale=1, max_scale=1,
                min_confidence=0.95
            )
            

            end_x = min(self.window_match.end_x , start.start_x + 350)
            end_y = min(self.window_match.end_y, start.start_y + 25)

            hover_box = MatchResult(
                start.start_x, start.start_y,
                end_x, end_y
            )
            
            end = self.find_in_window(
                h_end,
                sub_match=hover_box,
                min_scale=1, max_scale=1,
                min_confidence=0.95
            )

            action = MatchResult(
                start.start_x, start.start_y,
                end.end_x, end.end_y
            )
            action_img = action.crop_in(self.get_screenshot())
            action_txt = tools.mask_above_color_value(
                action_img,
                threshold=150
            )
            ans = ocr.execute(
                action_txt,
                font=ocr.FontChoice.RUNESCAPE_PLAIN_11,
                psm=ocr.TessPsm.SINGLE_LINE,
                raise_on_blank=False,
                preprocess=False
            )
            return ans
        except Exception as e:
            return None




        
        


        
    def click_chat_text(self,text):
        match = self.find_chat_text(text)
        self.click(match)

    def is_text_in_chat(self, text: str, confidence=.7) -> bool:
        """
        Checks if the given text is present in the RuneLite chat.
        tip: use a full line of text for best results.
        """
        text = text.lower()
        chat_text = self.get_chat_text().lower()
        for line in chat_text.splitlines():
            similar = tools.text_similarity(line, text)
            if similar >= confidence:
                self.log.debug(f'Text match in chat with similarity: {similar:.2f}')
                return True
        return False

    @property
    def quick_prayer_active(self) -> bool:
        """Checks if the quick prayer is active in the RuneLite window."""
        qp_disabled = Image.open("data/ui/quick-prayer-disabled.png")
        qp_enabled = Image.open("data/ui/quick-prayer-enabled.png")

        self.get_screenshot()
        
        disabled_match = self.find_in_window(qp_disabled, self.screenshot)
        enabled_match = self.find_in_window(qp_enabled, self.screenshot)
        
        if enabled_match.confidence > disabled_match.confidence:
            return True
        return False
    
@dataclass
class PlayerPosition:
    tile: Tuple[int,int,int]
    chunk: int
    region: int

    
class UIArea(Enum):
    TOOLPLANE = 'toolplane'
    CHAT = 'chat'
    MINIMAP = 'minimap'

class UIType(Enum):
    MODERN = 'modern'
    CLASSIC = 'classic'
    FIXED = 'fixed'

class UISectors:
    """Represents UI sectors such as the toolplane and chat areas."""
    toolplane: MatchResult = None
    chat: MatchResult = None

    def find_matches(self, sc: Image.Image, uitype: UIType):
        """
        Finds and sets the matches for UI sectors based on the UI type.

        Args:
            sc (Image.Image): The screenshot of the RuneLite window.
            uitype (UIType): The type of UI (modern, classic, etc.).
        """
        # Determine the toolplane template based on the UI type
        if uitype == UIType.MODERN:
            toolplane = Image.open('data/ui/toolplane-modern.png')
        else:
            toolplane = Image.open('data/ui/toolplane-classic.png')
        
        # Find the toolplane match
        self.toolplane = find_subimage(
            sc, toolplane,
            min_scale=1, max_scale=1
        )

        # Find the chat area matches
        chat_bottom_right = Image.open('data/ui/chat-bottom-right.png')
        chat_top_left = Image.open('data/ui/chat-top-left.png')

        match_br = find_subimage(
            sc, chat_bottom_right,
            min_scale=1,max_scale=1
        )
        match_tl = find_subimage(
            sc, chat_top_left,
            min_scale=1,max_scale=1
        )
        self.chat = MatchResult(
            match_tl.start_x,
            match_tl.start_y,
            match_br.end_x,
            match_br.end_y,
            confidence=(match_br.confidence + match_tl.confidence)/2
        )
    

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

    def __init__(self):
        self._TEMPLATE_PATHS = {
            "combat":    Path("data/ui/combat.webp"),
            "skills":    Path("data/ui/stats.webp"),
            "inventory": Path("data/ui/inventory.webp"),
            "equipment": Path("data/ui/equipment.webp"),
            "prayer":    Path("data/ui/prayer.webp"),
            "spells":    Path("data/ui/spellbook.webp"),
            "account":   Path("data/ui/account.webp"),
            "logout":    Path("data/ui/logout.webp"),
            "settings":  Path("data/ui/settings.webp"),
            "emotes":    Path("data/ui/emotes.webp"),
            "music":     Path("data/ui/music.webp"),
            # progress / groups / friends omitted for now
        }
        self._TEMPLATE_CACHE = {k: Image.open(p) for k, p in self._TEMPLATE_PATHS.items()}


    @timeit
    def find_matches(self, screenshot: Image.Image, max_workers: int | None = 10):
        """
        Locate all tool-plane icons in *screenshot* concurrently.
        Results are assigned to the matching attributes (self.combat, …).
        """
        def _worker(name_img):
            name, tpl_img = name_img
            return name, find_subimage(
                screenshot, tpl_img, min_scale=0.9, max_scale=1.1
            )

        # ThreadPoolExecutor is ideal here because find_subimage is
        # largely I/O / C-extension work, not pure Python CPU.
        template_items = self._template_items()
        with ThreadPoolExecutor(max_workers=min(MAXTHREAD, len(template_items))) as pool:
            futures = (pool.submit(_worker, item) for item in template_items)
            for fut in as_completed(futures):
                name, match = fut.result()
                setattr(self, name, match)

    # ────────────────────────────────────────────────────────────────
    # helper: iterator of (name, template-image) pairs
    # ────────────────────────────────────────────────────────────────
    def _template_items(self):
        return self._TEMPLATES.items() if "_TEMPLATES" in globals() else self._TEMPLATE_CACHE.items()

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

    @timeit
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
    map: MatchResult = None
    health: MatchResult = None
    prayer: MatchResult = None
    run: MatchResult = None
    spec: MatchResult = None
    globe: MatchResult = None
    MATCH_SCALE = -4 #px

    def get_minimap_value_match(self,match: MatchResult) -> MatchResult:
        """Returns the match object for the given match."""
        match = match.transform(-22+self.MATCH_SCALE, 13+self.MATCH_SCALE)
        match.end_x = match.start_x + 23
        match.end_y = match.start_y + 12 
        match.shape = MatchShape.RECT
        
        return match

    def get_minimap_stat(self,match: MatchResult, screenshot: Image.Image) -> int:
        """Returns the health value from the screenshot."""
        match = self.get_minimap_value_match(match)
        return match.extract_number(screenshot, ocr.FontChoice.RUNESCAPE_PLAIN_11)
    @timeit
    def find_matches(self, screenshot: Image.Image):
        """Finds and sets the matches for health, prayer, run, and spec."""

        map = find_subimage(screenshot, Image.open("data/ui/map.webp"))
        map.shape = MatchShape.ELIPSE
        self.map = map.transform(-63, -60).scale_px(60)
        self.health = map.transform(-152, -76)
        self.prayer = map.transform(-152, -42)
        self.run = map.transform(-142, -10)
        self.spec = map.transform(-120, 15)

        # make match mildly smaller
        for variable in vars(self):
            match = getattr(self, variable)
            if isinstance(match, MatchResult):
                m: MatchResult = match.scale_px(self.MATCH_SCALE)
                match.start_x = m.start_x
                match.start_y = m.start_y
                match.end_x = m.end_x
                m.end_y = m.end_y
        self.globe = map # blue globe thing
                
                

    

    

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
