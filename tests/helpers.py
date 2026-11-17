from types import SimpleNamespace as NS
from math import cos, sin, radians
import time


class Mouse:
    def __init__(self):
        self.events = []
        self.xy = (960, 540)

    def size(self):
        return 1920, 1080

    def position(self):
        return self.xy

    def check_failsafe(self):
        pass

    def moveTo(self, x, y):
        self.xy = x, y
        self.events.append(("move", x, y))

    def mouseDown(self, button="left"):
        self.events.append(("down", button))

    def mouseUp(self, button="left"):
        self.events.append(("up", button))

    def click(self, button="left"):
        self.events.append(("click", button))

    def doubleClick(self):
        self.events.append(("double",))

    def scroll(self, amount):
        self.events.append(("scroll", amount))

    def hscroll(self, amount):
        self.events.append(("hscroll", amount))


def hand(mask=15, spread=True, pinch=False, scale=1.0, angle=0):
    points = [NS(x=0.5, y=0.85, z=0.0) for _ in range(21)]
    points[4] = NS(x=0.25, y=0.66, z=0.0)
    for n, base in enumerate((5, 9, 13, 17)):
        x = 0.40+n*0.065
        points[base] = NS(x=x, y=0.65, z=0.0)
        if mask & (8 >> n):
            target_x = x
            if mask == 12:
                target_x = ((0.35, 0.53) if spread else (0.45, 0.47))[n] if n < 2 else x
            for k, y in ((1, 0.53), (2, 0.43), (3, 0.33)):
                ratio = (0.65-y)/0.32
                points[base+k] = NS(x=x+(target_x-x)*ratio, y=y, z=0.0)
        else:
            for k, y in ((1, 0.58), (2, 0.66), (3, 0.73)):
                points[base+k] = NS(x=x, y=y, z=0.0)
    if pinch:
        points[4] = NS(x=points[8].x+0.02, y=points[8].y, z=0.0)
    c, s = cos(radians(angle)), sin(radians(angle))
    for p in points:
        dx, dy = (p.x-0.5)*4/3, p.y-0.85
        p.x = 0.5+scale*(c*dx-s*dy)/(4/3)
        p.y = 0.85+scale*(s*dx+c*dy)
    return NS(landmark=points)


def fake_worker(settings, stop, frames, events, held, heartbeat):
    events.put(("state", "Running"))
    while not stop.wait(0.02):
        pass
    events.put(("stopped", ""))


def failed_worker(settings, stop, frames, events, held, heartbeat):
    events.put(("camera_error", "Synthetic camera unavailable"))


def hanging_worker(settings, stop, frames, events, held, heartbeat):
    while True:
        time.sleep(0.1)


def held_hanging_worker(settings, stop, frames, events, held, heartbeat):
    # Shared state only: no OS mouse injection in any test.
    held.value = True
    events.put(("state", "Running"))
    while True:
        time.sleep(0.1)
