import time
from functools import wraps

class SingletonMeta(type):
    """A thread-safe implementation of a Singleton metaclass."""
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]

class ScriptControl(metaclass=SingletonMeta):
    def __init__(self):
        self._terminate = False
        self._pause = False
        self.break_until = 0
        self.start_listener()
    
    def start_listener(self):
        """Start a thread to listen for termination and pause requests."""
        import threading
        threading.Thread(target=self._listen_for_control, daemon=True).start()
    def _listen_for_control(self):
        """Thread function to listen for control signals."""
        import keyboard
        while True:
            if keyboard.is_pressed('page up'):
                self.terminate = True
                return
            if keyboard.is_pressed('page down'):
                self.pause = not self.pause
            time.sleep(0.1)

    @property
    def terminate(self):
        return self._terminate

    @terminate.setter
    def terminate(self, value: bool):
        if self._terminate != value:
            print(f"Terminate set to {value}")
        self._terminate = value

    @property
    def pause(self):
        return self._pause

    @pause.setter
    def pause(self, value: bool):
        if self._pause != value:
            print(f"Pause {'enabled' if value else 'disabled'}")
        self._pause = value

    def initialize_break(self, seconds: int):
        """Set the break duration without causing the caller to sleep."""
        self.break_until = time.time() + seconds

    def guard(self, func):
        """
        Decorator to enforce termination and break logic.
        Raises RuntimeError if termination is requested.
        Waits if a break is active.
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            while time.time() < self.break_until or self.pause:
                if self.terminate:
                    raise RuntimeError("Script terminated.")
                time.sleep(1)
            if self.terminate:
                raise RuntimeError("Script terminated.")
            return func(*args, **kwargs)
        return wrapper


