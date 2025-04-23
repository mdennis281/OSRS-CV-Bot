from osrs_client import RuneLiteClient, ToolplaneTab, MinimapElement
from mouse_control import random_double_click
from tools import MatchResult, MatchShape
from PIL import Image
import time


rl_client = RuneLiteClient()
terminate = False



def main():
    # Check if RuneLite is open
    if not rl_client.is_open:
        print("RuneLite is not open.")
        return

    qp = rl_client.quick_prayer_active
    print(f"QP Enabled: {qp}")

    rl_client.click_minimap(MinimapElement.PRAYER, click_cnt=2)

    rl_client.get_screenshot()

    rl_client.click_toolplane(ToolplaneTab.PRAYER)
    rl_client.get_screenshot()

    rl_client.click_toolplane(ToolplaneTab.INVENTORY)

    rl_client.get_screenshot()

    rl_client.click_item('Dwarven rock cake', click_cnt=20)

    

    # map = rl_client.find_in_window(Image.open("./ui_icons/map.webp"), rl_client.get_screenshot())
    # map.shape = MatchShape.CIRCLE
    # other_match = map.transform(-119, 15)
    
    # rl_client.show_in_window(other_match,color=(0,200,0))


    

    

def listen_for_termination():
    global terminate
    while not terminate:
        time.sleep(.1)
    
main()
