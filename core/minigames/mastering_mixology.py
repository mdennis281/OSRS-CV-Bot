from PIL import Image
from core.bot import Bot
from bots.core.cfg_types import RGBParam
from core.logger import get_logger
from pathlib import Path
from enum import Enum
from core import tools
from typing import List, Tuple
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from core.region_match import MatchResult, MatchShape
import cv2
import numpy as np
import pyautogui

MOX = (3, 169, 244)
AGA = (0, 230, 118)
LYE = (233, 30, 99)

IMG_PATH = "data/ui/mastering_mixology"
HEADER = Image.open(f"{IMG_PATH}/orders_header.png")
AGITATOR = Image.open(f"{IMG_PATH}/actions/agitator_raw.png")
ALEMBIC = Image.open(f"{IMG_PATH}/actions/alembic_raw.png")
RETORT = Image.open(f"{IMG_PATH}/actions/retort_raw.png")
ORDER_DONE = Image.open(f"{IMG_PATH}/order_done.png")

class Action(Enum):
    AGITATOR = "agitator"
    ALEMBIC = "alembic"
    RETORT = "retort"

    @staticmethod
    def get_image(action: 'Action'):
        """
        Get the image associated with the action.
        """
        if action == Action.AGITATOR:
            return AGITATOR
        elif action == Action.ALEMBIC:
            return ALEMBIC
        elif action == Action.RETORT:
            return RETORT
        else:
            raise ValueError(f"Unknown action: {action}")
        
    @staticmethod
    def get_action_text(action: 'Action') -> List[str]:
        """
        valid hover text for the action
        """
        if action == Action.AGITATOR:
            return ['homo', 'genize', 'agita']
        if action == Action.ALEMBIC:
            return ['crys','talise','alem']
        if action == Action.RETORT:
            return ['conc','entrate','retort']
        

class Order:
    def __init__(self, ingredients: str, action: Action, match: tools.MatchResult):
        self.ingredients = ingredients
        self.action = action
        self.match = match

    def is_done(self, sc: Image.Image) -> bool:
        # make a copy
        match = self.match.copy()
        # only need second half
        match.start_x = match.start_x + (match.width/2)
        sc = self.match.crop_in(sc)
        m = tools.find_subimage(sc,ORDER_DONE)
        if m.confidence > .90:
            return True
        return False

    def __repr__(self):
        return f"Order(ingredients={self.ingredients}, action={self.action})"

class MasteringMixology():
    def __init__(
            self, 
            bot: Bot,
            mixer_tile = RGBParam(255, 110, 50),
            station_tile: RGBParam = RGBParam(100, 50, 200),
            quick_action_tile: RGBParam = RGBParam(255, 0, 255),
            digweed_tile: RGBParam = RGBParam(0, 255, 0),
            ingredient_exclude: List[str] = [],
        ):
        self.bot = bot
        self.potions: dict = self.get_potions()
        self.mixer_tile = mixer_tile.value
        self.station_tile = station_tile.value
        self.quick_action_tile = quick_action_tile.value
        self.digweed_tile = digweed_tile.value
        self.ingredient_exclude = ingredient_exclude
        self.order_ui = self.get_order_ui()
        self.log = get_logger('MixologyHelper')
        
    
    
    def get_potions(self):
        pot_path = Path(f"{IMG_PATH}/pots")
        potions = {}
        for pot_file in pot_path.glob("*.png"):
            pot_name = pot_file.stem
            potion_image = Image.open(pot_file)
            potions[pot_name] = potion_image
        return potions
    
    def fill_potion(self, potion_name: str, _retry: int = 4):
        self.find_digweed()
        potion_name = potion_name.upper()
        c_key = {'M': MOX, 'A': AGA, 'L': LYE}
        n_key = {'M': 'mox', 'A': 'aga', 'L': 'lye'}
        try:
            for i in range(3):
                ingredient = potion_name[i]
                self.bot.client.smart_click_tile(
                    c_key[ingredient],
                    [n_key[ingredient]],
                    filter_out=[self.order_ui]
                )

                if i < 2:
                    self.bot.client.follow_tile(
                        c_key[potion_name[i + 1]],
                        filter_out=[self.order_ui],
                        filter_ui=True
                    )
                self.find_digweed()
                time.sleep(random.uniform(0.1, 0.3))  # delay so camera can catch up

        except Exception as e:
            if _retry > 0:
                self.log.warning(f"Error filling potion {potion_name}: {e}. Retrying...")
                return self.fill_potion(potion_name, _retry - 1)
            else:
                self.log.error(f"Exhausted retries filling potion {potion_name}.")
                raise e
            
        # now we have all ingredients, click the mixer tile
        self.bot.client.smart_click_tile(
            self.mixer_tile,
            ['take', '-from', 'mix']
        )
        # validation
        while self.bot.client.is_moving():
            continue
        empty = 'the mixing vessel is currently empty'
        if self.bot.client.is_text_in_chat(empty):
            if _retry > 0:
                self.log.error(f'Failed to fill potion {potion_name}. Retrying...')
                return self.fill_potion(potion_name, _retry - 1)
            raise Exception(f"Exhausted retries filling potion {potion_name}.")
        
        missing_ingredients = 'are missing the following'
        if self.bot.client.is_text_in_chat(missing_ingredients, .5):
            raise MissingIngredientError()
        self.find_digweed()
    
    def find_digweed(self):
        digweed = None
        try:
            sc = self.bot.client.get_filtered_screenshot()
            digweed = tools.find_color_box(sc, self.digweed_tile, tol=30)
        except:
            pass
        if digweed and digweed.size_px > 30:
            for _ in range(3):
                try:
                    self.bot.client.smart_click_match(
                        digweed, 
                        ['dig', 'weed', 'mature'],
                        retry_hover=5
                    )
                    while self.bot.client.is_moving():
                        continue
                    return
                except:
                    pass
                digweed = tools.find_color_box(sc, self.digweed_tile, tol=30)


    def follow_station(self):
        self.bot.client.follow_tile(
            self.station_tile
        )

        
    def get_order_ui(self) -> tools.MatchResult:
        """
        Get the UI element for the orders header.
        """
        m = self.bot.client.find_in_window(HEADER)
        m.width = 225
        m.end_y = m.start_y + 200
        return m
    
    def get_orders(self):
        
        m = self.bot.client.find_in_window(HEADER)
        sc = self.bot.client.get_screenshot()
        
        matches: List[tools.MatchResult] = [
            m.transform(0,25),
            m.transform(0, 50),
            m.transform(0, 75)
        ]
        orders: List[Order] = []
        excluded: List[Order] = []
        for o in matches:
            o.width = 200
            o.height = 25
            o.end_x = o.end_x + 25 # it's off center
            order = Order(
                ingredients=self._get_order_ingredients(o.copy()),
                action=self._get_order_action(o.copy()),
                match=o
            )
            if not order.is_done(sc):
                if order.ingredients not in self.ingredient_exclude:
                    orders.append(
                        order
                    )
                else:
                    self.log.info(f"Excluding order with ingredients: {order.ingredients}")
                    excluded.append(order)
        if len(orders) == 0:
            self.log.info("No valid orders found, doing one excluded")
            orders.append(excluded[0])
        return orders

    def _get_order_action(self, order: tools.MatchResult) -> Action:
        """
        Determine the action required for the given order based on the image match.
        """
        sc = self.bot.client.get_screenshot()
        order.end_x = order.start_x + 25 # 
        sc = order.crop_in(sc)
        

        best: Tuple[Action, float, tools.MatchResult] = (None, 0.0)
        for action in Action:
            action_image = Action.get_image(action)

            match = tools.find_subimage(sc, action_image)
            # print(f"Checking action: {action} with match: {match.confidence}")
            if match and match.confidence > best[1]:
                
                best = (action, match.confidence, match)

        # print(f"Best action match: {best[0]} with confidence {best[1]}")
        # best[2].debug_draw(sc, color=(0, 255, 0)).show()
        # Action.get_image(best[0]).show()
        # input("Press Enter to continue...")
        return best[0]
    
    def _get_order_ingredients(self, order: tools.MatchResult) -> str:
        """
        Extract the ingredients from the order image.
        """
        sc = self.bot.client.get_screenshot()
        sc = order.crop_in(sc)

        best: Tuple[str, float] = (None, 0.0)
        for potion_name, potion_image in self.potions.items():
            match = tools.find_subimage(sc, potion_image)
            if match and match.confidence > best[1]:
                best = (potion_name, match.confidence)

        return best[0]
    

    def do_action_station(self, order: Order, _retry: int = 1):
        # Click the station and wait for movement to complete
        self.find_digweed()
        self.bot.client.smart_click_tile(
            self.station_tile,
            Action.get_action_text(order.action),
            filter_out=[self.order_ui],
            filter_ui=True
        )
        # Get initial state
        state = self._get_station_state(order)
        click_cnt = 0
        loop_count = 0
        
        stop_monitoring = threading.Event()
        
        # Start quick action monitoring thread
        monitor_thread = threading.Thread(
            target=self._quick_action_executor, 
            args=(order, stop_monitoring)
        )
        monitor_thread.daemon = True
        monitor_thread.start()
        max_retort_clicks = random.randint(5, 7)

        self.follow_station()

        try:
            while state:    
                
                if state == 1:
                    if order.action == Action.RETORT:
                        if order.is_done(self.bot.client.get_screenshot()):
                            self.log.info(f"Order {order.ingredients} completed at station with action {order.action}.")
                            break
                        if click_cnt < max_retort_clicks:
                            self.bot.client.click(
                                self.bot.client.mouse_position(),
                                click_cnt=1,
                                rand_move_chance=0,
                                after_click_settle_chance=0
                            )
                            click_cnt += 1
                            
                state = self._get_station_state(order)
                if order.is_done(self.bot.client.get_screenshot()):
                    self.log.info(f"Order {order.ingredients} completed at station with action {order.action}.")
                    break
                
                loop_count += 1
                if loop_count > 40:
                    loop_count = 0
                    self.bot.client.click(
                        self.bot.client.mouse_position(),
                        click_cnt=1,
                        rand_move_chance=0,
                        after_click_settle_chance=0
                    )
        finally:
            # Always clean up thread
            stop_monitoring.set()
            monitor_thread.join(timeout=1.0)

        if not order.is_done(self.bot.client.get_screenshot()):
            raise Exception(f"Failed to complete order {order.ingredients} at station with action {order.action}.")
    
    def _quick_action_executor(self, order: Order, stop_event: threading.Event):
        """
        Thread function to monitor for quick action tiles near cursor.
        
        Args:
            detected_event: Event to signal when quick action is detected
            stop_event: Event to signal when to stop monitoring
        """
        try:
            while not stop_event.is_set():
                # Get current mouse position
                x, y = self.bot.client.mouse_position()
                
                # Create a match result for a 30x30 area around cursor
                search_area = MatchResult(
                    x - 20, y - 20, 
                    x + 20, y + 20,
                    confidence=1.0, 
                    scale=1.0,
                    shape=MatchShape.RECT
                )
                
                try:
                    # Get screenshot and check for color
                    sc = self.bot.client.get_screenshot()
                    crop = search_area.crop_in(sc)
                    
                    # Check if the quick action tile color exists in the cropped area
                    # Convert the cropped image to HSV for better color detection
                    crop_hsv = cv2.cvtColor(np.array(crop), cv2.COLOR_RGB2HSV)
                    quick_action_hsv = cv2.cvtColor(
                        np.uint8([[self.quick_action_tile]]), cv2.COLOR_RGB2HSV
                    )[0][0]

                    # Define a range around the target color
                    lower_bound = np.array([max(quick_action_hsv[0] - 3, 0), 50, 50])
                    upper_bound = np.array([min(quick_action_hsv[0] + 3, 179), 255, 255])

                    # Create a mask for the color range
                    mask = cv2.inRange(crop_hsv, lower_bound, upper_bound)

                    # Check if the mask has more than 10 non-zero pixels
                    color_match = np.count_nonzero(mask) > 10
                    
                    if color_match:
                        self.log.info("Quick action detected! Performing immediate action...")
                        click_cnt = 2 if order.action == Action.AGITATOR else 1

                        for _ in range(click_cnt):
                            # using pyautogui to go as fast as possible
                            duration = random.uniform(0.03, 0.1)
                            pyautogui.click(duration=duration)
                            time.sleep(random.uniform(0.2, 0.4))
                        time.sleep(1)

                except Exception as e:
                    self.log.warning(f"Error checking for quick action: {e}")
                
                # Short sleep to avoid hammering CPU
                time.sleep(0.01)
        except Exception as e:
            self.log.error(f"Quick action monitor thread error: {e}")
    
    def _get_station_state(self,order: Order, retries: int = 3) -> int:
        action = order.action
        sc = self.bot.client.get_filtered_screenshot()
        sc = self.order_ui.remove_from(sc)
        ans = 1
        def find_station_tile():
            return tools.find_color_box(sc, self.station_tile, tol=30)

        def find_quick_action_tile():
            return tools.find_color_box(sc, self.quick_action_tile, tol=30)

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = {
            executor.submit(find_station_tile): "station_tile",
            executor.submit(find_quick_action_tile): "quick_action_tile"
            }

            results = {}
            for future in as_completed(futures):
                try:
                    results[futures[future]] = future.result()
                except:
                    pass

        if "station_tile" in results and "quick_action_tile" in results:
            if results["station_tile"].confidence > results["quick_action_tile"].confidence:
                m: tools.MatchResult = results["station_tile"]
                ans = 1
            else:
                ans = 1
                #return 2
            
        elif "station_tile" in results:
            m: tools.MatchResult = results["station_tile"]
            ans = 1
        elif "quick_action_tile" in results:
            m: tools.MatchResult = results["quick_action_tile"]
            #return 2 # needs to happen quickly

        else:
            self.log.warning("No station found for action.")
            return 0
        # cursor to station
        
        def is_hover_valid() -> bool:
            valid = False
            hover = self.bot.client.get_hover_text().lower()
            for txt in Action.get_action_text(action):
                if txt in hover:
                    valid = True
            return valid
        
        valid = is_hover_valid()
        if not valid:
            x,y = self.bot.client.mouse_position()
            if not m.contains(x,y):
                self.bot.client.move_to(
                    m.get_center(),
                    rand_move_chance=0
                )
            valid = is_hover_valid()
        
        if not valid:    
            if not order.is_done(self.bot.client.get_screenshot()):
                if retries <= 0:
                    raise Exception(f"Exhausted retries for finding action {action} at station.")
                self.log.warning(f"Having trouble finding action {action} at station. Retrying...")
                if retries == 1:
                    self.bot.client.move_off_window()
                return self._get_station_state(order, retries - 1)
            return 0
        return ans




class MissingIngredientError(Exception):
    """
    Exception raised when a required ingredient is missing.
    """
    def __init__(self):
        super().__init__(f"Missing required ingredients")





