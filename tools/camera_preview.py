"""Opt-in camera diagnostic: displays frames, never activates mouse control."""
import argparse
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.camera import LatestCamera
from src.config import Settings


def main():
    import cv2
    parser=argparse.ArgumentParser()
    parser.add_argument("--index",type=int,default=0)
    parser.add_argument("--backend",choices=["DSHOW","MSMF","AUTO"],default="DSHOW")
    args=parser.parse_args()
    camera=LatestCamera(Settings(camera_index=args.index,backend=args.backend)).start()
    sequence=0
    try:
        while True:
            packet=camera.read(sequence,timeout=2)
            if packet is None:
                raise RuntimeError("No camera frame within 2 seconds")
            sequence,_,frame=packet
            cv2.imshow("Camera diagnostic - Escape to close",frame)
            if cv2.waitKey(1)&255==27:
                break
    finally:
        camera.close()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
