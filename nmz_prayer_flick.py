from osrs_client import RuneLiteClient
from mouse_control import random_double_click
from tools import MatchResult
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
    


    

    

def listen_for_termination():
    global terminate
    while not terminate:
        time.sleep(.1)
    
main()