"""Compatibility entry for the camera-only diagnostic."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
if __name__ == "__main__":
    from tools.camera_preview import main
    main()
