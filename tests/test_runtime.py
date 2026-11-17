import queue
import threading
import time
from types import SimpleNamespace as NS
import numpy as np
import pytest
from src.camera import LatestCamera, CameraError
from src.config import Settings
from src.engine import run_engine, latest_put
from src.session import EngineSession
from .helpers import Mouse, fake_worker, failed_worker, hanging_worker, held_hanging_worker


class Capture:
    def __init__(self, opened=True, fails=False):
        self.opened, self.fails, self.released, self.n = opened, fails, False, 0
    def isOpened(self): return self.opened
    def set(self, *args): return True
    def read(self):
        time.sleep(.002)
        self.n += 1
        return (False,None) if self.fails else (True,np.full((8,8,3),self.n%255,dtype=np.uint8))
    def release(self): self.released = True


def test_latest_camera_skips_old_frames_and_releases():
    cap=Capture()
    camera=LatestCamera(Settings(),lambda *args:cap).start()
    try:
        first=camera.read(timeout=2)
        assert first
        time.sleep(.04)
        second=camera.read(first[0])
        assert second[0] > first[0]+1
        assert second[2].shape == (8,8,3)
    finally:
        camera.close()
    assert cap.released
    assert not camera.thread.is_alive()


@pytest.mark.parametrize("opened,fails",[(False,False),(True,True)])
def test_camera_open_and_read_errors_release(opened,fails):
    cap=Capture(opened,fails)
    camera=LatestCamera(Settings(),lambda *args:cap).start()
    try:
        with pytest.raises(CameraError):
            for _ in range(30): camera.read(timeout=.1)
    finally:
        camera.close()
    assert cap.released


def test_preview_queue_is_bounded_latest_only():
    q=queue.Queue(1)
    for n in range(100): latest_put(q,n)
    assert q.qsize() == 1 and q.get() == 99


def test_process_repeated_start_stop_and_duplicate_guard(qtbot):
    session=EngineSession(worker=fake_worker)
    states=[]
    session.status.connect(states.append)
    try:
        for _ in range(3):
            assert session.start(Settings())
            assert not session.start(Settings())
            qtbot.waitUntil(lambda: states[-1] == "Running",timeout=15000)
            session.stop()
            qtbot.waitUntil(lambda: not session.active,timeout=6000)
            assert states[-1] == "Ready"
    finally:
        session.shutdown()


def test_camera_error_is_surfaced_and_allows_restart(qtbot):
    session=EngineSession(worker=failed_worker)
    states,messages=[],[]
    session.status.connect(states.append)
    session.message.connect(messages.append)
    try:
        session.start(Settings())
        qtbot.waitUntil(lambda: not session.active,timeout=15000)
        assert states[-1] == "Camera Error"
        assert "Synthetic camera unavailable" in messages
    finally:
        session.shutdown()


def test_hung_worker_stop_timeout(qtbot):
    session=EngineSession(worker=hanging_worker)
    try:
        session.start(Settings())
        session.stop()
        session.stopping_at=time.monotonic()-3.2
        qtbot.waitUntil(lambda: not session.active,timeout=6000)
    finally:
        session.shutdown()


def test_forced_exit_releases_shared_hold_without_orphaned_mutex(qtbot,monkeypatch):
    released=[]
    def release(shared):
        released.append(bool(shared.value))
        shared.value=False
    monkeypatch.setattr("src.session.emergency_release",release)
    session=EngineSession(worker=held_hanging_worker)
    states=[]
    session.status.connect(states.append)
    try:
        assert not hasattr(session.held,"get_lock")
        session.start(Settings())
        qtbot.waitUntil(lambda:states[-1]=="Running",timeout=15000)
        session.stop()
        session.stopping_at=time.monotonic()-3.2
        qtbot.waitUntil(lambda:not session.active,timeout=6000)
        assert released==[True]
        assert not session.held.value
    finally:
        session.shutdown()


def test_real_mediapipe_model_initializes_and_processes_blank_frame():
    import mediapipe as mp
    with mp.solutions.hands.Hands(max_num_hands=2,model_complexity=1) as model:
        result=model.process(np.zeros((480,640,3),dtype=np.uint8))
        assert not result.multi_hand_landmarks


def test_real_aruco_detector_blank_and_generated_marker():
    import cv2
    from src.Gesture_Controller_Gloved import Marker
    marker=Marker()
    marker.detect(np.full((400,400,3),255,dtype=np.uint8))
    assert not marker.is_detected()
    target=np.full((400,400),255,dtype=np.uint8)
    target[100:300,100:300]=cv2.aruco.generateImageMarker(marker.aruco_dict,0,200)
    marker.detect(cv2.cvtColor(target,cv2.COLOR_GRAY2BGR))
    assert marker.is_detected()


def test_engine_model_exception_closes_camera_and_tracker(monkeypatch):
    import multiprocessing
    import mediapipe as mp
    import src.engine as engine
    import src.desktop as desktop
    class Frames(queue.Queue):
        def cancel_join_thread(self): pass
    class Cam:
        closed=False
        def __init__(self,*args): pass
        def start(self): return self
        def read(self,*args): return 1,time.monotonic(),np.zeros((480,640,3),np.uint8)
        def close(self): Cam.closed=True
    class Tracker:
        closed=False
        def __init__(self,**kwargs): pass
        def process(self,frame): raise RuntimeError("inference failed")
        def close(self): Tracker.closed=True
    class Controls:
        closed=False
        def __init__(self,*args): pass
        def close(self): Controls.closed=True
    m=Mouse()
    monkeypatch.setattr(engine,"LatestCamera",Cam)
    monkeypatch.setattr(mp.solutions.hands,"Hands",Tracker)
    monkeypatch.setattr(desktop,"DesktopMouse",lambda held:m)
    monkeypatch.setattr(desktop,"SystemControls",Controls)
    ctx=multiprocessing.get_context("spawn")
    events=queue.Queue()
    engine.run_engine(Settings(),threading.Event(),Frames(1),events,ctx.Value("b",False),ctx.Value("d",time.monotonic()))
    assert Cam.closed and Tracker.closed and Controls.closed
    assert any(k=="error" and "inference failed" in value for k,value in list(events.queue))
