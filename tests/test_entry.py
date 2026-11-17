import os
import subprocess
import sys
from pathlib import Path
from PySide6.QtCore import QLockFile
from src.config import TITLE


def test_application_lock_rejects_second_instance(qapp,tmp_path,monkeypatch):
    monkeypatch.setenv("GESTURE_CONTROL_DATA_DIR",str(tmp_path))
    lock=QLockFile(str(tmp_path/"application.lock"))
    assert lock.tryLock(0)
    notices=[]
    monkeypatch.setattr("PySide6.QtWidgets.QMessageBox.information",lambda *args:notices.append(args))
    try:
        from src.app import main
        assert main()==0
        assert notices and "already open" in notices[0][-1]
    finally:
        lock.unlock()


def test_real_entry_point_opens_login_and_closes_cleanly(tmp_path):
    root=Path(__file__).resolve().parents[1]
    script="""
import runpy
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtCore import QTimer
app=QApplication([])
def verify_and_close():
    windows=[w for w in app.topLevelWidgets() if isinstance(w,QMainWindow)]
    assert len(windows)==1
    w=windows[0]
    assert w.stack.currentWidget() is w.login_page
    assert not w.session.active
    print('LOGIN_VISIBLE_CAMERA_OFF',flush=True)
    w.close()
QTimer.singleShot(1000,verify_and_close)
runpy.run_path('main.py',run_name='__main__')
"""
    env=dict(os.environ,QT_QPA_PLATFORM="offscreen",GESTURE_CONTROL_DATA_DIR=str(tmp_path))
    for _ in range(2):
        result=subprocess.run([sys.executable,"-c",script],cwd=root,env=env,capture_output=True,text=True,timeout=20)
        assert result.returncode==0,result.stdout+result.stderr
        assert "LOGIN_VISIBLE_CAMERA_OFF" in result.stdout
