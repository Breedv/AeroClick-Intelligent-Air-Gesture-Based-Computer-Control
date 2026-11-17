"""Nonblocking mouse actions and explicit drag lifecycle. All times are monotonic."""
from enum import Enum
from math import exp, hypot
from .config import Settings
from .recognition import Gest


class DragState(str, Enum):
    IDLE = "IDLE"
    PICK_CANDIDATE = "PICK_CANDIDATE"
    DRAGGING = "DRAGGING"
    RELEASE_CANDIDATE = "RELEASE_CANDIDATE"


class CursorFilter:
    def __init__(self, size, margin=0.08):
        self.width, self.height = size
        self.margin = margin
        self.value = None
        self.last_time = None
        self.offset = (0, 0)

    def reset(self):
        self.value = self.last_time = None

    def target(self, point):
        m = self.margin
        return tuple((p-m)/(1-2*m)*(s-1)
                     for p, s in zip(point, (self.width, self.height)))

    def anchor(self, point, cursor):
        target = self.target(point)
        self.offset = tuple(c-t for c, t in zip(cursor, target))
        self.value = tuple(cursor)
        self.last_time = None

    def update(self, point, now):
        raw = self.target(point)
        # Clamp after the anchor offset, so a shifted origin can still reach
        # screen edges. Inset one pixel for the physical corner emergency stop.
        target = tuple(max(1, min(s-2, p+o)) for p, o, s in
                       zip(raw, self.offset, (self.width, self.height)))
        if self.value is None:
            self.value = target
        else:
            distance = hypot(target[0]-self.value[0], target[1]-self.value[1])
            dt = min(0.08, max(0.001, now-(self.last_time or now-1/30)))
            # Faster motion gets less filtering. Time-based, not FPS dependent.
            tau = 0.055 if distance < 12 else 0.018
            alpha = 1-exp(-dt/tau)
            if distance >= 1.2:
                self.value = tuple(v+alpha*(t-v) for v, t in zip(self.value, target))
        self.last_time = now
        return tuple(round(v) for v in self.value)


class Controller:
    def __init__(self, mouse, settings=None, system=None):
        self.mouse = mouse
        self.settings = settings or Settings()
        self.system = system
        self.cursor = CursorFilter(mouse.size(), self.settings.active_margin)
        self.state = DragState.IDLE
        self.held = False
        self.armed = False
        self.candidate_since = 0.0
        self.last_seen = None
        self.missing = False
        self.need_neutral = True
        self.stable_gesture = None
        self.stable_since = 0.0
        self.stable_frames = 0
        self.pinch_origin = None
        self.pinch_kind = None
        self.last_pinch_action = -1.0
        self.last_move = None

    def _move(self, point, now):
        if point is None:
            return
        xy = self.cursor.update(point, now)
        if xy != self.last_move:
            self.mouse.moveTo(*xy)
            self.last_move = xy

    def _release(self):
        if self.held:
            self.mouse.mouseUp(button="left")
            self.held = False
        self.state = DragState.IDLE
        self.armed = False
        self.cursor.offset = (0, 0)

    def close(self):
        self._release()
        self.need_neutral = True
        self.pinch_origin = self.pinch_kind = None

    def _stable(self, gesture, now, seconds):
        if gesture != self.stable_gesture:
            self.stable_gesture, self.stable_since, self.stable_frames = gesture, now, 1
        else:
            self.stable_frames += 1
        return self.stable_frames >= 2 and now-self.stable_since >= seconds-1e-9

    def update(self, gesture, point, now, pinch_point=None):
        if gesture is None or gesture == Gest.UNKNOWN:
            # Unknown observations cannot release a drag or accumulate debounce.
            self.stable_gesture = None
            self.pinch_origin = self.pinch_kind = None
            self.missing = True
            if self.state == DragState.PICK_CANDIDATE:
                self.state = DragState.IDLE
            if self.state == DragState.RELEASE_CANDIDATE:
                self.state = DragState.DRAGGING
            if self.last_seen is not None and now-self.last_seen >= self.settings.tracking_grace:
                self.close()
                self.cursor.reset()
            return
        # Reacquisition rebases at the current cursor instead of jumping.
        if self.missing and point is not None:
            self.cursor.anchor(point, self.mouse.position())
            self.missing = False
        self.last_seen = now
        stable = self._stable(gesture, now, self.settings.action_seconds)
        movers = (Gest.PALM,) if self.settings.profile == "simple" else (Gest.V_GEST,)
        neutral = gesture in (Gest.PALM, Gest.V_GEST)
        if self.need_neutral:
            if neutral and stable:
                self.need_neutral = False
            else:
                return
        if self.held:
            # Only an intentional neutral/move pose drops. Click/pinch glitches
            # never steal ownership or fire an action during a drag.
            if neutral:
                if self.state != DragState.RELEASE_CANDIDATE:
                    self.state = DragState.RELEASE_CANDIDATE
                    self.candidate_since = now
                if now-self.candidate_since >= self.settings.release_seconds-1e-9 and self.stable_frames >= 2:
                    self._release()
                    self.need_neutral = False
                return  # Freeze at the intended drop position while opening hand.
            self.state = DragState.DRAGGING
            if gesture == Gest.FIST:
                self._move(point, now)
            return
        if gesture == Gest.FIST:
            if self.state != DragState.PICK_CANDIDATE:
                self.state = DragState.PICK_CANDIDATE
                self.candidate_since = now
            delay = (self.settings.simple_hold_seconds if self.settings.profile == "simple"
                     else self.settings.pick_seconds)
            if now-self.candidate_since >= delay-1e-9 and self.stable_frames >= 2:
                # Preserve hover location as fingers close; palm-base movement
                # after the pick controls drag displacement.
                if point is not None:
                    self.cursor.anchor(point, self.mouse.position())
                self.held = True
                self.mouse.mouseDown(button="left")
                self.state = DragState.DRAGGING
                self.armed = False
            return
        if self.state == DragState.PICK_CANDIDATE:
            held_for = now-self.candidate_since
            self.state = DragState.IDLE
            if (self.settings.profile == "simple" and neutral
                    and held_for >= self.settings.action_seconds):
                self.mouse.click()
                self.armed = False
        if gesture in movers:
            self._move(point, now)
            if stable:
                self.armed = True
        clicks = ({Gest.INDEX: "right", Gest.FIRST2: "double"}
                  if self.settings.profile == "simple" else
                  {Gest.MID: "left", Gest.INDEX: "right", Gest.TWO_FINGER_CLOSED: "double"})
        if stable and self.armed and gesture in clicks:
            action = clicks[gesture]
            if action == "double":
                self.mouse.doubleClick()
            else:
                self.mouse.click(button=action)
            self.armed = False
        if gesture in (Gest.PINCH_MAJOR, Gest.PINCH_MINOR) and stable and pinch_point:
            self._pinch(gesture, pinch_point, now)
        else:
            self.pinch_origin = self.pinch_kind = None

    def _pinch(self, gesture, point, now):
        if self.pinch_kind != gesture:
            self.pinch_kind, self.pinch_origin = gesture, point
            return
        dx, dy = point[0]-self.pinch_origin[0], self.pinch_origin[1]-point[1]
        horizontal = abs(dx) > abs(dy)
        delta = dx if horizontal else dy
        if abs(delta) < 0.025 or now-self.last_pinch_action < 0.10:
            return
        amount = max(-6, min(6, int(delta/0.025)))
        if gesture == Gest.PINCH_MINOR:
            (self.mouse.hscroll if horizontal else self.mouse.scroll)(amount)
        elif self.system:
            self.system.submit("brightness" if horizontal else "volume", amount*0.03)
        self.last_pinch_action = now
        self.pinch_origin = point
