import os
import time
import ctypes
import threading
import sys

class CoreDefense:
    """Active runtime watchdog to detect and prevent memory tampering and debugging."""
    
    FORBIDDEN_PROCESSES = [
        "cheat engine", "x64dbg", "ollydbg", "wireshark", 
        "process hacker", "vmmap", "die.exe", "idat.exe", "idat64.exe"
    ]

    def __init__(self, lockout_callback):
        self.lockout_callback = lockout_callback
        self.running = False
        self._thread = None

    def start(self):
        """Starts the background monitoring thread."""
        if not self.running:
            self.running = True
            self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self._thread.start()

    def stop(self):
        """Stops the monitoring thread."""
        self.running = False

    def _monitor_loop(self):
        """Continuously scans for threats (debuggers, forbidden tools, windows)."""
        while self.running:
            try:
                # 1. Check for attached debuggers (API level)
                if self._check_debuggers():
                    self._trigger_emergency_lockdown("Debugger Detected")
                    break
                
                # 2. Check for unauthorized tools (Process + Window level)
                if self._check_forbidden_tools():
                    self._trigger_emergency_lockdown("Forbidden Reversing Tool Detected")
                    break
                
                # 3. Check for remote debuggers
                if self._check_remote_debuggers():
                    self._trigger_emergency_lockdown("Remote Debugger Detected")
                    break

            except Exception as e:
                print(f"[SECURITY] Defense scan error: {type(e).__name__}: {e}")
            
            time.sleep(2) 

    def _check_forbidden_tools(self) -> bool:
        """Checks both process list and window titles for forbidden tools."""
        # A. Process List Scan
        try:
            with os.popen('tasklist /FI "STATUS eq running" /NH') as f:
                output = f.read().lower()
                for proc in self.FORBIDDEN_PROCESSES:
                    if proc in output:
                        return True
        except Exception:
            pass

        # B. Window Title Scan (Deep Scan)
        return self._scan_window_titles()

    def _scan_window_titles(self) -> bool:
        """Enumerates all windows to find forbidden titles."""
        found = [False]
        EnumWindows = ctypes.windll.user32.EnumWindows
        EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int))
        GetWindowText = ctypes.windll.user32.GetWindowTextW
        GetWindowTextLength = ctypes.windll.user32.GetWindowTextLengthW

        def foreach_window(hwnd, lParam):
            length = GetWindowTextLength(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                GetWindowText(hwnd, buff, length + 1)
                title = buff.value.lower()
                for tool in self.FORBIDDEN_PROCESSES:
                    if tool in title:
                        found[0] = True
                        return False # Stop enumerating
            return True

        EnumWindows(EnumWindowsProc(foreach_window), 0)
        return found[0]

    def _check_debuggers(self) -> bool:
        """Checks for an attached local debugger using Windows API."""
        try:
            return ctypes.windll.kernel32.IsDebuggerPresent() != 0
        except Exception:
            return False

    def _check_remote_debuggers(self) -> bool:
        """Checks for remote debugging sessions attached to this process."""
        try:
            is_debugged = ctypes.c_int(0)
            ctypes.windll.kernel32.CheckRemoteDebuggerPresent(
                ctypes.windll.kernel32.GetCurrentProcess(),
                ctypes.byref(is_debugged)
            )
            return is_debugged.value != 0
        except Exception:
            return False

    def _trigger_emergency_lockdown(self, reason: str):
        """Emergency procedure: wipe memory, lock vault, and terminate."""
        print(f"\n[!] SECURITY BREACH: {reason}")
        if self.lockout_callback:
            self.lockout_callback()
        
        # Hard exit to prevent any further memory access
        os._exit(1)
