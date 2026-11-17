import pytest
from PySide6.QtCore import QObject, Signal, QTimer, Qt
from PySide6.QtWidgets import QLineEdit
from src.auth import AuthStore
from src.ui import MainWindow


class FakeSession(QObject):
    status=Signal(str)
    preview=Signal(dict)
    message=Signal(str)
    finished=Signal()
    def __init__(self):
        super().__init__()
        self.active=False
        self.starts=0
    def start(self,settings):
        if self.active: return False
        self.active=True
        self.starts+=1
        self.status.emit("Starting")
        QTimer.singleShot(10,lambda:self.status.emit("Running") if self.active else None)
        return True
    def stop(self):
        if self.active:
            self.status.emit("Stopping")
            QTimer.singleShot(20,self.finish)
    def finish(self):
        self.active=False
        self.status.emit("Ready")
        self.finished.emit()
    def shutdown(self): self.active=False


@pytest.fixture
def window(qtbot,tmp_path):
    w=MainWindow(AuthStore(tmp_path/"users.db"),FakeSession())
    qtbot.addWidget(w)
    w.show()
    yield w
    w.session.shutdown()
    for job in (w.auth_job,w.voice_job,w.speech_job):
        if job: job.wait(5000)


def register(w,qtbot):
    qtbot.mouseClick(w.mode_button,Qt.MouseButton.LeftButton)
    w.user_field.setText("Tester")
    w.password_field.setText("a-test-password")
    w.confirm_field.setText("a-test-password")
    qtbot.mouseClick(w.login_button,Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda:w.username is not None,timeout=10000)
    qtbot.waitUntil(lambda:not w.auth_job.isRunning(),timeout=10000)


def test_login_registration_start_stop_logout(window,qtbot):
    w=window
    assert w.stack.currentWidget() is w.login_page
    w.start_control()
    assert w.session.starts==0
    register(w,qtbot)
    assert w.stack.currentWidget() is w.dashboard
    assert not w.password_field.text()
    for _ in range(3):
        qtbot.mouseClick(w.start_button,Qt.MouseButton.LeftButton)
        qtbot.waitUntil(lambda:w.status_badge.text()=="Running")
        assert not w.start_button.isEnabled()
        assert not w.profile.isEnabled()
        qtbot.mouseClick(w.stop_button,Qt.MouseButton.LeftButton)
        qtbot.waitUntil(lambda:w.status_badge.text()=="Ready")
    qtbot.mouseClick(w.start_button,Qt.MouseButton.LeftButton)
    qtbot.mouseClick(w.logout_button,Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda:w.username is None)
    assert not w.session.active
    assert w.stack.currentWidget() is w.login_page


def test_invalid_password_then_valid_login(window,qtbot):
    w=window
    register(w,qtbot)
    w.logout()
    w.user_field.setText("Tester")
    w.password_field.setText("wrong-password")
    w.authenticate()
    qtbot.waitUntil(lambda:"Invalid" in w.auth_error.text(),timeout=10000)
    assert w.username is None
    qtbot.waitUntil(lambda:w.login_button.isEnabled(),timeout=3000)
    w.password_field.setText("a-test-password")
    w.authenticate()
    qtbot.waitUntil(lambda:w.username=="Tester",timeout=10000)


def test_password_visibility_mismatch_and_required_fields(window,qtbot):
    w=window
    w.authenticate()
    assert "Enter" in w.auth_error.text()
    w.show_password.setChecked(True)
    assert w.password_field.echoMode()==QLineEdit.EchoMode.Normal
    w.set_register(True)
    w.user_field.setText("Tester")
    w.password_field.setText("a-test-password")
    w.confirm_field.setText("different-pass")
    w.authenticate()
    assert "match" in w.auth_error.text()
    assert not w.auth.has_users()


def test_close_during_active_session_stops_before_exit(window,qtbot):
    w=window
    register(w,qtbot)
    w.start_control()
    w.close()
    assert w.pending=="close"
    qtbot.waitUntil(lambda:not w.isVisible(),timeout=3000)
    assert not w.session.active


def test_proton_routes_start_stop(window,qtbot):
    w=window
    register(w,qtbot)
    w.open_proton()
    w.command_field.setText("Proton launch gesture recognition")
    w.send_command()
    assert w.session.active
    w.command_field.setText("Proton stop gesture recognition")
    w.send_command()
    qtbot.waitUntil(lambda:not w.session.active)
    assert "Stopping" in w.conversation.toPlainText()
