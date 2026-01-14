import time
from functools import wraps
from bots.core.cfg_types import BreakCfgParam
from core.logger import get_logger
import threading


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
        self.break_until: float = 0
        self.break_config: BreakCfgParam = None
        self.log = get_logger("ScriptControl")
        self._listener: threading.Thread = None
        
        
        self.start_listener()
        
        

    
    def start_listener(self):
        """Start a thread to listen for termination and pause requests.

        Uses keyboard.hook so we can differentiate physical PageUp/PageDown keys
        from numpad 9/3 (which report as PageUp/PageDown when NumLock is off).
        We only act on PageUp/PageDown when the event is NOT from keypad. This
        prevents accidental termination/pause when using numpad navigation.
        """
        if self._listener is None or not self._listener.is_alive():
            self._listener = threading.Thread(target=self._listen_for_control, daemon=True)
            self._listener.start()


    def propose_break(self):
        """Propose break based on configuration."""
        if self.break_config:
            if self.break_config.should_break():
                sec = int(self.break_config.break_duration.choose())
                self.initialize_break(
                    sec
                )
                self.log.info(f"Sleeping for {sec} seconds.")
        else:
            self.log.warning("Break proposed but no break configuration set.")
    def _listen_for_control(self):
        """Thread function to listen for control signals.

        Distinguishes keypad vs non-keypad PageUp/PageDown using event.is_keypad.
        Terminate: Physical PageUp (not keypad) key down.
        Pause toggle: Physical PageDown (not keypad) key down.

        Numpad 9 / 3 (NumLock off -> PageUp/PageDown) are ignored so they don't
        unintentionally terminate or pause the script.
        """
        try:
            import keyboard  # type: ignore
        except ImportError:
            self.log.error("keyboard module not available; control hotkeys disabled.")
            return

        # Debounce to avoid rapid toggles if OS sends repeats
        last_pause_toggle = 0.0
        toggle_cooldown = 0.4  # seconds

        def handler(e):
            nonlocal last_pause_toggle
            try:
                # We only act on key down events
                if getattr(e, 'event_type', None) != 'down':
                    return
                name = (e.name or '').lower()
                is_keypad = getattr(e, 'is_keypad', False)
                is_pageup = name in ('page up', 'pageup')
                is_pagedown = name in ('page down', 'pagedown')

                # Is pageup and is not from numpad (Numpad 9)
                if is_pageup and not is_keypad:
                    self.terminate = True
                # Is pagedown and is not from numpad (Numpad 3)
                elif is_pagedown and not is_keypad:
                    now = time.time()
                    if now - last_pause_toggle >= toggle_cooldown:
                        self.pause = not self.pause
                        last_pause_toggle = now
                else:
                    # Optional future: map dedicated keypad combo if desired
                    pass
            except Exception as ex:  # Never let hook raise
                self.log.debug(f"Control hook error: {ex}")

        hook = keyboard.hook(handler)
        # Keep thread alive until termination requested
        while not self.terminate:
            time.sleep(0.25)
        keyboard.unhook(hook)
        self.log.info("Control listener thread exiting.")

    @property
    def terminate(self):
        return self._terminate

    @terminate.setter
    def terminate(self, value: bool):
        if self._terminate != value:
            self.log.info(f"Terminate set to {value}")
        self._terminate = value

    @property
    def pause(self):
        return self._pause
    
    def reset(self):
        """Reset control flags to default states."""
        self.log.info("Resetting ScriptControl state.")
        self._terminate = False
        self._pause = False
        self.break_until = 0
        
        # Ensure listener thread calls are responsive
        self.start_listener()

    @pause.setter
    def pause(self, value: bool):
        if self._pause != value:
            self.log.info(f"Pause {'enabled' if value else 'disabled'}")
        self._pause = value

    def initialize_break(self, seconds: int):
        """Set the break duration without causing the caller to sleep."""
        self.break_until = time.time() + int(seconds)

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
                    raise ScriptTerminationException()
                time.sleep(1)
            if self.terminate:
                raise ScriptTerminationException()
            return func(*args, **kwargs)
        return wrapper


class ScriptTerminationException(Exception):
    """Exception raised when script termination is requested."""
    def __init__(self, message="Script termination requested."):
        self.message = message
        super().__init__(self.message)
        
    def __str__(self):
        return self.message