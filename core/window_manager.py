"""
Cross-platform window management module for OSRS client.
Provides window manipulation functionality across Windows, macOS, and Linux.
"""

import sys
import pyautogui

# Platform detection
IS_WINDOWS = sys.platform.startswith('win')
IS_MAC = sys.platform == 'darwin'
IS_LINUX = sys.platform.startswith('linux')

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
                print("Warning: pygetwindow not found, falling back to basic window manager")
                return BasicWindowManager()
        elif IS_MAC:
            try:
                import AppKit
                return MacWindowManager()
            except ImportError:
                print("Warning: pyobjc not found, falling back to basic window manager")
                return BasicWindowManager()
        elif IS_LINUX:
            try:
                import Xlib
                return LinuxWindowManager()
            except ImportError:
                print("Warning: python-xlib not found, falling back to basic window manager")
                return BasicWindowManager()
        else:
            print(f"Warning: Unsupported platform {sys.platform}, using basic window manager")
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
        return self.gw.getWindowsWithTitle(title)

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
    
    def minimize(self):
        """Minimize the window (best effort)"""
        pass
    
    def restore(self):
        """Restore the window (best effort)"""
        self.activate()

class LinuxWindowManager:
    """Linux-specific window management using Xlib"""
    
    def __init__(self):
        import Xlib
        import Xlib.display
        self.display = Xlib.display.Display()
        self.root = self.display.screen().root
    
    def get_windows_with_title(self, title):
        """Get windows with the given title using Xlib"""
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
                        windows.append(LinuxWindow(window, window_title, self.display))
                except:
                    continue
                    
            return windows
        except Exception as e:
            print(f"Error enumerating Linux windows: {e}")
            return []

class LinuxWindow:
    """Linux window wrapper to match the pygetwindow interface"""
    
    def __init__(self, window, title, display):
        self.window = window
        self.title = title
        self.display = display
        
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
        try:
            self.window.set_input_focus()
            self.window.configure(stack_mode=Xlib.X.Above)
            self.display.sync()
        except:
            pass
    
    def minimize(self):
        """Minimize the window"""
        try:
            WM_CHANGE_STATE = self.display.intern_atom('WM_CHANGE_STATE')
            iconify_event = Xlib.protocol.event.ClientMessage(
                window=self.window,
                client_type=WM_CHANGE_STATE,
                data=(32, [Xlib.Xutil.IconicState, 0, 0, 0, 0])
            )
            mask = Xlib.X.SubstructureRedirectMask | Xlib.X.SubstructureNotifyMask
            self.display.screen().root.send_event(iconify_event, mask)
            self.display.sync()
        except:
            pass
    
    def restore(self):
        """Restore the window"""
        self.activate()
