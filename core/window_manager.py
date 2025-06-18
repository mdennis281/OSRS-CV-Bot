"""
Cross-platform window management module for OSRS client.
Provides window manipulation functionality across Windows, macOS, and Linux.
"""

import sys
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
        self.win32_window = win32_window
        self.title = win32_window.title
        self.left = win32_window.left
        self.top = win32_window.top
        self.width = win32_window.width
        self.height = win32_window.height
        self.right = win32_window.right
        self.bottom = win32_window.bottom
        self.isActive = win32_window.isActive
    
    def activate(self):
        """Activate the window"""
        self.win32_window.activate()
    
    def bring_to_focus(self):
        """Bring window to foreground on Windows"""
        # Pressing alt makes activate() more reliable on Windows
        try:
            # Pressing alt makes activate() more reliable
            keyboard.press('alt')
            self.win32_window.activate()
        except:
            self.win32_window.minimize()
            self.win32_window.restore()
            time.sleep(0.3)
        finally:
            keyboard.release('alt')
    
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
        self.title = title
        # Get screen size as a fallback
        screen = pyautogui.size()
        self.width = screen[0]
        self.height = screen[1]
        self.left = 0
        self.top = 0
        self.right = self.left + self.width
        self.bottom = self.top + self.height
        self.isActive = app.isActive()
    
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
        self.title = title
        self.display = display
        self.Xlib = Xlib  # Store Xlib module reference
        
        # Get geometry
        geom = window.get_geometry()
        self.width = geom.width
        self.height = geom.height
        
        # Try to get absolute position
        try:
            root_pos = window.translate_coords(self.display.screen().root, 0, 0)
            self.left = root_pos.x
            self.top = root_pos.y
        except:
            # Fallback
            self.left = 0
            self.top = 0
            
        self.right = self.left + self.width
        self.bottom = self.top + self.height
        
        # Check if window is active
        self.isActive = self._is_active()
    
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
