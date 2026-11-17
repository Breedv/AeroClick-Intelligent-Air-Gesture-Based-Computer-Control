"""Camera-free dependency/model check. Does not move the mouse or record audio."""
import importlib
import importlib.metadata
import platform
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    print("Python:", sys.version.split()[0], platform.architecture()[0], platform.system())
    for name in ("numpy", "cv2", "mediapipe", "PySide6", "pyautogui", "pycaw.pycaw"):
        module = importlib.import_module(name)
        print(name, getattr(module, "__version__", "OK"))
    # Importing this package immediately connects to Windows WMI. Verify its
    # installation separately from device permission/availability.
    print("screen-brightness-control", importlib.metadata.version("screen-brightness-control"))
    try:
        importlib.import_module("screen_brightness_control")
    except ModuleNotFoundError:
        raise
    except Exception as exc:
        print("DEVICE CHECK DEFERRED: Windows brightness/WMI access:", exc)
    import cv2
    import numpy as np
    import mediapipe as mp
    with mp.solutions.hands.Hands(max_num_hands=2) as hands:
        result = hands.process(np.zeros((480,640,3), dtype=np.uint8))
        assert not result.multi_hand_landmarks
    assert hasattr(cv2.aruco, "ArucoDetector")
    print("PASS: core imports, installed packages, MediaPipe model, and ArUco API.")
    print("Physical webcam, desktop mouse actions, volume and brightness changes are not tested by this command.")


if __name__ == "__main__":
    main()
