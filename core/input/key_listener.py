import threading
import time
import keyboard  # Requires admin privileges on some systems


class KeyListener:
    def __init__(self, interval=0.1):
        self.interval = interval
        self.listeners = {}  # key: list of callbacks
        self.running = False
        self.thread = threading.Thread(target=self._run, daemon=True)

    def add_listener(self, key: str, callback):
        """Register a callback for a key."""
        if key not in self.listeners:
            self.listeners[key] = []
        self.listeners[key].append(callback)

    def start(self):
        """Start the listener thread."""
        if not self.running:
            self.running = True
            if not self.thread.is_alive():
                self.thread = threading.Thread(target=self._run, daemon=True)
                self.thread.start()

    def stop(self):
        """Stop the listener thread."""
        self.running = False

    def wait_for_term(self):
        """Wait for the listener to terminate."""
        self.thread.join()

    def _run(self):
        print("[KeyListener] Listening for keypresses...")
        while self.running:
            for key, callbacks in self.listeners.items():
                if keyboard.is_pressed(key):
                    for callback in callbacks:
                        try:
                            callback()
                        except Exception as e:
                            print(f"[KeyListener] Error in callback for '{key}': {e}")
                    time.sleep(0.3)  # debounce to avoid repeat spam
            time.sleep(self.interval)
    
    


# === Testable Example ===
if __name__ == "__main__":
    def on_b():
        print("[Callback] B was pressed!")
    
    def on_a():
        print("[Callback] A key was pressed!")

    def on_a_second():
        print("[Callback] Another function bound to A!")

    def on_c(listener: KeyListener):
        print("[Callback] C was pressed!")
        listener.stop()

    listener = KeyListener(interval=0.1)
    listener.add_listener('b', on_b)
    listener.add_listener('a', on_a)
    listener.add_listener('a', on_a_second)
    listener.add_listener('c', listener.stop()) 

    listener.start()
    print("Press 'A' or 'Esc' to trigger callbacks. Ctrl+C to exit.")

    try:
        listener.wait_for_term()
    except KeyboardInterrupt:
        print("Stopping listener...")
        listener.stop()
