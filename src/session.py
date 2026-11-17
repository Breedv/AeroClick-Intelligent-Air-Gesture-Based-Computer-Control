"""Qt-side lifecycle: one process, stop deadline, crash recovery, shared release."""
import multiprocessing as mp
import queue
import time
from PySide6.QtCore import QObject, QTimer, Signal
from .engine import run_engine
from .desktop import emergency_release


class EngineSession(QObject):
    status = Signal(str)
    preview = Signal(dict)
    message = Signal(str)
    finished = Signal()

    def __init__(self, parent=None, worker=run_engine):
        super().__init__(parent)
        self.worker = worker
        self.ctx = mp.get_context("spawn")
        self.process = None
        self.held = self.ctx.RawValue("b", False)
        self.timer = QTimer(self)
        self.timer.setInterval(33)
        self.timer.timeout.connect(self.poll)
        self.stopping_at = None
        self.error_state = None
        self.last_packet = 0.0

    @property
    def active(self):
        return self.process is not None

    def start(self, settings):
        if self.active:
            return False
        self.stop_event = self.ctx.Event()
        self.frames, self.events = self.ctx.Queue(maxsize=1), self.ctx.Queue()
        self.heartbeat = self.ctx.Value("d", time.monotonic())
        self.error_state = self.stopping_at = None
        self.last_packet = self.started_at = time.monotonic()
        self.process = self.ctx.Process(target=self.worker,
            args=(settings, self.stop_event, self.frames, self.events, self.held, self.heartbeat), daemon=True)
        self.status.emit("Starting")
        try:
            self.process.start()
        except Exception as exc:
            self.process.close()
            self.process = None
            for channel in (self.frames, self.events):
                channel.close()
            self.status.emit("Error")
            self.message.emit(str(exc))
            self.finished.emit()
            return False
        self.timer.start()
        return True

    def stop(self):
        if self.active and self.stopping_at is None:
            self.stopping_at = time.monotonic()
            self.stop_event.set()
            self.status.emit("Stopping")

    def poll(self):
        if not self.active:
            return
        now = time.monotonic()
        self.heartbeat.value = now
        while True:
            try:
                kind, value = self.events.get_nowait()
            except queue.Empty:
                break
            if kind == "state" and self.stopping_at is None:
                self.status.emit(value)
            elif kind in ("error", "camera_error"):
                self.error_state = "Camera Error" if kind == "camera_error" else "Error"
                self.message.emit(value)
                self.stop()
            elif kind == "warning":
                self.message.emit(value)
        try:
            packet = self.frames.get_nowait()
        except queue.Empty:
            packet = None
        if packet:
            self.last_packet = now
            self.preview.emit(packet)
        limit = 15 if self.last_packet == self.started_at else 2.0
        if self.stopping_at is None and now-self.last_packet > limit:
            self.error_state = "Camera Error"
            self.message.emit("Engine stopped responding. Camera and mouse control are being released.")
            self.stop()
        if self.stopping_at is not None and now-self.stopping_at > 3.0 and self.process.is_alive():
            self.process.terminate()
        if not self.process.is_alive():
            self.process.join(timeout=0)
            if self.process.exitcode and self.error_state is None and self.stopping_at is None:
                self.error_state = "Error"
                self.message.emit(f"Engine exited unexpectedly (code {self.process.exitcode}).")
            emergency_release(self.held)
            self.process.close()
            self.process = None
            for channel in (self.frames, self.events):
                channel.close()
                channel.cancel_join_thread()
            self.timer.stop()
            self.status.emit(self.error_state or "Ready")
            self.finished.emit()

    def shutdown(self):
        # Final process teardown only, after the Qt event loop has stopped.
        if self.active:
            self.stop_event.set()
            self.process.join(timeout=1)
            if self.process.is_alive():
                self.process.terminate()
                self.process.join(timeout=1)
            emergency_release(self.held)
            self.process.close()
            self.process = None
