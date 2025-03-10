import random
import time
import pyautogui
import keyboard
import ctypes
import threading

terminate = False  # Global flag for termination
is_paused = False

user32 = ctypes.windll.user32


def do_move(x,y):
    x2, y2 = pyautogui.position()

    diff = int((abs(x - x2) + abs(y - y2)) / 10)
    duration = (diff / 100) 
    print(f'x2: {x2}, y2: {y2}, x: {x}, y: {y}, diff: {diff}, duration={duration}')
    pyautogui.moveTo(x, y,duration=duration)

            
        


def curved_move_to(x, y, duration=1.0):
    """Move the mouse in a curved path to the target position."""
    global terminate
    start_x, start_y = pyautogui.position()
    user32.BlockInput(True)  # Disable mouse and keyboard input

    diff = abs(x - start_x) + abs(y - start_y)
    steps = int(duration * diff/10)
    steps = min(steps, 2)

    for i in range(steps):
        pause_terminate_handler()

        t = i / steps
        noise_diff = min(10,diff)
        noise_x = random.uniform(-noise_diff, noise_diff) * (1 - t)
        noise_y = random.uniform(-noise_diff, noise_diff) * (1 - t)

        intermediate_x = start_x + (x - start_x) * t + noise_x
        intermediate_y = start_y + (y - start_y) * t + noise_y
        do_move(intermediate_x, intermediate_y)
    do_move(x, y)
    user32.BlockInput(False)  # Re-enable input

def random_double_click(x, y):
    global terminate
    pause_terminate_handler()

    target_x = x + random.randint(-5, 5)
    target_y = y + random.randint(-5, 5)
    print(f"Moving to: ({target_x}, {target_y})")
    curved_move_to(target_x, target_y, duration=random.uniform(1.5, 3.0))
    
    pause_terminate_handler()

    pyautogui.click()
    time.sleep(random.uniform(0.15, 0.5))
    do_move(target_x, target_y) # in case the mouse is actively moving
    pyautogui.click()



def listen_for_escape():
    """Thread function to listen for the Esc key."""
    global terminate
    while True:
        if keyboard.is_pressed('esc'):
            print("Terminating...")
            terminate = True
            return
        time.sleep(0.1)

def listen_for_pause():
    global is_paused
    while True:
        if keyboard.is_pressed('`'):
            is_paused = not is_paused
            if is_paused:
                print("Paused. Press '`' to resume.")
            else:
                print("Resumed.")
        if terminate: return
        time.sleep(0.1)

def pause_terminate_handler():
    """Check for pause or termination conditions."""

    if is_paused or terminate: 
        user32.BlockInput(False)  # Re-enable input
    if terminate:
        raise TerminateException("Terminating...")

    if is_paused:
        while is_paused:
            time.sleep(0.1)

def main():
    global terminate
    print("Press '`' to set the initial mouse position, 'Esc' to terminate.")

    # Start Esc listener in a background thread
    esc_thread = threading.Thread(target=listen_for_escape, daemon=True)
    esc_thread.start()
    

    while True:
        pause_terminate_handler()

        if keyboard.is_pressed('`'):
            x, y = pyautogui.position()
            print(f"Captured initial position at: ({x}, {y})")
            break
        time.sleep(0.1)

    threading.Thread(target=listen_for_pause, daemon=True).start()
    
    # Perform random double-clicks at random intervals
    while not terminate:
        interval = random.randint(300,350) / 100
        time.sleep(interval)
        pause_terminate_handler()


        random_double_click(x, y)


class TerminateException(Exception):
    pass

if __name__ == "__main__":
    main()
