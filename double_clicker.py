import random
import time
import pyautogui
import keyboard
import ctypes
import threading

terminate = False  # Global flag for termination
movement_multiplier = .5

user32 = ctypes.windll.user32


def do_move(x,y):
    x2, y2 = pyautogui.position()

    diff = int((abs(x - x2) + abs(y - y2)) / 10)
    duration = (diff / 100) * movement_multiplier
    print(f'x2: {x2}, y2: {y2}, x: {x}, y: {y}, diff: {diff}, duration={duration}')
    pyautogui.moveTo(x, y,duration=duration)

            
        


def curved_move_to(x, y, duration=1.0):
    """Move the mouse in a curved path to the target position."""
    global terminate
    start_x, start_y = pyautogui.position()

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
        do_move(intermediate_x, intermediate_y)
    do_move(x, y)
    

def random_double_click(x, y):
    global terminate
    if terminate:
        return
    user32.BlockInput(True)  # Disable mouse and keyboard input
    pyautogui.mouseUp()  # Release any mouse button that might be pressed
    target_x = x + random.randint(-5, 5)
    target_y = y + random.randint(-5, 5)
    print(f"Moving to: ({target_x}, {target_y})")
    curved_move_to(target_x, target_y, duration=random.uniform(1.5, 3.0))
    
    #pyautogui.moveTo(target_x, target_y) #,duration=2)
    if terminate:
        return

    pyautogui.click()
    time.sleep(random.uniform(0.15, 0.5))
    do_move(target_x, target_y) # in case the mouse is actively moving
    pyautogui.click()
    user32.BlockInput(False)  # Re-enable input

def listen_for_escape():
    """Thread function to listen for the Esc key."""
    global terminate
    while True:
        if keyboard.is_pressed('esc'):
            print("Terminating...")
            user32.BlockInput(False)  # Re-enable input
            terminate = True
            return
        time.sleep(0.1)

def listen_set_multiplier():
    """Thread function to listen for the Esc key."""
    global movement_multiplier
    while True:
        if keyboard.is_pressed('+'):
            movement_multiplier += .1
            print(f"Movement multiplier: {movement_multiplier}")
        if keyboard.is_pressed('-'):
            movement_multiplier -= .1
            print(f"Movement multiplier: {movement_multiplier}")
        time.sleep(0.1)

def main():
    global terminate
    print("Press '`' to set the initial mouse position, 'Esc' to terminate.")

    # Start Esc listener in a background thread
    esc_thread = threading.Thread(target=listen_for_escape, daemon=True)
    esc_thread.start()
    threading.Thread(target=listen_set_multiplier, daemon=True).start()

    while True:
        if terminate:
            return

        if keyboard.is_pressed('`'):
            x, y = pyautogui.position()
            print(f"Captured initial position at: ({x}, {y})")
            break
        time.sleep(0.1)
    
    # Perform random double-clicks at random intervals
    while not terminate:
        interval = int(random.uniform(40, 55))
        for _ in range(interval):
            if terminate:
                return
            time.sleep(1)


        random_double_click(x, y)

if __name__ == "__main__":
    main()
