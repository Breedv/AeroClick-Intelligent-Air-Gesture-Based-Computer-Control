from dataclasses import replace
import random
import pytest
from src.config import Settings
from src.controller import Controller, DragState, CursorFilter
from src.recognition import Gest
from .helpers import Mouse


def settle(c, gesture, start=0.0, point=(0.5, 0.5)):
    for offset in (0, 0.04, 0.08, 0.12, 0.16):
        c.update(gesture, point, start+offset)


def ready(profile="full"):
    mouse = Mouse()
    c = Controller(mouse, replace(Settings(), profile=profile))
    settle(c, Gest.PALM if profile == "simple" else Gest.V_GEST)
    mouse.events.clear()
    return c, mouse


def pick(c, start=1):
    settle(c, Gest.FIST, start)
    assert c.held


def count(mouse, event):
    return sum(e[0] == event for e in mouse.events)


def test_start_requires_neutral_pose():
    c, m = Controller(Mouse()), None
    settle(c, Gest.FIST)
    assert not c.held
    assert c.mouse.events == []


def test_pick_drag_drop_exact_events_and_anchor():
    c, m = ready()
    pick(c)
    assert count(m, "down") == 1
    assert m.xy == pytest.approx((960, 540), abs=2)
    settle(c, Gest.FIST, 1.3, (0.7, 0.65))
    assert m.xy[0] > 1100
    assert count(m, "down") == 1
    assert count(m, "click") == 0
    xy = m.xy
    settle(c, Gest.PALM, 2, (0.9, 0.9))
    assert m.xy == xy  # Opening fingers must not move the drop target.
    assert count(m, "up") == 1
    assert c.state == DragState.IDLE
    c.close()
    c.close()
    assert count(m, "up") == 1


@pytest.mark.parametrize("gesture", [Gest.MID, Gest.INDEX, Gest.TWO_FINGER_CLOSED, Gest.PINCH_MAJOR, Gest.PINCH_MINOR])
def test_other_actions_cannot_interrupt_drag(gesture):
    c, m = ready()
    pick(c)
    settle(c, gesture, 1.3)
    assert c.held
    assert count(m, "up") == count(m, "click") == count(m, "double") == 0


def test_one_wrong_drop_frame_and_release_candidate_reset():
    c, m = ready()
    pick(c)
    c.update(Gest.PALM, (.5, .5), 1.2)
    c.update(Gest.FIST, (.5, .5), 1.23)
    assert c.held
    c.update(Gest.PALM, (.5, .5), 1.4)
    c.update(None, None, 1.45)
    c.update(Gest.PALM, (.5, .5), 1.52)
    assert c.held
    c.update(Gest.PALM, (.5, .5), 1.66)
    assert not c.held
    assert count(m, "up") == 1


def test_short_loss_rebases_without_jump_long_loss_releases_and_requires_neutral():
    c, m = ready()
    pick(c)
    xy = m.xy
    c.update(None, None, 1.25)
    c.update(Gest.FIST, (.85, .85), 1.4)
    assert c.held and m.xy == xy
    c.update(None, None, 1.9)
    assert not c.held and count(m, "up") == 1
    settle(c, Gest.FIST, 2.0)
    assert not c.held
    settle(c, Gest.V_GEST, 2.3)
    pick(c, 2.6)
    c.close()
    assert count(m, "down") == count(m, "up") == 2


def test_candidate_does_not_survive_loss():
    c, m = ready()
    c.update(Gest.FIST, (.5, .5), 1)
    c.update(None, None, 1.05)
    c.update(Gest.FIST, (.5, .5), 1.15)
    assert not c.held


@pytest.mark.parametrize("gesture,event,button", [(Gest.MID,"click","left"), (Gest.INDEX,"click","right"), (Gest.TWO_FINGER_CLOSED,"double",None)])
def test_clicks_are_once_per_arm(gesture,event,button):
    c, m = ready()
    settle(c, gesture, 1)
    settle(c, gesture, 2)
    assert count(m, event) == 1
    if button:
        assert (event, button) in m.events
    settle(c, Gest.V_GEST, 3)
    settle(c, gesture, 4)
    assert count(m, event) == 2


def test_simple_short_fist_click_long_fist_drag():
    c, m = ready("simple")
    c.update(Gest.FIST, (.5, .5), 1)
    c.update(Gest.FIST, (.5, .5), 1.1)
    c.update(Gest.PALM, (.5, .5), 1.15)
    assert count(m, "click") == 1
    assert count(m, "down") == 0
    settle(c, Gest.PALM, 1.3)
    settle(c, Gest.FIST, 2)
    settle(c, Gest.FIST, 2.2)
    assert c.held
    settle(c, Gest.PALM, 2.6)
    assert count(m, "down") == count(m, "up") == 1
    assert count(m, "click") == 1


@pytest.mark.parametrize("horizontal", [True, False])
def test_minor_pinch_scroll(horizontal):
    c, m = ready()
    for t in (1, 1.04, 1.08, 1.12):
        c.update(Gest.PINCH_MINOR, (.5, .5), t, (.5, .5))
    c.update(Gest.PINCH_MINOR, (.5, .5), 1.3, (.6, .5) if horizontal else (.5, .4))
    assert count(m, "hscroll" if horizontal else "scroll") == 1
    c.update(Gest.PINCH_MINOR, (.5, .5), 1.5, (.6, .5) if horizontal else (.5, .4))
    assert count(m, "hscroll" if horizontal else "scroll") == 1


def test_major_pinch_routes_brightness_and_volume():
    class System:
        def __init__(self): self.calls = []
        def submit(self, *args): self.calls.append(args)
    c, m = ready()
    c.system = System()
    for t in (1, 1.04, 1.08, 1.12):
        c.update(Gest.PINCH_MAJOR, (.5,.5), t, (.5,.5))
    c.update(Gest.PINCH_MAJOR, (.5,.5), 1.3, (.65,.5))
    c.update(Gest.PINCH_MAJOR, (.5,.5), 1.5, (.65,.35))
    assert [x[0] for x in c.system.calls] == ["brightness", "volume"]


def test_repeated_drags_and_random_noise_never_duplicate_down_or_up():
    c, m = ready()
    rng = random.Random(72)
    for cycle in range(100):
        start = 1+cycle*3
        pick(c, start)
        for n in range(10):
            c.update(rng.choice([Gest.FIST, Gest.INDEX, Gest.UNKNOWN]), (.5+n*.005, .5), start+.2+n*.02)
        settle(c, Gest.PALM, start+1)
    c.close()
    assert count(m, "down") == count(m, "up") == 100
    assert count(m, "click") == 0


def test_cursor_bounds_filter_jitter_and_fast_response():
    f = CursorFilter((1920,1080))
    assert f.update((-1,2),1) == (1,1078)
    f.reset()
    baseline = f.update((.5,.5),2)
    jitter = f.update((.5001,.5001),2.03)
    assert baseline == jitter
    rapid = f.update((.8,.5),2.06)
    assert rapid[0] > baseline[0]+400
