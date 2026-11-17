import sys
import threading
from types import SimpleNamespace as NS
from src.desktop import SystemControls, DesktopMouse


def test_slow_system_controls_off_thread_and_disable_failed_device(monkeypatch):
    calls=[]
    warnings=[]
    completed=threading.Event()
    def failed_brightness(**kwargs):
        calls.append(threading.current_thread().name)
        raise PermissionError("synthetic WMI denial")
    monkeypatch.setitem(sys.modules,"screen_brightness_control",NS(get_brightness=failed_brightness))
    monkeypatch.setitem(sys.modules,"comtypes",NS(CoInitialize=lambda:None,CoUninitialize=lambda:None))
    controls=SystemControls(lambda msg:(warnings.append(msg),completed.set()))
    try:
        controls.submit("brightness",.03)
        assert completed.wait(3)
        controls.submit("brightness",.03)
    finally:
        controls.close()
    assert calls == ["system-controls"]
    assert len(warnings)==1 and "synthetic WMI denial" in warnings[0]
    assert "brightness" in controls.disabled
    assert not controls.thread.is_alive()


def test_mouse_adapter_marks_held_before_down_and_keeps_failsafe(monkeypatch):
    import multiprocessing
    events=[]
    held=multiprocessing.get_context("spawn").Value("b",False)
    fake=NS(PAUSE=.1,FAILSAFE=False,size=lambda:(1920,1080),position=lambda:(500,500),
            mouseDown=lambda **kwargs:events.append(("down",held.value)),
            moveTo=lambda *args,**kwargs:events.append(("move",kwargs)),
            failSafeCheck=lambda:events.append(("check",)))
    monkeypatch.setitem(sys.modules,"pyautogui",fake)
    def release(shared):
        events.append(("up",shared.value))
        shared.value=False
    monkeypatch.setattr("src.desktop.emergency_release",release)
    mouse=DesktopMouse(held)
    mouse.check_failsafe()
    mouse.mouseDown()
    mouse.moveTo(100,100)
    mouse.mouseUp()
    assert fake.FAILSAFE and fake.PAUSE==0
    assert ("down",1) in events and ("up",1) in events
    assert not held.value
    assert events[2][1]["duration"]==0
