import pygetwindow as gw
import pyautogui
import mss
import time
from PIL import Image
import io
from tools import find_subimage, MatchResult, draw_box_on_image, MatchShape
from mouse_control import click_in_match

class GenericWindow:
    def __init__(self, window_title):
        self.window_title = window_title
        self.window = None
        self.update_window()

    def update_window(self):
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
    
    def find_in_window(self, img: Image.Image, screenshot: Image=None) -> MatchResult:
        """Finds a subimage within the RuneLite window."""
        screenshot = screenshot or self.get_screenshot()
        return find_subimage(screenshot, img)
    
    def show_in_window(self, match: MatchResult, screenshot: Image=None, color="red"):
        """Draws a box around the found match in the screenshot."""
        screenshot = screenshot or self.get_screenshot()
        if screenshot:
            img_with_box = match.debug_draw(screenshot, color=color)
            img_with_box.show()

    def click(self, match: MatchResult):
        """Clicks on the center of the matched area."""
        match = match.transform(self.window.left, self.window.top)
        click_in_match(match)

class RLContext:
    health: MatchResult = None
    prayer: MatchResult = None
    run: MatchResult = None
    spec: MatchResult = None

    def get_minimap_stat(self,match: MatchResult, screenshot: Image.Image) -> int:
        """Returns the health value from the screenshot."""
        val = match.transform(-22, 12)
        val.end_x = val.start_x + 22
        val.end_y = val.start_y + 15
        val.shape = MatchShape.SQUARE
        val.debug_draw(screenshot, color=(255, 255, 255))
        

        return val.extract_text(screenshot)

    def find_matches(self, screenshot: Image.Image):
        """Finds and sets the matches for health, prayer, run, and spec."""

        map = find_subimage(screenshot, Image.open("ui_icons/map.webp"))
        map.shape = MatchShape.CIRCLE
        self.health = map.transform(-151, -76)
        self.prayer = map.transform(-151, -42)
        self.run = map.transform(-141, -10)
        self.spec = map.transform(-119, 15)
        


class RuneLiteClient(GenericWindow):
    def __init__(self,username=''):
        super().__init__(f'RuneLite - {username}')
        self.context = RLContext()
        self._last_screenshot = None
        self.on_resize()

    @property
    def screenshot(self) -> Image.Image:
        if self._last_screenshot:
            return self._last_screenshot
        return self.get_screenshot()
    
    def debug_context(self):
        self.context.find_matches(self.screenshot)
        self.context.health.debug_draw(self.screenshot, color=(0, 255, 0))
        self.context.prayer.debug_draw(self.screenshot, color=(0, 0, 255))
        self.context.run.debug_draw(self.screenshot, color=(255, 0, 0))
        self.context.spec.debug_draw(self.screenshot, color=(255, 255, 0))
        health_val = self.context.get_minimap_stat(self.context.health, self.screenshot)
        print(f"Health: {health_val}")
        prayer_val = self.context.get_minimap_stat(self.context.prayer, self.screenshot)
        print(f"Prayer: {prayer_val}")
        run_val = self.context.get_minimap_stat(self.context.run, self.screenshot)
        print(f"Run: {run_val}")
        spec_val = self.context.get_minimap_stat(self.context.spec, self.screenshot)
        print(f"Spec: {spec_val}")
        self.screenshot.show()

    
    def on_resize(self):
        sc = self.get_screenshot()
        self.context.find_matches(sc)

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
