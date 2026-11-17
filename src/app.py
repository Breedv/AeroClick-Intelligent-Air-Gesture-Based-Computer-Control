"""Native application entry; camera stays off until authenticated Start."""
import logging
import multiprocessing
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    multiprocessing.freeze_support()
    from PySide6.QtCore import QLockFile
    from PySide6.QtWidgets import QApplication, QMessageBox
    from src.auth import data_dir
    from src.ui import MainWindow
    from src.config import TITLE
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName(TITLE)
    lock = QLockFile(str(data_dir()/"application.lock"))
    lock.setStaleLockTime(0)
    if not lock.tryLock(0):
        QMessageBox.information(None, TITLE, "Gesture Control is already open in this Windows user account.")
        return 0
    from logging.handlers import RotatingFileHandler
    logging.basicConfig(level=logging.INFO, handlers=[RotatingFileHandler(data_dir()/"application.log", maxBytes=1_000_000, backupCount=2, encoding="utf-8")],
                        format="%(asctime)s %(levelname)s %(message)s")
    window = MainWindow()
    app.aboutToQuit.connect(window.session.shutdown)
    window.show()
    try:
        return app.exec()
    finally:
        window.session.shutdown()
        lock.unlock()


if __name__ == "__main__":
    raise SystemExit(main())
