from osrs_client import RuneLiteClient
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

    if qp:
        rl_client.click(rl_client.context.quick_prayer)

    rl_client.debug_context()

    # map = rl_client.find_in_window(Image.open("./ui_icons/map.webp"), rl_client.get_screenshot())
    # map.shape = MatchShape.CIRCLE
    # other_match = map.transform(-119, 15)
    
    # rl_client.show_in_window(other_match,color=(0,200,0))


    

    

def listen_for_termination():
    global terminate
    while not terminate:
        time.sleep(.1)
    
main()