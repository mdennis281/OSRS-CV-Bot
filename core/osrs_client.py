import pygetwindow as gw
import pyautogui
import mss
import time
from PIL import Image
import io
from core.tools import find_subimage, MatchResult, MatchShape, timeit, write_text_to_image, find_color_box,seconds_to_hms, find_subimages
from core.input.mouse_control import click_in_match, move_to, ClickType, click
from core import ocr
from typing import Tuple, List
import threading
import cv2
import numpy as np
from dataclasses import field
from core.item_db import ItemLookup, Item
from enum import Enum
import random
from pathlib import Path
import keyboard
from concurrent.futures import ThreadPoolExecutor, as_completed

import os

MAXTHREAD = os.cpu_count()


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
        self._last_screenshot: Image.Image = None
        self.update_window()

    def update_window(self) -> gw.Win32Window:
        """Finds and updates the RuneLite window reference."""
        windows = gw.getWindowsWithTitle(self.window_title)
        self.window = windows[0] if windows else None

    def start_resize_watch_polling(self, on_resize=None, interval=0.2):
        def _loop():
            while not stop_evt.is_set():
                if self.is_open:
                    rect = (self.window.width, self.window.height)
                    if rect != last[0]:
                        last[0] = rect
                        if on_resize: on_resize()
                        else: self.on_resize()
                stop_evt.wait(interval)
        stop_evt, last = threading.Event(), [(self.window.width, self.window.height)]
        threading.Thread(target=_loop, daemon=True).start()
        return stop_evt  # caller .set() to stop

    @property
    def screenshot(self) -> Image.Image:
        if self._last_screenshot:
            return self._last_screenshot
        return self.get_screenshot()

    @property
    def is_open(self):
        """Returns True if the RuneLite window is open, False otherwise."""
        self.update_window()
        return self.window is not None

    @property
    def dimensions(self):
        """Returns the (width, height) of the RuneLite window."""
        if not self.is_open:
            self.bring_to_focus()
        return (self.window.width, self.window.height)

    @property
    def coordinates(self):
        """Returns the (x, y) position of the RuneLite window."""
        if not self.is_open:
            self.bring_to_focus()
        
        return (self.window.left, self.window.top)
    @property
    def window_match(self):
        x1,y1 = self.coordinates
        w, h  = self.dimensions
        x2, y2 = ( x1+w, y1+h )
        return MatchResult(
            x1,y1,x2,y2,
            1,1,
            MatchShape.RECT
        )


    def bring_to_focus(self):
        """Brings the RuneLite window to the foreground."""
        if self.is_open and not self.window.isActive:
            try:
                # pressing alt makes activate() more reliable
                keyboard.press('alt')
                self.window.activate()
            except:
                self.window.minimize()
                self.window.restore()
                time.sleep(.3)
            finally:
                keyboard.release('alt')
        

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
            raise RuntimeError(f'Window {self.window_title} is not open.')
        
        with mss.mss() as sct:
            bbox = (self.window.left, self.window.top, self.window.left + self.window.width, self.window.top + self.window.height)
            sct_img = sct.grab(bbox)
            img = Image.frombytes('RGB', sct_img.size, sct_img.rgb)
        
        self._last_screenshot = img
        return self._last_screenshot

    def save_screenshot(self, filename="runelite_screenshot.png"):
        """Saves a screenshot of the RuneLite window to a file."""
        screenshot = self.get_screenshot()
        if screenshot:
            screenshot.save(filename)
            return filename
        return None
    
    @timeit
    def find_in_window(
            self, img: Image.Image, screenshot: Image.Image=None,
            min_scale: float = 0.9, max_scale: float = 1.1,
            min_confidence: float = 0.7
        ) -> MatchResult:
        """Finds a subimage within the RuneLite window."""
        screenshot = screenshot or self.get_screenshot()

        return find_subimage(
            screenshot, img, 
            min_scale=min_scale, max_scale=max_scale,
            min_confidence=min_confidence
        )
    
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
        

    

    def move_to(self,match: MatchResult | Tuple[int], 
                rand_move_chance:float=0.4,
                translated=False):
        if isinstance(match, MatchResult):
            x,y = match.get_point_within()
        else:
            x,y = match
            x,y = match
        # todo: sector support???
        if not translated:
            x += self.window.left
            y += self.window.top

        # move the mouse around a bit
        if random.random() < rand_move_chance:
            self.move_to(self.window_match,translated=True)
            
        move_to(x,y)


    def click(
            self, match: MatchResult | Tuple[int], 
            click_cnt:int=1, min_click_interval: float = 0.3, 
            click_type=ClickType.LEFT, parent_sectors: List[MatchResult]=[],
            rand_move_chance:float=.4, after_click_settle_chance=.4):
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


        self.move_to((x,y),rand_move_chance, translated=True) 
        click(
            -1,-1,
            click_type=click_type,
            click_cnt=click_cnt, 
            min_click_interval=min_click_interval,
        )
        if random.random() < after_click_settle_chance:
            time.sleep(random.uniform(.2,.6))
            self.move_to(self.window_match)
            


        


class RuneLiteClient(GenericWindow):
    def __init__(self,username=''):
        print('[RLClient init] Instantiating...')
        start_time = time.time()
        super().__init__(f'RuneLite - {username}')
        self.minimap = MinimapContext()
        self.toolplane = ToolplaneContext()
        self.item_db = ItemLookup()
        self.sectors: UISectors = UISectors()

        self.ui_type: UIType = self.get_ui_type()
        print(f'[RLClient init] UI Type: {self.ui_type.value}')
        print(f'[RLClient init] finding sectors')
        
        self.on_resize()
        self.start_resize_watch_polling()
        elapsed = seconds_to_hms(time.time() - start_time)
        print(f'[RLClient init] Instantiated in {elapsed}')
        

    
    @timeit
    def click_minimap(self, element: MinimapElement, click_cnt:int=1):
        match: MatchResult = getattr(self.minimap, element.value)
        self.click(match, click_cnt=click_cnt)

    
    @timeit    
    def click_toolplane(self, tab: ToolplaneTab,reload_on_tab_change:bool=True):
        match = getattr(self.toolplane, tab.value)

        if self.toolplane.get_active_tab(self.screenshot) != tab.value:
            self.click(match)
            if reload_on_tab_change: 
                # necessary for getting active tab
                self.get_screenshot()

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
            crop: Tuple[int,int,int,int] = None # left top right bottom
        ) -> MatchResult:
        self.get_screenshot()
        self.click_toolplane(tab)

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

        sc = self.sectors.toolplane.crop_in(self.screenshot)
        match = self.find_in_window(
            item.icon, sc, min_scale=1,max_scale=1
        )

        print(f"{item_name} | Confidence: {round(match.confidence*100,2)}%")
        
        if match.confidence < min_confidence:
            raise ValueError(f"Item {item_name} not found in window. Confidence: {match.confidence}")
        plane = self.sectors.toolplane
        match = match.transform(plane.start_x,plane.start_y)

        return match

    def get_item_cnt(
            self,
            item_identifier: str | int,
            tab: ToolplaneTab = ToolplaneTab.INVENTORY,
            min_confidence=0.97
        ):
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
        match.end_x = match.start_x + 30

        try:
            return match.extract_number(
                self.screenshot,
                ocr.FontChoice.RUNESCAPE_SMALL
            )
            
        except Exception as e: 
            match.debug_draw(self.screenshot).show()
            print('failed on item:',item_identifier)
            return 0
            
        
         

            
    @timeit
    def click_item(
            self,
            item_identifier: str | int,
            tab: ToolplaneTab = ToolplaneTab.INVENTORY,
            click_cnt: int = 1,
            min_confidence=0.97,
            min_click_interval: float = 0.3,
            crop: Tuple[int] = None
    ):
        
        match = self.find_item(
            item_identifier,
            tab,
            min_confidence,
            crop
        )
        
            
        self.click(
            match, click_cnt=click_cnt, 
            min_click_interval=min_click_interval,
        )



    def choose_right_click_opt(
            self,
            option: str
    ):
        sc = self.get_screenshot()
        right_click_header = Image.open('data/ui/right-click-header.png')
        right_click_menu_end = Image.open('data/ui/right-click-menu-end.png')

        top_left = self.find_in_window(
            right_click_header,
            sc,
            min_scale=.99,
            max_scale=1.01
        )
        bottom_right = self.find_in_window(
            right_click_menu_end,
            sc,
            min_scale=.99,
            max_scale=1.01
        )
        menu_match = MatchResult(
            start_x=top_left.start_x,
            start_y=top_left.start_y,
            end_x=bottom_right.end_x,
            end_y=bottom_right.end_y,
        )
        
        menu = menu_match.crop_in(sc)

        ocr_match = ocr.find_string_bounds(
            menu,
            option,
            lang=ocr.FontChoice.RUNESCAPE_BOLD.value
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
        self.click(match)

    
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

    def get_hover_text(self):
        """not gonna lie, this kinda sucks"""
        logo = Image.open('data/ui/rl-window-logo.png')
        match = self.find_in_window(
            logo,min_scale=1,max_scale=1
        )
        match = match.transform(0,25)
        match.end_x = match.start_x + 350
        hover_info = match.crop_in(self.get_screenshot())
        ans = ''
        if hover_info:
            ans = ocr.execute(
                hover_info,
                font=ocr.FontChoice.RUNESCAPE_BOLD,
                psm=ocr.TessPsm.SINGLE_LINE,
                raise_on_blank=False
            )
        return ans
    
    def get_skilling_state(self, substring: str) -> bool:
        state_box = Image.open('data/ui/skilling-state.png')
        sc = self.get_screenshot()
        matches = find_subimages(
            sc,state_box,
            min_scale=1, max_scale=1,
            min_confidence=0.9
            )
        skill_match = None
        for match in matches:
            text = ocr.execute(
                match.crop_in(sc),
                font=ocr.FontChoice.RUNESCAPE,
                psm=ocr.TessPsm.SPARSE_TEXT
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
        
    
    def smart_click_tile(
            self,
            tile_color, # (255,0,50)
            hover_text, # 'furnace'
            retry_hover=3,
            retry_match=2
        ):
        for mult in range(retry_match):
            sc = self.get_screenshot()
            match = find_color_box(
                sc,tile_color,
                tol=40+(10*mult)
            )
            try:
                self.smart_click_match(
                    match,
                    hover_text,
                    retry_hover
                )
                return
            except Exception as e:
                if (mult+1) == retry_match:
                    raise e
            
    def smart_click_match(
            self,
            match: MatchResult,
            hover_text:str, # 'furnace'
            retry_hover=3,
            click_cnt=1,
            click_type=ClickType.LEFT
        ):
        for _ in range(retry_hover):
            point = match.get_point_within()
            self.move_to(point,rand_move_chance=0)

            ans = self.get_hover_text()
            
            if hover_text.lower() in ans.lower():
                self.click(
                    point,
                    click_type=click_type,
                    click_cnt=click_cnt,
                    rand_move_chance=0
                )
                return
        raise RuntimeError(f'[SmartClick] cant find match {hover_text}')



    
    def on_resize(self):
        print("resized!")
        sc = self.get_screenshot()

        match_jobs = [
            (self.minimap.find_matches, (sc,),             {}),
            (self.toolplane.find_matches, (sc,),           {}),               
            (self.sectors.find_matches,  (sc, self.ui_type), {}),             
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

    def get_screenshot(self, maximize=True) -> Image.Image:
        self._last_screenshot = super().get_screenshot(maximize)
        return self._last_screenshot
    
    def find_chat_text(self,text):
        chat = self.sectors.chat

        sc = self.get_screenshot()
        sc = chat.crop_in(sc)

        
        ocr_match = ocr.find_string_bounds(
            sc,text,
            lang=ocr.FontChoice.RUNESCAPE.value
        )
        match = MatchResult(
            ocr_match['x1'],
            ocr_match['y1'],
            ocr_match['x2'],
            ocr_match['y2'],
            confidence=ocr_match['confidence']
        )
        return match.transform(chat.start_x,chat.start_y)
        
    def click_chat_text(self,text):
        match = self.find_chat_text(text)
        self.click(match)


        
        

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
    
class UIArea(Enum):
    TOOLPLANE = 'toolplane'
    CHAT = 'chat'
    MINIMAP = 'minimap'

class UIType(Enum):
    MODERN = 'modern'
    CLASSIC = 'classic'
    FIXED = 'fixed'

class UISectors:
    toolplane: MatchResult = None
    chat: MatchResult = None

    def find_matches(self, sc: Image.Image, uitype: UIType):
        # toolplane
        if uitype == UIType.MODERN:
            toolplane = Image.open('data/ui/toolplane-modern.png')
        else:
            toolplane = Image.open('data/ui/toolplane-classic.png')
        
        self.toolplane = find_subimage(
            sc, toolplane,
            min_scale=1,max_scale=1
        )

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
    health: MatchResult = None
    prayer: MatchResult = None
    run: MatchResult = None
    spec: MatchResult = None
    MATCH_SCALE = -4 #px

    def get_minimap_match(self,match: MatchResult, screenshot: Image.Image) -> MatchResult:
        """Returns the match object for the given match."""
        match = match.transform(-22+self.MATCH_SCALE, 13+self.MATCH_SCALE)
        match.end_x = match.start_x + 23
        match.end_y = match.start_y + 12 
        match.shape = MatchShape.RECT
        
        return match

    def get_minimap_stat(self,match: MatchResult, screenshot: Image.Image) -> int:
        """Returns the health value from the screenshot."""
        match = self.get_minimap_match(match, screenshot)
        return match.extract_number(screenshot, ocr.FontChoice.RUNESCAPE_SMALL)
    @timeit
    def find_matches(self, screenshot: Image.Image):
        """Finds and sets the matches for health, prayer, run, and spec."""

        map = find_subimage(screenshot, Image.open("data/ui/map.webp"))
        map.shape = MatchShape.ELIPSE
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
