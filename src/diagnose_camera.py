"""Compatibility entry for dependency validation and optional camera preview."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
if __name__ == "__main__":
    from tools.check_install import main
    main()
    print("To test the webcam separately: python tools/camera_preview.py --index 0 --backend DSHOW")
