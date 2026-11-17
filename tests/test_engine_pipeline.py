"""Full frame -> landmark -> gesture -> action pipeline with synthetic input."""
import multiprocessing
import queue
import threading
import time
from types import SimpleNamespace as NS
import numpy as np
import pytest
from src.config import Settings
from src.camera import CameraError
from .helpers import Mouse, hand


@pytest.mark.parametrize("drop",[True,False])
def test_frame_pipeline_drag_and_error_cleanup(monkeypatch,drop):
    import src.engine as engine
    import src.desktop as desktop
    import mediapipe as mp
    poses=[hand(12) for _ in range(5)]+[hand(0) for _ in range(6)]
    for n in range(5):
        h=hand(0)
        for p in h.landmark: p.x+=.02*n
        poses.append(h)
    if drop:
        poses += [hand(15) for _ in range(6)]
    class Frames(queue.Queue):
        def cancel_join_thread(self): pass
    class Cam:
        closed=False
        def __init__(self,*args): self.i=0
        def start(self): return self
        def read(self,*args):
            if self.i>=len(poses): raise CameraError("synthetic disconnection")
            self.i+=1
            time.sleep(.045)
            return self.i,time.monotonic(),np.zeros((480,640,3),np.uint8)
        def close(self): Cam.closed=True
    class Tracker:
        def __init__(self,**kwargs): self.i=0
        def process(self,frame):
            h=poses[self.i]
            self.i+=1
            return NS(multi_hand_landmarks=[h],multi_handedness=[NS(classification=[NS(label="Right",score=.99)])])
        def close(self): pass
    class Controls:
        def __init__(self,*args): pass
        def close(self): pass
    mouse=Mouse()
    monkeypatch.setattr(engine,"LatestCamera",Cam)
    monkeypatch.setattr(mp.solutions.hands,"Hands",Tracker)
    monkeypatch.setattr(mp.solutions.drawing_utils,"draw_landmarks",lambda *args:None)
    monkeypatch.setattr(desktop,"DesktopMouse",lambda held:mouse)
    monkeypatch.setattr(desktop,"SystemControls",Controls)
    ctx=multiprocessing.get_context("spawn")
    engine.run_engine(Settings(),threading.Event(),Frames(1),queue.Queue(),ctx.Value("b",False),ctx.Value("d",time.monotonic()))
    assert Cam.closed
    assert [e[0] for e in mouse.events].count("down")==1
    assert [e[0] for e in mouse.events].count("up")==1
    assert [e[0] for e in mouse.events].count("click")==0
    assert mouse.xy[0]>1000
