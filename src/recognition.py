"""Original gesture encodings with scale-normalized, orientation-aware geometry.

Temporal action validation belongs to Controller, so cursor motion is never
delayed behind an N-frame classifier. No desktop or camera imports are needed.
"""
from enum import IntEnum
from math import acos, degrees, hypot, isfinite


class Gest(IntEnum):
    FIST = 0
    PINKY = 1
    RING = 2
    MID = 4
    LAST3 = 7
    INDEX = 8
    FIRST2 = 12
    LAST4 = 15
    THUMB = 16
    PALM = 31
    V_GEST = 33
    TWO_FINGER_CLOSED = 34
    PINCH_MAJOR = 35
    PINCH_MINOR = 36
    UNKNOWN = 99


class HLabel(IntEnum):
    MINOR = 0
    MAJOR = 1


class HandRecog:
    def __init__(self, hand_label=HLabel.MAJOR):
        self.hand_label = hand_label
        self.hand_result = None
        self.finger = 0
        self._open = [False] * 4
        self._pinching = False
        self._spread = False
        self.aspect = 4 / 3

    def update_hand_result(self, hand_result):
        self.hand_result = hand_result
        if hand_result is None:
            self._open = [False] * 4
            self._pinching = False
            self._spread = False

    def xy(self, index):
        p = self.hand_result.landmark[index]
        return p.x * self.aspect, p.y

    def get_dist(self, points):
        a, b = (self.xy(i) for i in points)
        return hypot(a[0] - b[0], a[1] - b[1])

    def _angle(self, a, b, c):
        a, b, c = self.xy(a), self.xy(b), self.xy(c)
        u, v = (a[0]-b[0], a[1]-b[1]), (c[0]-b[0], c[1]-b[1])
        den = hypot(*u) * hypot(*v)
        if den < 1e-9:
            return 0.0
        return degrees(acos(max(-1.0, min(1.0, (u[0]*v[0]+u[1]*v[1])/den))))

    def valid(self):
        return (self.hand_result is not None
                and len(self.hand_result.landmark) == 21
                and all(isfinite(p.x) and isfinite(p.y) for p in self.hand_result.landmark)
                and self.get_dist((0, 9)) > 0.025)

    def set_finger_state(self):
        if not self.valid():
            self.finger = -1
            return
        self.finger = 0
        for n, base in enumerate((5, 9, 13, 17)):
            # Straightness and distance from wrist work for tilted hands too.
            angle = self._angle(base, base + 1, base + 3)
            reach = self.get_dist((base + 3, 0)) / max(self.get_dist((base + 1, 0)), 1e-6)
            self._open[n] = (angle > (145 if self._open[n] else 158)
                             and reach > (1.04 if self._open[n] else 1.10))
            self.finger = (self.finger << 1) | int(self._open[n])

    def get_gesture(self, profile="full"):
        if not self.valid() or self.finger < 0:
            return Gest.UNKNOWN
        if profile == "simple":
            return {0: Gest.FIST, 8: Gest.INDEX, 12: Gest.FIRST2,
                    15: Gest.PALM}.get(self.finger, Gest.UNKNOWN)
        scale = max(self.get_dist((0, 9)), self.get_dist((5, 17)), 1e-6)
        pinch = self.get_dist((4, 8)) / scale
        # Require the other three fingers; a closed fist must never be a pinch.
        self._pinching = (self.finger in (7, 15)
                          and pinch < (0.38 if self._pinching else 0.27))
        if self._pinching:
            return Gest.PINCH_MINOR if self.hand_label == HLabel.MINOR else Gest.PINCH_MAJOR
        if self.finger == 12:
            spread = self.get_dist((8, 12)) / max(self.get_dist((5, 9)), 1e-6)
            self._spread = spread > (1.55 if self._spread else 1.8)
            return Gest.V_GEST if self._spread else Gest.TWO_FINGER_CLOSED
        if self.finger == 15:
            return Gest.PALM
        return {0: Gest.FIST, 4: Gest.MID, 8: Gest.INDEX}.get(self.finger, Gest.UNKNOWN)
