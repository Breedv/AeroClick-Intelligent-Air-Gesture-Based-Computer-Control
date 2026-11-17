"""Compatibility entry; camera ownership now belongs to the dashboard."""
import sys
from pathlib import Path
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.recognition import Gest, HLabel, HandRecog
from src.controller import Controller
from src.session import EngineSession as GestureController


def main():
    from src.app import main as launch
    return launch()


if __name__ == "__main__":
    raise SystemExit(main())
