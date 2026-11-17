"""Synthetic CPU-only logic timing; excludes camera, inference, IPC and OS input."""
import json
import statistics
import sys
from pathlib import Path
from time import perf_counter_ns
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.recognition import HandRecog
from src.controller import Controller
from tests.helpers import Mouse, hand


def main():
    mouse=Mouse()
    controller=Controller(mouse)
    recognizer=HandRecog()
    poses=[hand(12),hand(0),hand(15),hand(4),hand(8),hand(12,spread=False),hand(7,pinch=True)]
    samples=[]
    for n in range(10500):
        start=perf_counter_ns()
        recognizer.update_hand_result(poses[(n//10)%len(poses)])
        recognizer.set_finger_state()
        gesture=recognizer.get_gesture()
        controller.update(gesture,(.5,.5),n/30,(.5,.5))
        elapsed=(perf_counter_ns()-start)/1e6
        if n>=500: samples.append(elapsed)
    controller.close()
    print(json.dumps({"samples":len(samples), "median_ms":round(statistics.median(samples),4),
                      "p95_ms":round(sorted(samples)[int(len(samples)*.95)],4),
                      "mean_ms":round(statistics.mean(samples),4),
                      "scope":"synthetic landmark classification plus action logic only; recording mouse; no camera/MediaPipe inference/OS input"},indent=2))


if __name__ == "__main__":
    main()
