from dataclasses import replace
import logging
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QImage, QPixmap, QKeySequence, QShortcut
from PySide6.QtWidgets import (QMainWindow, QWidget, QLabel, QPushButton, QLineEdit,
    QVBoxLayout, QHBoxLayout, QFormLayout, QFrame, QStackedWidget, QCheckBox,
    QComboBox, QSpinBox, QTextEdit, QDialog, QScrollArea)
from .auth import AuthStore
from .config import Settings, TITLE
from .session import EngineSession
from .Proton import Proton


STYLE = """
QWidget { background: #0c1020; color: #eef0fc; font-family: 'Segoe UI'; font-size: 13px; }
QFrame#card { background: #151b2f; border: 1px solid #29324e; border-radius: 16px; }
QFrame#brand { background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #262d6a,stop:1 #15182f); border-radius: 20px; }
QLabel { background: transparent; border: none; }
QLabel#title { font-size: 27px; font-weight: 650; }
QLabel#subtitle { color: #aab3d0; font-size: 14px; }
QLabel#eyebrow { color: #a2a8ff; font-size: 11px; font-weight: 700; }
QLabel#error { color: #ffb1ba; }
QLabel#status { background: #232d48; border-radius: 13px; padding: 7px 15px; color: #b9c7ff; }
QLineEdit, QComboBox, QSpinBox { background: #0e1426; border: 1px solid #343d5b; border-radius: 9px; padding: 10px; min-height: 20px; }
QLineEdit:focus, QComboBox:focus, QSpinBox:focus { border: 1px solid #8c8fff; }
QComboBox, QSpinBox { padding: 5px 9px; min-height: 17px; }
QComboBox QAbstractItemView { background: #151b2f; selection-background-color: #454c8c; }
QPushButton { background: #252e49; border: 1px solid #394566; border-radius: 9px; padding: 11px 17px; font-weight: 600; }
QPushButton:hover { background: #354166; border-color: #6c78ad; }
QPushButton:pressed { background: #202944; }
QPushButton#primary { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #526eec,stop:1 #795cda); border: none; }
QPushButton#primary:hover { background: #6d75ef; }
QPushButton#danger { background: #402939; border-color: #6a3f52; }
QPushButton:disabled { background: #1b2336; color: #67718c; border-color: #263049; }
QPushButton#link { background: transparent; border: none; color: #b3b9ff; }
QTextEdit { background: #0e1426; border: 1px solid #29324e; border-radius: 10px; padding: 10px; }
QCheckBox { background: transparent; spacing: 8px; }
QCheckBox::indicator { width: 15px; height: 15px; border: 1px solid #657194; border-radius: 4px; background: #0e1426; }
QCheckBox::indicator:checked { background: #7984f5; border-color: #a6afff; }
QScrollArea { border: none; }
"""


def label(text, name=None, wrap=False):
    item = QLabel(text)
    item.setTextFormat(Qt.TextFormat.PlainText)
    item.setWordWrap(wrap)
    if name:
        item.setObjectName(name)
    return item


def button(text, name=None):
    item = QPushButton(text)
    if name:
        item.setObjectName(name)
    item.setCursor(Qt.CursorShape.PointingHandCursor)
    return item


def card():
    item = QFrame()
    item.setObjectName("card")
    return item


class AuthJob(QThread):
    result = Signal(bool, str)

    def __init__(self, store, username, password, register, parent):
        super().__init__(parent)
        self.store, self.username, self.password, self.register = store, username, password, register

    def run(self):
        try:
            if self.register:
                self.store.register(self.username, self.password)
                self.result.emit(True, self.username.strip())
            elif self.store.verify(self.username, self.password):
                self.result.emit(True, self.username.strip())
            else:
                self.result.emit(False, "Invalid username or password.")
        except Exception as exc:
            self.result.emit(False, str(exc))
        finally:
            self.password = ""


class VoiceJob(QThread):
    result = Signal(str)
    error = Signal(str)

    def run(self):
        try:
            import speech_recognition as sr
            recognizer = sr.Recognizer()
            recognizer.operation_timeout = 5
            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.4)
                audio = recognizer.listen(source, timeout=4, phrase_time_limit=5)
            if not self.isInterruptionRequested():
                self.result.emit(recognizer.recognize_google(audio))
        except ImportError:
            self.error.emit("Install requirements-voice.txt to enable the optional microphone.")
        except Exception as exc:
            self.error.emit(f"Voice input unavailable: {exc}")


class SpeechJob(QThread):
    def __init__(self, text, parent):
        super().__init__(parent)
        self.text = text

    def run(self):
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.say(self.text[:500])
            engine.runAndWait()
            engine.stop()
        except Exception:
            logging.exception("Optional speech output failed")


class MainWindow(QMainWindow):
    def __init__(self, auth=None, session=None):
        super().__init__()
        self.auth = auth or AuthStore()
        self.session = session or EngineSession(self)
        self.auth_job = self.voice_job = self.speech_job = None
        self.username = self.pending = None
        self.account_generation = 0
        self.proton = Proton()
        self.proton_dialog = None
        self.setWindowTitle(TITLE)
        self.resize(1160, 820)
        self.setMinimumSize(940, 700)
        self.setStyleSheet(STYLE)
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        self.build_login()
        self.build_dashboard()
        self.stack.setCurrentWidget(self.login_page)
        self.session.status.connect(self.set_status)
        self.session.preview.connect(self.update_preview)
        self.session.message.connect(self.show_message)
        self.session.finished.connect(self.finish_pending)
        self.escape = QShortcut(QKeySequence("Esc"), self)
        self.escape.activated.connect(self.session.stop)

    def build_login(self):
        self.login_page = QWidget()
        row = QHBoxLayout(self.login_page)
        row.setContentsMargins(48, 56, 48, 56)
        row.setSpacing(36)
        brand = QFrame()
        brand.setObjectName("brand")
        left = QVBoxLayout(brand)
        left.setContentsMargins(36, 42, 36, 42)
        left.addWidget(label("◈  GESTURE / CONTROL", "eyebrow"))
        left.addStretch()
        left.addWidget(label("Your hand.\nYour workspace.", "title"))
        left.addWidget(label("A more natural way to move, select and create.", "subtitle", True))
        left.addSpacing(30)
        for title, text in (("01   Move with intent", "Live hand tracking, directly on your desktop."),
                            ("02   Pick. Move. Drop.", "Continuous dragging with a deliberate release."),
                            ("03   Stay in control", "Local accounts. A clear start and stop.")):
            left.addWidget(label(title))
            left.addWidget(label(text, "subtitle", True))
            left.addSpacing(18)
        left.addStretch()
        left.addWidget(label("ON-DEVICE TRACKING  /  WINDOWS", "eyebrow"))
        row.addWidget(brand, 1)
        right = QVBoxLayout()
        right.setSpacing(12)
        right.addStretch()
        right.addWidget(label(TITLE, "title", True))
        self.auth_heading = label("Welcome back", "subtitle", True)
        right.addWidget(self.auth_heading)
        right.addSpacing(16)
        right.addWidget(label("Username"))
        self.user_field = QLineEdit()
        self.user_field.setPlaceholderText("Your username")
        self.user_field.setMaxLength(32)
        right.addWidget(self.user_field)
        right.addWidget(label("Password"))
        self.password_field = QLineEdit()
        self.password_field.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_field.setMaxLength(128)
        self.password_field.setPlaceholderText("Your password")
        right.addWidget(self.password_field)
        self.show_password = QCheckBox("Show password")
        self.show_password.toggled.connect(lambda checked: self.password_field.setEchoMode(
            QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password))
        right.addWidget(self.show_password)
        self.confirm_field = QLineEdit()
        self.confirm_field.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_field.setMaxLength(128)
        self.confirm_field.setPlaceholderText("Confirm password")
        right.addWidget(self.confirm_field)
        self.auth_error = label("", "error", True)
        self.auth_error.setMinimumHeight(44)
        right.addWidget(self.auth_error)
        self.login_button = button("Login", "primary")
        self.login_button.clicked.connect(self.authenticate)
        self.password_field.returnPressed.connect(self.authenticate)
        self.confirm_field.returnPressed.connect(self.authenticate)
        right.addWidget(self.login_button)
        self.mode_button = button("Create a local account", "link")
        self.mode_button.clicked.connect(lambda: self.set_register(not self.register_mode))
        right.addWidget(self.mode_button)
        right.addWidget(label("Your account stays on this Windows user profile.", "subtitle", True))
        right.addStretch()
        row.addLayout(right, 1)
        self.stack.addWidget(self.login_page)
        self.set_register(False)
        if not self.auth.has_users():
            self.auth_heading.setText("First visit? Create a local account below.")

    def set_register(self, enabled):
        self.register_mode = enabled
        self.confirm_field.setVisible(enabled)
        self.confirm_field.clear()
        self.auth_error.clear()
        self.auth_heading.setText("Create your account · password: 10–128 characters" if enabled else "Welcome back")
        self.login_button.setText("Create Account" if enabled else "Login")
        self.mode_button.setText("Back to login" if enabled else "Create a local account")

    def authenticate(self):
        if self.pending or not self.login_button.isEnabled():
            return
        if self.auth_job and self.auth_job.isRunning():
            return
        username, password = self.user_field.text().strip(), self.password_field.text()
        if not username or not password:
            self.auth_error.setText("Enter your username and password.")
            return
        if self.register_mode and password != self.confirm_field.text():
            self.auth_error.setText("Passwords do not match.")
            return
        self.login_button.setEnabled(False)
        self.mode_button.setEnabled(False)
        self.auth_error.setText("Checking your account…")
        self.auth_job = AuthJob(self.auth, username, password, self.register_mode, self)
        self.auth_job.result.connect(self.auth_result)
        self.auth_job.finished.connect(self.finish_pending)
        self.auth_job.start()

    def auth_result(self, ok, value):
        self.password_field.clear()
        self.confirm_field.clear()
        self.show_password.setChecked(False)
        self.mode_button.setEnabled(True)
        if ok:
            self.login_button.setEnabled(True)
            self.username = value
            self.user_label.setText(f"LOCAL WORKSPACE  /  {value}")
            self.auth_error.clear()
            self.stack.setCurrentWidget(self.dashboard)
            self.set_status("Ready")
        else:
            self.auth_error.setText(value)
            QTimer.singleShot(1000, lambda: self.login_button.setEnabled(True))

    def build_dashboard(self):
        self.dashboard = QScrollArea()
        self.dashboard.setWidgetResizable(True)
        dashboard_content = QWidget()
        self.dashboard.setWidget(dashboard_content)
        outer = QVBoxLayout(dashboard_content)
        outer.setContentsMargins(26, 20, 26, 20)
        outer.setSpacing(16)
        header = QHBoxLayout()
        titles = QVBoxLayout()
        self.user_label = label("LOCAL WORKSPACE", "eyebrow")
        titles.addWidget(self.user_label)
        titles.addWidget(label(TITLE, "title", True))
        header.addLayout(titles, 1)
        self.status_badge = label("Ready", "status")
        header.addWidget(self.status_badge)
        self.logout_button = button("Logout")
        self.logout_button.clicked.connect(self.logout)
        header.addWidget(self.logout_button)
        outer.addLayout(header)
        body = QHBoxLayout()
        body.setSpacing(20)
        preview_card = card()
        preview_layout = QVBoxLayout(preview_card)
        preview_layout.setContentsMargins(18, 18, 18, 18)
        top = QHBoxLayout()
        top.addWidget(label("LIVE WORKSPACE", "eyebrow"))
        top.addStretch()
        top.addWidget(label("On-device hand tracking", "subtitle"))
        preview_layout.addLayout(top)
        self.preview_label = label("◈\n\nYour camera preview appears here\nStart gesture control when you’re ready.", "subtitle", True)
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumSize(420, 290)
        self.preview_label.setStyleSheet("background: #0b1020; border-radius: 12px;")
        preview_layout.addWidget(self.preview_label, 1)
        metrics = QHBoxLayout()
        self.gesture_label = label("Gesture   —")
        self.drag_label = label("Drag   IDLE")
        self.fps_label = label("— FPS   ·   — ms")
        for widget in (self.gesture_label, self.drag_label, self.fps_label):
            metrics.addWidget(widget)
        preview_layout.addLayout(metrics)
        body.addWidget(preview_card, 3)
        control_card = card()
        panel = QVBoxLayout(control_card)
        panel.setContentsMargins(18, 18, 18, 18)
        panel.setSpacing(9)
        panel.addWidget(label("CONTROL CENTER", "eyebrow"))
        panel.addWidget(label("Ready when you are", "subtitle"))
        self.camera_index = QSpinBox()
        self.camera_index.setRange(0, 9)
        self.backend = QComboBox()
        self.backend.addItems(["DSHOW", "MSMF", "AUTO"])
        self.hand = QComboBox()
        self.hand.addItems(["Right", "Left"])
        self.profile = QComboBox()
        self.profile.addItem("Original full gestures", "full")
        self.profile.addItem("Uploaded simple gestures", "simple")
        self.mode = QComboBox()
        self.mode.addItem("Bare hand · MediaPipe", "hands")
        self.mode.addItem("Glove · ArUco marker", "glove")
        form = QFormLayout()
        form.setSpacing(8)
        camera_row = QHBoxLayout()
        camera_row.addWidget(self.camera_index)
        camera_row.addWidget(self.backend)
        form.addRow("Camera", camera_row)
        for title, widget in (("Main hand", self.hand), ("Profile", self.profile), ("Tracking", self.mode)):
            form.addRow(title, widget)
        panel.addLayout(form)
        self.start_button = button("Start Gesture Control", "primary")
        self.stop_button = button("Stop Gesture Control", "danger")
        self.start_button.clicked.connect(self.start_control)
        self.stop_button.clicked.connect(self.session.stop)
        self.stop_button.setEnabled(False)
        panel.addWidget(self.start_button)
        panel.addWidget(self.stop_button)
        panel.addWidget(label("Esc stops control while this app is focused.\nMove your physical mouse to a screen corner to trigger the fail-safe.", "subtitle", True))
        self.proton_button = button("Open Proton assistant")
        self.proton_button.clicked.connect(self.open_proton)
        panel.addWidget(self.proton_button)
        panel.addStretch()
        body.addWidget(control_card, 2)
        outer.addLayout(body, 1)
        guide_card = card()
        guide_layout = QVBoxLayout(guide_card)
        guide_layout.setContentsMargins(20, 16, 20, 16)
        guide_layout.addWidget(label("GESTURE QUICK GUIDE", "eyebrow"))
        self.guide_label = label("", "subtitle", True)
        guide_layout.addWidget(self.guide_label)
        self.profile.currentIndexChanged.connect(self.update_guide)
        self.mode.currentIndexChanged.connect(self.update_guide)
        self.update_guide()
        outer.addWidget(guide_card)
        self.notice = label("Camera is off. Your mouse stays under your control until you press Start.", "subtitle", True)
        self.notice.setMinimumHeight(34)
        outer.addWidget(self.notice)
        self.stack.addWidget(self.dashboard)

    def update_guide(self):
        if self.mode.currentData() == "glove":
            text = "Original glove mode: spread two fingers to move / arm · fist to double-click · one finger is inactive. Use a solid-color glove and a DICT_4X4_50 marker. Pick and Drop is available in bare-hand mode."
        elif self.profile.currentData() == "simple":
            text = "PALM move / rearm  ·  brief FIST then PALM: left click  ·  hold FIST: pick and drag  ·  PALM: drop  ·  INDEX: right click  ·  FIRST2: double click. Return to PALM before another click."
        else:
            text = "V_GEST move / arm  ·  MID left click  ·  INDEX right click  ·  TWO_FINGER_CLOSED double click  ·  FIST pick and drag  ·  PALM or V_GEST drop\nPINCH_MINOR: scroll horizontally / vertically  ·  PINCH_MAJOR: brightness horizontally / volume vertically. Return to V_GEST before another click."
        self.guide_label.setText(text)

    def start_control(self):
        if not self.username or self.pending:
            return
        settings = Settings(camera_index=self.camera_index.value(), backend=self.backend.currentText(),
                            dominant_hand=self.hand.currentText(), profile=self.profile.currentData(), mode=self.mode.currentData())
        if settings.mode == "glove":
            settings = replace(settings, profile="full")
        self.notice.setText("Starting camera and tracker. Begin with an open palm or V gesture.")
        self.session.start(settings)

    def set_status(self, value):
        self.status_badge.setText(value)
        busy = value in ("Starting", "Running", "Stopping") or self.session.active
        self.start_button.setEnabled(not busy and self.username is not None)
        self.stop_button.setEnabled(busy and value != "Stopping")
        for widget in (self.camera_index, self.backend, self.hand, self.profile, self.mode):
            widget.setEnabled(not busy)
        if value in ("Ready", "Camera Error", "Error"):
            self.preview_label.clear()
            self.preview_label.setText("◈\n\nCamera is off\nStart gesture control to reconnect.")
            self.gesture_label.setText("Gesture   —")
            self.drag_label.setText("Drag   IDLE")
            self.fps_label.setText("— FPS   ·   — ms")

    def update_preview(self, packet):
        image = QImage.fromData(packet["jpeg"], "JPG")
        if not image.isNull():
            pixmap = QPixmap.fromImage(image).scaled(self.preview_label.size(), Qt.AspectRatioMode.KeepAspectRatio,
                                                   Qt.TransformationMode.SmoothTransformation)
            self.preview_label.setPixmap(pixmap)
        self.gesture_label.setText("Gesture   "+packet["gesture"])
        self.drag_label.setText("Drag   "+packet["drag"])
        self.fps_label.setText(f'{packet["fps"]:.0f} FPS  ·  {packet["ms"]:.1f} ms')
        self.fps_label.setToolTip(f'Frame age at action: {packet["age_ms"]:.1f} ms; excludes display/OS latency.')

    def show_message(self, text):
        logging.warning(text)
        self.notice.setText(text.split("\n")[0])
        self.notice.setToolTip(text)

    def logout(self):
        self.account_generation += 1
        self.pending = "logout"
        self.session.stop()
        if self.voice_job and self.voice_job.isRunning():
            self.voice_job.requestInterruption()
        self.finish_pending()

    def finish_pending(self):
        if not self.pending or self.session.active:
            return
        if any(job and job.isRunning() for job in (self.auth_job, self.voice_job, self.speech_job)):
            return
        pending, self.pending = self.pending, None
        if pending == "close":
            self.close()
        else:
            self.username = None
            self.proton = Proton()
            if self.proton_dialog:
                self.proton_dialog.close()
                self.proton_dialog.deleteLater()
                self.proton_dialog = None
            self.set_register(False)
            self.password_field.clear()
            self.user_field.clear()
            self.stack.setCurrentWidget(self.login_page)

    def closeEvent(self, event):
        if self.session.active or any(job and job.isRunning() for job in (self.auth_job, self.voice_job, self.speech_job)):
            event.ignore()
            self.pending = "close"
            self.session.stop()
            if self.voice_job and self.voice_job.isRunning():
                self.voice_job.requestInterruption()
            self.notice.setText("Closing safely. Waiting for active workers to finish…")
        else:
            event.accept()

    def open_proton(self):
        if self.proton_dialog:
            self.proton_dialog.show()
            self.proton_dialog.raise_()
            return
        self.proton_dialog = QDialog(self)
        self.proton_dialog.setWindowTitle("Proton assistant")
        self.proton_dialog.resize(600, 460)
        layout = QVBoxLayout(self.proton_dialog)
        layout.addWidget(label("PROTON / ASSISTANT", "eyebrow"))
        self.conversation = QTextEdit()
        self.conversation.setReadOnly(True)
        self.conversation.setPlainText("Type 'help' for commands. Optional voice input uses Google speech recognition (internet required). Text commands run locally except browser searches.")
        layout.addWidget(self.conversation)
        self.command_field = QLineEdit()
        self.command_field.setPlaceholderText("Try: Proton list files")
        self.command_field.returnPressed.connect(self.send_command)
        layout.addWidget(self.command_field)
        row = QHBoxLayout()
        send = button("Send", "primary")
        send.clicked.connect(self.send_command)
        self.voice_button = button("Listen once")
        self.voice_button.clicked.connect(self.listen)
        row.addWidget(send)
        row.addWidget(self.voice_button)
        layout.addLayout(row)
        self.proton_dialog.show()

    def send_command(self, spoken=None):
        if not self.username or self.pending:
            return
        text = spoken if isinstance(spoken, str) else self.command_field.text()
        if not text.strip():
            return
        self.command_field.clear()
        answer, action = self.proton.respond(text)
        self.conversation.insertPlainText(f"\n\nYou: {text}\nProton: {answer}")
        if action == "start":
            self.start_control()
        elif action == "stop":
            self.session.stop()
        elif action == "exit":
            self.close()
        elif action in ("copy", "paste"):
            generation = self.account_generation
            QTimer.singleShot(2000, lambda: self.shortcut(action, generation))
        if isinstance(spoken, str) and action != "exit" and not (self.speech_job and self.speech_job.isRunning()):
            self.speech_job = SpeechJob(answer, self)
            self.speech_job.finished.connect(self.finish_pending)
            self.speech_job.start()

    def shortcut(self, action, generation):
        if self.username and not self.pending and generation == self.account_generation:
            try:
                import pyautogui
                pyautogui.hotkey("ctrl", "c" if action == "copy" else "v")
            except Exception as exc:
                self.show_message(str(exc))

    def listen(self):
        if self.voice_job and self.voice_job.isRunning():
            return
        self.voice_button.setEnabled(False)
        self.voice_job = VoiceJob(self)
        self.voice_job.result.connect(self.send_command)
        self.voice_job.error.connect(self.show_message)
        self.voice_job.finished.connect(lambda: self.voice_button.setEnabled(True))
        self.voice_job.finished.connect(self.finish_pending)
        self.voice_job.start()
