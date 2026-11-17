import pytest
from types import SimpleNamespace as NS
from src.recognition import HandRecog, HLabel, Gest
from src.engine import select_hands
from .helpers import hand


@pytest.mark.parametrize("mask,expected", [(0,Gest.FIST),(4,Gest.MID),(8,Gest.INDEX),(15,Gest.PALM),(12,Gest.V_GEST),(1,Gest.UNKNOWN)])
@pytest.mark.parametrize("scale,angle", [(1,0),(.65,25),(1.2,-35)])
def test_geometry_and_scale_rotation_invariance(mask, expected, scale, angle):
    r = HandRecog()
    r.update_hand_result(hand(mask,scale=scale,angle=angle))
    r.set_finger_state()
    assert r.get_gesture() == expected


def test_closed_two_fingers_and_simple_bitmask():
    r = HandRecog()
    r.update_hand_result(hand(12, spread=False))
    r.set_finger_state()
    assert r.finger == 12
    assert r.get_gesture() == Gest.TWO_FINGER_CLOSED
    assert r.get_gesture("simple") == Gest.FIRST2
    r.update_hand_result(hand(8))
    r.set_finger_state()
    assert r.get_gesture("simple") == Gest.INDEX
    r.update_hand_result(hand(1))
    r.set_finger_state()
    assert r.get_gesture("simple") == Gest.UNKNOWN


@pytest.mark.parametrize("role,expected", [(HLabel.MAJOR,Gest.PINCH_MAJOR),(HLabel.MINOR,Gest.PINCH_MINOR)])
def test_pinch_hand_role(role,expected):
    r=HandRecog(role)
    r.update_hand_result(hand(7,pinch=True))
    r.set_finger_state()
    assert r.get_gesture() == expected


def test_degenerate_and_missing_landmarks_are_unknown():
    r=HandRecog()
    r.set_finger_state()
    assert r.get_gesture() == Gest.UNKNOWN
    r.update_hand_result(hand(scale=0))
    r.set_finger_state()
    assert r.get_gesture() == Gest.UNKNOWN
    r.update_hand_result(hand())
    r.hand_result.landmark[8].x=float("nan")
    r.set_finger_state()
    assert r.get_gesture() == Gest.UNKNOWN


def test_hand_roles_never_fall_back_to_other_hand():
    left, right = hand(), hand()
    result = NS(multi_hand_landmarks=[left],multi_handedness=[NS(classification=[NS(label="Left",score=.99)])])
    assert select_hands(result,"Right") == (None,left)
    assert select_hands(result,"Left") == (left,None)
    result.multi_hand_landmarks.append(right)
    result.multi_handedness.append(NS(classification=[NS(label="Right",score=.99)]))
    assert select_hands(result,"Right") == (right,left)
