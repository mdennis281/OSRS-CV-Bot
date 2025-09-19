"""
Cross-platform window management module for OSRS client.
Provides window manipulation functionality across Windows, macOS, and Linux.
"""

import sys
from turtle import title
import pyautogui
import time
import keyboard
import importlib
from core.logger import get_logger

# Platform detection
IS_WINDOWS = sys.platform.startswith('win')
IS_MAC = sys.platform == 'darwin'
IS_LINUX = sys.platform.startswith('linux')

log = get_logger("OSWindow")

class WindowManager:
    """Cross-platform window management"""
    
    @staticmethod
    def create():
        """Factory method to create appropriate window manager for the current platform"""
        if IS_WINDOWS:
            try:
                import pygetwindow as gw
                return WindowsWindowManager()
            except ImportError:
                log.warning("Warning: pygetwindow not found, falling back to basic window manager")
                return BasicWindowManager()
        elif IS_MAC:
            try:
                import AppKit
                return MacWindowManager()
            except ImportError:
                log.warning("Warning: pyobjc not found, falling back to basic window manager")
                return BasicWindowManager()
        elif IS_LINUX:
            try:
                import Xlib
                return LinuxWindowManager()
            except ImportError:
                log.warning("Warning: python-xlib not found, falling back to basic window manager")
                return BasicWindowManager()
        else:
            log.warning(f"Unsupported platform {sys.platform}, using basic window manager")
            return BasicWindowManager()

class BasicWindowManager:
    """Basic window manager for fallback when platform-specific implementations are unavailable"""
    
    def get_windows_with_title(self, title):
        """Get windows with the given title"""
        # Return a dummy window object that allows the script to continue
        return [BasicWindow(title)]
    
class BasicWindow:
    """Fallback window implementation when platform-specific windows are unavailable"""
    
    def __init__(self, title):
        self.title = title
        screen_size = pyautogui.size()
        self.left = 0
        self.top = 0
        self.width = screen_size[0]
        self.height = screen_size[1]
        self.right = self.left + self.width
        self.bottom = self.top + self.height
        self.isActive = True
    
    def activate(self):
        """Activate the window (no-op in basic implementation)"""
        pass
    
    def bring_to_focus(self):
        """Bring window to foreground (basic implementation)"""
        try:
            # Minimal implementation - just call activate
            self.activate()
        except Exception as e:
            log.error(f"Error bringing window to focus: {e}")
    
    def minimize(self):
        """Minimize the window (no-op in basic implementation)"""
        pass
    
    def restore(self):
        """Restore the window (best effort)"""
        pass
    
    def is_focused(self):
        """Always returns True for fallback window"""
        return True

class WindowsWindowManager:
    """Windows-specific window management using pygetwindow"""
    
    def __init__(self):
        import pygetwindow as gw
        self.gw = gw
    
    def get_windows_with_title(self, title):
        """Get windows with the given title using pygetwindow"""
        windows = self.gw.getWindowsWithTitle(title)
        return [WindowsWindow(window) for window in windows]

class WindowsWindow:
    """Windows window wrapper to ensure consistent interface"""
    
    def __init__(self, win32_window):
        # Copy all attributes from the original window
        import pygetwindow as gw
        self.gw = gw
        self.win32_window = win32_window

    @property
    def top(self):
        """Return the top coordinate of the window"""
        return self.win32_window.top
    @property
    def left(self):
        """Return the left coordinate of the window"""
        return self.win32_window.left
    
    @property
    def right(self):
        """Return the right coordinate of the window"""
        return self.win32_window.right
    
    @property
    def bottom(self):
        """Return the bottom coordinate of the window"""
        return self.win32_window.bottom
    
    @property
    def width(self):
        """Return the width of the window"""
        return self.win32_window.width
    
    @property
    def height(self):
        """Return the height of the window"""
        return self.win32_window.height
    
    @property
    def title(self):
        """Return the title of the window"""
        return self.win32_window.title
    
    @property
    def isActive(self):
        """Return True if this window is the active window"""
        return self.win32_window.isActive
    
    def activate(self):
        """Activate the window"""
        self.win32_window.activate()
    
    def bring_to_focus(self):
        """Bring window to foreground on Windows"""
        if not self.is_focused():
            log.info('Bringing window to focus')
            # Pressing alt makes activate() more reliable on Windows
            try:
                keyboard.press('alt')
                self.win32_window.activate()
            except:
                self.win32_window.minimize()
                self.win32_window.restore()
                time.sleep(0.3)
            finally:
                keyboard.release('alt')

    def is_focused(self):
        """Return True if this window is the active window"""
        try:
            
            active = self.gw.getActiveWindow()
            return active and active._hWnd == self.win32_window._hWnd
        except Exception:
            return False
    
    def minimize(self):
        """Minimize the window"""
        self.win32_window.minimize()
    
    def restore(self):
        """Restore the window"""
        self.win32_window.restore()

class MacWindowManager:
    """macOS-specific window management using AppKit"""
    
    def __init__(self):
        import AppKit
        self.AppKit = AppKit
    
    def get_windows_with_title(self, title):
        """Get windows with the given title using AppKit"""
        workspace = self.AppKit.NSWorkspace.sharedWorkspace()
        apps = workspace.runningApplications()
        matching_apps = [app for app in apps if title.lower() in app.localizedName().lower()]
        
        if not matching_apps:
            return []
        
        # Create a wrapper object that mimics the pygetwindow interface
        return [MacWindow(app, title) for app in matching_apps]

class MacWindow:
    """macOS window wrapper to match the pygetwindow interface"""
    
    def __init__(self, app, title):
        self.app = app
        self._title = title
    
    @property
    def title(self):
        """Return the title of the window"""
        return self._title
    
    @property
    def width(self):
        """Return the width of the window"""
        # Get screen size as a fallback for macOS
        screen = pyautogui.size()
        return screen[0]
    
    @property
    def height(self):
        """Return the height of the window"""
        # Get screen size as a fallback for macOS
        screen = pyautogui.size()
        return screen[1]
    
    @property
    def left(self):
        """Return the left coordinate of the window"""
        return 0
    
    @property
    def top(self):
        """Return the top coordinate of the window"""
        return 0
    
    @property
    def right(self):
        """Return the right coordinate of the window"""
        return self.left + self.width
    
    @property
    def bottom(self):
        """Return the bottom coordinate of the window"""
        return self.top + self.height
    
    @property
    def isActive(self):
        """Return True if this window is the active app"""
        try:
            return self.app.isActive()
        except Exception:
            return False
    
    def activate(self):
        """Activate the window"""
        self.app.activateWithOptions_(0)
    
    def bring_to_focus(self):
        """Bring window to foreground on macOS"""
        try:
            # Press Command key to help with activation
            if keyboard:
                try:
                    keyboard.press('command')
                    self.activate()
                    time.sleep(0.1)
                finally:
                    keyboard.release('command')
            else:
                # Fallback if keyboard module isn't available
                self.activate()
                
            # Additional activation attempt if needed
            if not self.isActive:
                self.app.activateWithOptions_(1)  # 1 = Activate and bring to front
        except Exception as e:
            log.error(f"Error focusing macOS window: {e}")
    
    def minimize(self):
        """Minimize the window (best effort)"""
        pass
    
    def restore(self):
        """Restore the window (best effort)"""
        self.activate()

    def is_focused(self):
        """Return True if this window is the active app"""
        try:
            return self.app.isActive()
        except Exception:
            return False

class LinuxWindowManager:
    """Linux-specific window management using Xlib"""
    
    def __init__(self):
        try:
            import Xlib
            import Xlib.display
            self.Xlib = Xlib
            self.display = Xlib.display.Display()
            self.root = self.display.screen().root
        except ImportError:
            log.warning("Xlib module not found or couldn't be imported")
            self.Xlib = None
            self.display = None
            self.root = None
    
    def get_windows_with_title(self, title):
        """Get windows with the given title using Xlib"""
        if not self.Xlib:
            log.warning("Xlib not available, returning empty window list")
            return []
            
        try:
            from Xlib.protocol import event
            NET_CLIENT_LIST = self.display.intern_atom('_NET_CLIENT_LIST')
            windows = []
            
            window_ids = self.root.get_full_property(NET_CLIENT_LIST, 
                                                    self.display.intern_atom('WINDOW')).value
            
            for window_id in window_ids:
                window = self.display.create_resource_object('window', window_id)
                
                try:
                    window_title = window.get_wm_name()
                    if window_title and title.lower() in window_title.lower():
                        windows.append(LinuxWindow(window, window_title, self.display, self.Xlib))
                except:
                    continue
                    
            return windows
        except Exception as e:
            log.error(f"Error enumerating Linux windows: {e}")
            return []

class LinuxWindow:
    """Linux window wrapper to match the pygetwindow interface"""
    
    def __init__(self, window, title, display, Xlib):
        self.window = window
        self._title = title
        self.display = display
        self.Xlib = Xlib  # Store Xlib module reference
        self.root = self.display.screen().root
    
    @property
    def title(self):
        """Return the title of the window"""
        return self._title
    
    @property
    def width(self):
        """Return the width of the window"""
        try:
            geom = self.window.get_geometry()
            return geom.width
        except Exception:
            # Fallback to screen width
            return pyautogui.size()[0]
    
    @property
    def height(self):
        """Return the height of the window"""
        try:
            geom = self.window.get_geometry()
            return geom.height
        except Exception:
            # Fallback to screen height
            return pyautogui.size()[1]
    
    @property
    def left(self):
        """Return the left coordinate of the window"""
        try:
            # Try translate_coords first
            x, y, _ = self.window.translate_coords(self.root, 0, 0)
            return max(0, min(pyautogui.size()[0] - 1, x))
        except Exception:
            # Fallback to traversing window tree
            return self._get_window_x_position()
    
    @property
    def top(self):
        """Return the top coordinate of the window"""
        try:
            # Try translate_coords first
            x, y, _ = self.window.translate_coords(self.root, 0, 0)
            return max(0, min(pyautogui.size()[1] - 1, y))
        except Exception:
            # Fallback to traversing window tree
            return self._get_window_y_position()
    
    @property
    def right(self):
        """Return the right coordinate of the window"""
        return self.left + self.width
    
    @property
    def bottom(self):
        """Return the bottom coordinate of the window"""
        return self.top + self.height
    
    @property
    def isActive(self):
        """Return True if this window is the active window"""
        return self._is_active()
    
    def _get_window_x_position(self):
        """Get window X position by traversing the window tree"""
        try:
            geom = self.window.get_geometry()
            x = geom.x
            
            parent = self.window.query_tree().parent
            
            while parent and parent.id != self.root.id:
                parent_geom = parent.get_geometry()
                x += parent_geom.x
                parent = parent.query_tree().parent
            
            return max(0, min(pyautogui.size()[0] - 1, x))
        except Exception as e:
            log.error(f"Error getting window X position: {e}")
            return 0
    
    def _get_window_y_position(self):
        """Get window Y position by traversing the window tree"""
        try:
            geom = self.window.get_geometry()
            y = geom.y
            
            parent = self.window.query_tree().parent
            
            while parent and parent.id != self.root.id:
                parent_geom = parent.get_geometry()
                y += parent_geom.y
                parent = parent.query_tree().parent
            
            return max(0, min(pyautogui.size()[1] - 1, y))
        except Exception as e:
            log.error(f"Error getting window Y position: {e}")
            return 0
    
    def _is_active(self):
        """Check if the window is active"""
        try:
            active_window_id = self.display.get_input_focus().focus.id
            return active_window_id == self.window.id
        except:
            return False
    
    def activate(self):
        """Activate the window"""
        if not self.Xlib:
            log.warning("Xlib not available, can't activate window")
            return
            
        try:
            # Fix: Add the required arguments to set_input_focus
            self.window.set_input_focus(self.Xlib.X.RevertToParent, 0)
            self.window.configure(stack_mode=self.Xlib.X.Above)
            self.display.flush()
            self.display.sync()
        except Exception as e:
            log.error(f"Error activating window: {e}")
    
    def bring_to_focus(self):
        """Bring window to foreground on Linux"""
        if not self.Xlib:
            log.warning("Xlib not available, can't focus window")
            return
            
        try:
            # Use direct focus method - this is the most reliable approach
            self.window.set_input_focus(self.Xlib.X.RevertToParent, 0)
            self.window.configure(stack_mode=self.Xlib.X.Above)
            self.display.flush()
            self.display.sync()
            
            # Give window manager time to respond
            time.sleep(0.2)
            
            # Check if window activation was successful
            if self._is_active():
                return
            
            # If focus failed, try once more with map operation
            log.debug("First focus attempt failed, trying map operation")
            self.window.map()
            self.window.raise_window()
            self.display.flush()
            self.display.sync()
        except Exception as e:
            log.error(f"Error focusing Linux window: {e}")
    
    def minimize(self):
        """Minimize the window"""
        if not self.Xlib:
            return
            
        try:
            WM_CHANGE_STATE = self.display.intern_atom('WM_CHANGE_STATE')
            iconify_event = self.Xlib.protocol.event.ClientMessage(
                window=self.window,
                client_type=WM_CHANGE_STATE,
                data=(32, [self.Xlib.Xutil.IconicState, 0, 0, 0, 0])
            )
            mask = self.Xlib.X.SubstructureRedirectMask | self.Xlib.X.SubstructureNotifyMask
            self.display.screen().root.send_event(iconify_event, mask)
            self.display.sync()
        except Exception as e:
            log.error(f"Error minimizing window: {e}")
    
    def restore(self):
        """Restore the window"""
        self.activate()

    def is_focused(self):
        """Return True if this window is the active window"""
        return self._is_active()
