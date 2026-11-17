# Gesture Control Recognition System

An updated version of the uploaded Gesture-Controlled-Virtual-Mouse project: a native PySide6 login/dashboard integrated with the OpenCV + MediaPipe controller. The original gesture encodings, glove recognition pipeline, assets, license and Proton commands are retained. See `docs/CHANGES.md` for the discrepancies found in the upload and the mapping decisions.

**Start here:** use **Windows 10/11, Python 3.10 (64-bit)** and the primary monitor. Automated software tests do not establish physical gesture accuracy. The required webcam acceptance test is in `docs/WEBCAM_TEST.md`.

## Run in VS Code on Windows

1. Extract the ZIP into a short path, for example `C:\Projects\Gesture-Control-Recognition-System`. Open that folder in VS Code: **File → Open Folder**. The folder must contain `main.py` and `requirements.txt`.
2. Install Python **3.10 x64** and the Microsoft **Python** extension for VS Code. Check the interpreter with `py -3.10 --version`.
3. Open **Terminal → New Terminal**, choose **PowerShell**, and run these commands from the project root:

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
python tools\check_install.py
python main.py
```

If PowerShell blocks activation, use the virtual environment directly; no execution-policy change is required:

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe tools\check_install.py
.\.venv\Scripts\python.exe main.py
```

4. In VS Code, press **Ctrl+Shift+P → Python: Select Interpreter**, then select `.venv\Scripts\python.exe`. The included **Gesture Control · Login** debug configuration runs `main.py` with F5.
5. The first screen is **Login**. Click **Create a local account**. Usernames use 3–32 letters, digits, dots, underscores or hyphens. Passwords use 10–128 characters. There is no default password. Registration opens the dashboard; subsequent launches require login.
6. Select your main hand, camera index and gesture profile. Click **Start Gesture Control**, show an open palm or V gesture, then use the gestures below. **Stop Gesture Control**, Logout and closing the window stop the engine and release any held left button.

Installation needs internet access. Bare-hand tracking, login and the dashboard work locally afterward; MediaPipe's hand model is bundled in its pinned wheel. Install only `opencv-contrib-python` from this project, not an additional `opencv-python` or headless OpenCV wheel.

### If installation reports WinError 206

Move the extracted project to a short path. Set a short temporary build folder for this terminal, then retry installation:

```powershell
New-Item -ItemType Directory -Force .\work\tmp | Out-Null
$env:TEMP = (Resolve-Path .\work\tmp).Path
$env:TMP = $env:TEMP
python -m pip install -r requirements.txt
```

### Run automated tests

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m compileall -q src tools tests main.py
python -m pip check
```

For headless UI tests only: `$env:QT_QPA_PLATFORM = "offscreen"` before pytest. Remove it before normal use: `Remove-Item Env:\QT_QPA_PLATFORM -ErrorAction SilentlyContinue`. Tests use synthetic hands, fake cameras and a recording mouse; they never move your desktop mouse or open a webcam. They also initialize the real MediaPipe model on a blank frame and test a generated ArUco marker. Test accounts are temporary.

`requirements.txt` pins the direct runtime dependencies. `requirements-lock.txt` records all packages from the tested Python 3.10 environment, including test and optional voice packages, for exact environment reproduction with `python -m pip install -r requirements-lock.txt`.

## Gesture guide

The preview is mirrored. **Right/Left** refers to your physical main hand. Keep the whole hand visible, palm generally facing the camera. The palm base (landmark 9) drives the cursor, as in the uploaded controller. Cursor motion is bounded to the primary screen; multi-monitor spanning is not implemented.

### Original full gestures (default)

The upload's README described these features, but its shortened active controller had lost most of them. They are restored using the original project's gesture meanings.

| Recognized gesture | Pose | Action |
|---|---|---|
| `PALM` | Four fingers open | Neutral; drop after a stable release pose |
| `V_GEST` | Index and middle open, spread in a V | Move the cursor and arm the next click; also drop |
| `MID` | Middle finger open, others folded | One left click after V_GEST |
| `INDEX` | Index finger open, others folded | One right click after V_GEST |
| `TWO_FINGER_CLOSED` | Index and middle open, together | One double-click after V_GEST |
| `FIST` | Four fingers folded | Pick: hold left button, then drag with hand movement |
| `PINCH_MINOR` | Thumb/index pinch with remaining three fingers open, other hand | Move pinch left/right to scroll horizontally; up/down to scroll vertically |
| `PINCH_MAJOR` | Same pinch, main hand | Move pinch left/right to adjust brightness; up/down to adjust volume |

Return to V_GEST before another click. Holding a click pose does not generate repeated clicks. Pinch controls use incremental displacement with a dead zone; holding the pinch still does not continuously change the setting. Volume is clamped to 0–100%; brightness targets display 0 and depends on monitor/driver support. Unsupported system controls report a message and disable only that control for the current session.

**Pick and Drop:** hover over a disposable test file with V_GEST → close your fist for about 90 ms → move the closed fist → show PALM or V_GEST for about 120 ms to drop. The hover location is anchored when picking, and cursor movement pauses during the release candidate to keep the drop position steady. Multi-item selection uses the same drag action starting on empty space.

### Uploaded simple gestures

Preserves the shortened upload's intended Palm/Fist/Index/First2 actions and fixes its reversed bitmask checks:

| Pose | Action |
|---|---|
| `PALM` | Move/rearm; drop if dragging |
| Brief `FIST`, then PALM | One left click on release (at least 80 ms, below 300 ms) |
| Hold `FIST` for 300 ms | Pick and drag |
| `INDEX` | One right click after PALM |
| `FIRST2` | One double-click after PALM |

The short-fist/long-fist distinction is necessary because the uploaded version used FIST for left-click while the original full version uses it for dragging. The simple profile does not activate pinch controls. Unknown finger combinations do nothing instead of being misclassified as a palm.

### Glove / ArUco mode

This retains the separate uploaded marker/HSV/contour pipeline and its original mapping: **spread two fingers to move/arm**, **fist to double-click**, **one finger inactive**. It shares the dashboard, camera ownership, preview and stop lifecycle. Use a solid-color glove and a `DICT_4X4_50` marker, oriented as in the original setup. The original ArUco API calls and tracker initialization were updated for the pinned OpenCV version. Bare-hand Pick and Drop does not apply to this legacy glove mapping. Physical glove/marker verification is still required.

## Stopping and recovery

- Click Stop or press **Escape while this app is focused**. Logout and window close also stop.
- Move the physical mouse into a primary-screen corner to trigger PyAutoGUI's fail-safe. The engine checks it on every iteration. Cleanup can release the left button even while that fail-safe is active.
- Brief hand loss freezes the cursor and preserves a drag for up to **450 ms**. Longer loss releases the button and requires PALM/V_GEST before accepting another action. Reacquisition anchors at the current cursor instead of jumping.
- Clicks and pinches cannot interrupt an active drag. A confirmed PALM/V_GEST drops it. A one-frame mistake cannot pick, click or drop.
- Start is guarded against duplicates. Only one application instance per Windows user data directory is allowed. A stalled worker has a stop deadline; the dashboard can terminate it and release the button.
- Cleanup covers normal stop, camera errors, Python exceptions and supervised engine exits. Forced termination of the entire application tree, OS failure or power loss cannot guarantee cleanup. A physical mouse click/release restores control if needed.

## Camera troubleshooting

Close other camera applications. In Windows Settings, allow desktop applications to access the camera. Try camera index 0, then 1; try **DSHOW**, **MSMF**, then **AUTO**. The app reports **Camera Error** on open/read failure. Stop and restart after correcting the issue.

The separate diagnostic never activates mouse control:

```powershell
python tools\camera_preview.py --index 0 --backend DSHOW
```

If a system library fails to import, install the current Microsoft Visual C++ Redistributable x64, recreate the virtual environment, and reinstall the pinned requirements. Run `tools\check_install.py` and inspect the log for the exact exception. Avoid Python 3.13+ for this pinned legacy MediaPipe Solutions stack; Python 3.10 x64 is the tested target.

## Proton assistant

Open Proton from the authenticated dashboard. Text commands retain the original start/stop, date/time, search/location, file navigation, copy/paste, sleep/wake and exit features. File navigation starts in the Windows user's home directory instead of a hardcoded `C:\` root. Copy/paste gives two seconds to focus the target application. Search/location opens the default browser.

Optional original speech input/output:

```powershell
python -m pip install -r requirements-voice.txt
```

**Listen once** records a bounded utterance and uses Google speech recognition, as the original Proton did; this optional feature sends audio to that service and needs internet. Replies use local text-to-speech. The core gesture application has no cloud dependency. Microphone and spoken output require separate physical tests.

## Accounts and logs

Accounts are in `%LOCALAPPDATA%\GestureControlRecognition\accounts.sqlite3`. Passwords use PBKDF2-HMAC-SHA256 with 600,000 iterations, independent 32-byte salts, constant-time comparison and parameterized SQLite queries. Passwords are never logged or stored in plaintext. This is a local application gate, not protection against someone who can modify your Windows files or source code. No password reset or recovery service is included; create another local account if necessary.

Rotating diagnostics are in the same directory as `application.log`. Test harnesses can set `GESTURE_CONTROL_DATA_DIR` to an isolated folder. No account database or log is distributed in the ZIP.

## Layout

```text
main.py                         Application launcher
src/app.py, ui.py                Native login/dashboard and lifecycle
src/auth.py                     Local accounts
src/recognition.py               Original encodings, repaired landmark classification
src/controller.py                Drag states, click gating, cursor filter, pinch actions
src/camera.py                    Single latest-frame capture thread
src/engine.py, session.py        Recognition process and Qt supervisor
src/desktop.py                   Mouse, fail-safe cleanup, volume/brightness worker
src/Gesture_Controller.py        Compatible login launcher and public exports
src/Gesture_Controller_Gloved.py Preserved and updated glove recognition pipeline
src/Proton.py                    Integrated assistant commands
src/calib_images, src/web        Original calibration and web assets (reference)
tests/                          Automated tests; no camera or real mouse injection
tools/                          Installation and camera diagnostics
docs/                           Changes, test results, manual acceptance procedure
```

The old Eel server is no longer used by the application. Its assets remain for provenance. Directly running `src/app.py`, `src/Gesture_Controller.py` or `src/Proton.py` opens the same login interface.

## Performance and limits

This update removes per-frame click spam and PyAutoGUI's default 100 ms pause; cursor moves have zero requested duration. Capture holds only the latest frame, preview is capped at 15 FPS, drawing happens only for preview frames, model initialization happens once per Start, and monitor/audio calls run outside recognition. A separate process keeps ML and camera work off the GUI thread.

The dashboard reports processed FPS, processing duration and frame age. These are software diagnostics, not full camera-to-cursor latency measurements. No accuracy percentage, sustained laptop FPS or speedup is claimed without physical measurement. Real hand shapes, lighting, occlusion, Windows DPI, camera drivers, monitor brightness and native file drag/drop still need the acceptance procedure.

See `docs/TEST_RESULTS.md` for the actual executed checks and `docs/WEBCAM_TEST.md` for remaining work. Original GPL-3.0 license and attribution are retained in `LICENSE` and `docs/ORIGINAL_README.md`.

Dependency references: [MediaPipe 0.10.21 Windows wheels](https://pypi.org/project/mediapipe/0.10.21/), [Qt for Python installation](https://doc.qt.io/qtforpython-6.8/gettingstarted.html).
