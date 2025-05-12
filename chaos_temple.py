#!/usr/bin/env python3
"""
Rapid two-point clicker. 
Press:
  1 to record mouse position #1
  2 to record mouse position #2
  3 to start/pause alternating clicks (200 ms between clicks)
  Esc to exit
Requires: pyautogui, keyboard
    pip install pyautogui keyboard
"""
import threading
import time
import sys

import pyautogui
import keyboard

# Shared state
pos1 = None
pos2 = None
clicker_active = False
exit_flag = False

def click_loop():
    """Background thread: when enabled, alternates clicks at pos1/pos2."""
    global exit_flag
    while not exit_flag:
        if clicker_active:
            # Both positions must be set
            if pos1 is None or pos2 is None:
                time.sleep(0.1)
                continue
            pyautogui.moveTo(x=pos1[0], y=pos1[1],duration=.15)
            pyautogui.click()  # sub .25 sec delay
            pyautogui.moveTo(x=pos2[0], y=pos2[1],duration=.15)
            pyautogui.click()
        else:
            time.sleep(0.1)
def record_pos1():
    global pos1
    pos1 = pyautogui.position()
    print(f"[1] Position 1 recorded at {pos1}")

def record_pos2():
    global pos2
    pos2 = pyautogui.position()
    print(f"[2] Position 2 recorded at {pos2}")

def toggle_clicker():
    global clicker_active
    if pos1 is None or pos2 is None:
        print("⚠️  Record both positions first (press 1 then 2).")
        return
    clicker_active = not clicker_active
    state = "▶️  Running" if clicker_active else "⏸️  Paused"
    print(f"[3] {state}")

def exit_program():
    global exit_flag
    exit_flag = True
    print("🛑 Exiting...")

def main():
    # Register hotkeys
    keyboard.add_hotkey('1', record_pos1)
    keyboard.add_hotkey('2', record_pos2)
    keyboard.add_hotkey('3', toggle_clicker)
    keyboard.add_hotkey('esc', exit_program)

    # Start clicker thread
    thread = threading.Thread(target=click_loop)
    thread.start()

    print("Ready. Press 1, 2, 3 or Esc.")
    # Block until Esc is pressed
    keyboard.wait('esc')
    # Wait for thread to finish cleanly
    thread.join()
    sys.exit(0)

if __name__ == "__main__":
    main()
