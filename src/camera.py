"""One camera owner, latest frame only. No unbounded backlog of stale frames."""
import threading
import time


class CameraError(RuntimeError):
    pass


class LatestCamera:
    def __init__(self, settings, capture_factory=None):
        self.settings = settings
        self.factory = capture_factory
        self._stop = threading.Event()
        self._condition = threading.Condition()
        self._frame = None
        self._sequence = 0
        self._timestamp = 0.0
        self.error = None
        self.thread = None

    def start(self):
        self.thread = threading.Thread(target=self._capture, name="camera", daemon=True)
        self.thread.start()
        return self

    def _capture(self):
        cap = None
        try:
            import cv2
            backend = {"DSHOW": cv2.CAP_DSHOW, "MSMF": cv2.CAP_MSMF,
                       "AUTO": cv2.CAP_ANY}[self.settings.backend]
            cap = (self.factory or cv2.VideoCapture)(self.settings.camera_index, backend)
            if not cap.isOpened():
                raise CameraError("Cannot open camera. Check the index, Windows camera privacy settings, and other apps.")
            for prop, value in ((cv2.CAP_PROP_FRAME_WIDTH, self.settings.width),
                                (cv2.CAP_PROP_FRAME_HEIGHT, self.settings.height),
                                (cv2.CAP_PROP_FPS, self.settings.fps), (cv2.CAP_PROP_BUFFERSIZE, 1)):
                cap.set(prop, value)
            failures = 0
            while not self._stop.is_set():
                ok, frame = cap.read()
                if not ok or frame is None:
                    failures += 1
                    if failures >= 5:
                        raise CameraError("Camera stopped delivering frames. Reconnect it and start again.")
                    self._stop.wait(0.025)
                    continue
                failures = 0
                with self._condition:
                    self._frame = frame
                    self._sequence += 1
                    self._timestamp = time.monotonic()
                    self._condition.notify_all()
        except Exception as exc:
            with self._condition:
                self.error = str(exc)
                self._condition.notify_all()
        finally:
            if cap is not None:
                cap.release()

    def read(self, after=0, timeout=0.10):
        with self._condition:
            self._condition.wait_for(lambda: self._sequence > after or self.error or self._stop.is_set(), timeout)
            if self.error:
                raise CameraError(self.error)
            if self._sequence <= after:
                return None
            return self._sequence, self._timestamp, self._frame

    def close(self):
        self._stop.set()
        with self._condition:
            self._condition.notify_all()
        if self.thread:
            self.thread.join(timeout=0.7)
        # A hung OS driver is contained in the engine process. The UI supervises
        # and terminates that process after its stop timeout, releasing the device.
