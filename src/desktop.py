"""Desktop adapters. Imported only in the engine process or for emergency cleanup."""
import ctypes
import os
import queue
import threading


def emergency_release(shared_held):
    # Direct release bypasses PyAutoGUI's corner fail-safe, which must not prevent
    # cleanup. The shared bit is set BEFORE mouseDown and cleared AFTER mouseUp.
    # Production uses a RawValue: a killed child cannot orphan a mutex and
    # deadlock the GUI's cleanup. Parent writes only after the child has exited.
    if shared_held.value:
        if os.name == "nt":
            ctypes.windll.user32.mouse_event(0x0004, 0, 0, 0, 0)
        else:
            import pyautogui
            previous = pyautogui.FAILSAFE
            try:
                pyautogui.FAILSAFE = False
                pyautogui.mouseUp(button="left", _pause=False)
            finally:
                pyautogui.FAILSAFE = previous
        shared_held.value = False


class DesktopMouse:
    def __init__(self, shared_held):
        import pyautogui
        self.api = pyautogui
        self.held = shared_held
        self.api.PAUSE = 0
        self.api.FAILSAFE = True

    def size(self):
        return self.api.size()

    def position(self):
        return self.api.position()

    def check_failsafe(self):
        self.api.failSafeCheck()

    def moveTo(self, x, y):
        self.api.moveTo(x, y, duration=0, _pause=False)

    def mouseDown(self, button="left"):
        self.held.value = True
        self.api.mouseDown(button=button, _pause=False)

    def mouseUp(self, button="left"):
        emergency_release(self.held)

    def click(self, button="left"):
        self.api.click(button=button, _pause=False)

    def doubleClick(self):
        self.api.doubleClick(interval=0, _pause=False)

    def scroll(self, amount):
        self.api.scroll(amount, _pause=False)

    def hscroll(self, amount):
        # Windows WM_MOUSEHWHEEL equivalent via MOUSEEVENTF_HWHEEL.
        if os.name == "nt":
            ctypes.windll.user32.mouse_event(0x01000, 0, 0, amount*120, 0)
        else:
            self.api.hscroll(amount, _pause=False)


class SystemControls:
    """Slow monitor/COM calls run outside the recognition loop."""
    def __init__(self, warning):
        self.warning = warning
        self.queue = queue.Queue(maxsize=4)
        self.stopping = threading.Event()
        self.disabled = set()
        self.thread = threading.Thread(target=self._run, name="system-controls", daemon=True)
        self.thread.start()

    def submit(self, kind, amount):
        if kind not in self.disabled:
            try:
                self.queue.put_nowait((kind, amount))
            except queue.Full:
                pass

    def _run(self):
        import comtypes
        comtypes.CoInitialize()
        volume = None
        try:
            while not self.stopping.is_set():
                try:
                    kind, amount = self.queue.get(timeout=0.1)
                except queue.Empty:
                    continue
                if self.stopping.is_set() or kind in self.disabled:
                    continue
                try:
                    if kind == "volume":
                        if volume is None:
                            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
                            device = AudioUtilities.GetSpeakers()
                            interface = device.Activate(IAudioEndpointVolume._iid_, comtypes.CLSCTX_ALL, None)
                            volume = ctypes.cast(interface, ctypes.POINTER(IAudioEndpointVolume))
                        value = max(0, min(1, volume.GetMasterVolumeLevelScalar()+amount))
                        volume.SetMasterVolumeLevelScalar(value, None)
                    else:
                        import screen_brightness_control as sbc
                        value = sbc.get_brightness(display=0)[0]
                        sbc.set_brightness(round(max(0, min(100, value+amount*100))), display=0)
                except Exception as exc:
                    self.disabled.add(kind)
                    self.warning(f"{kind.title()} unavailable on this device: {exc}")
        finally:
            volume = None
            comtypes.CoUninitialize()

    def close(self):
        self.stopping.set()
        self.thread.join(timeout=0.5)
