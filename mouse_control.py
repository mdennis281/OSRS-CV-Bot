import random
import time
import pyautogui
import keyboard
import ctypes
import threading

terminate = False  # Global flag for termination
movement_multiplier = .5

user32 = ctypes.windll.user32


def _do_move(x,y):
    x2, y2 = pyautogui.position()

    diff = int((abs(x - x2) + abs(y - y2)) / 10)
    duration = (diff / 100) * (movement_multiplier * random.uniform(0.5, 1.5))
    print(f'x2: {x2}, y2: {y2}, x: {x}, y: {y}, diff: {diff}, duration={duration}')
    pyautogui.moveTo(x, y,duration=duration)

def click(x=-1,y=-1):
    if all((x,y)) > -1:
        move_to(x,y)

    pyautogui.click()

            
def move_to_range(x1, y1, x2, y2):
    x = random.randint(x1, x2)
    y = random.randint(y1, y2)
    move_to(x, y)


def move_to(x, y, duration=1.0):
    """Move the mouse in a curved path to the target position."""
    global terminate
    start_x, start_y = pyautogui.position()
    user32.BlockInput(True) 

    diff = abs(x - start_x) + abs(y - start_y)
    steps = int(duration * diff/10)
    steps = min(steps, 2)

    for i in range(steps):
        if terminate:
            return  # Stop moving if Esc is pressed

        t = i / steps
        noise_diff = min(10,diff)
        noise_x = random.uniform(-noise_diff, noise_diff) * (1 - t)
        noise_y = random.uniform(-noise_diff, noise_diff) * (1 - t)

        intermediate_x = start_x + (x - start_x) * t + noise_x
        intermediate_y = start_y + (y - start_y) * t + noise_y
        _do_move(intermediate_x, intermediate_y)
    _do_move(x, y)
    user32.BlockInput(False) 
    

def random_double_click(x, y, variance=5):
    global terminate
    if terminate:
        return
    user32.BlockInput(True)  # Disable mouse and keyboard input
    pyautogui.mouseUp() # release any held mouse buttons
    target_x = x + random.randint(-abs(variance), abs(variance))
    target_y = y + random.randint(-5, 5)
    print(f"Moving to: ({target_x}, {target_y})")
    move_to(target_x, target_y, duration=random.uniform(1.5, 3.0))
    
    #pyautogui.moveTo(target_x, target_y) #,duration=2)
    if terminate:
        return
    
    
    pyautogui.click()
    time.sleep(random.uniform(0.15, 0.5))
    _do_move(target_x, target_y) # in case the mouse is actively moving
    pyautogui.click()
    user32.BlockInput(False)  # Re-enable input