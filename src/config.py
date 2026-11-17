from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    camera_index: int = 0
    backend: str = "DSHOW"
    dominant_hand: str = "Right"
    profile: str = "full"
    mode: str = "hands"
    width: int = 640
    height: int = 480
    fps: int = 30
    preview_fps: int = 15
    detection_confidence: float = 0.6
    tracking_confidence: float = 0.6
    pick_seconds: float = 0.09
    release_seconds: float = 0.12
    action_seconds: float = 0.08
    tracking_grace: float = 0.45
    simple_hold_seconds: float = 0.30
    active_margin: float = 0.08


TITLE = "Gesture Control Recognition System"
