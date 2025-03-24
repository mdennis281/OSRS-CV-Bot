import pygetwindow as gw
import pyautogui
import mss
import time
from PIL import Image
import io
from tools import find_subimage, MatchResult

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
class RuneLiteClient(GenericWindow):
    def __init__(self):
        super().__init__("RuneLite -")

    def find_in_window(self, img: Image.Image):
        """Finds a subimage within the RuneLite window."""
        screenshot = self.get_screenshot()
        return find_subimage(screenshot, img)
    

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
