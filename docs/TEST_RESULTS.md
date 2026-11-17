# Executed validation — 17 November 2026

Test host: Windows x64 (build 26300), CPython **3.10.2**, isolated virtual environment. The deliverable targets Python 3.10 x64. Installed versions are recorded in `requirements-lock.txt`.

## Results

| Check actually executed | Result |
|---|---|
| `python -m pytest -q --junitxml=docs/test-results.xml` | **73 passed in 17.83 seconds** |
| Python syntax/bytecode compilation of all project `.py` files | Passed |
| `python -m pip check` | No broken requirements found |
| `python tools/check_install.py` | Core imports, installed-package checks, real MediaPipe initialization/inference on a blank frame and ArUco API passed |
| Optional SpeechRecognition, PyAudio and pyttsx3 imports | Passed; no microphone/audio output was used |
| Actual `main.py` launch, login-first screen, camera-off state and clean close | Passed twice in subprocess tests |
| Native Qt Windows platform rendering | Login/dashboard rendered successfully using 186 system font families, without displaying a live control session |
| UI layout inspection | Login and dashboard inspected; small dashboard uses scrolling instead of cutting off controls |
| Synthetic 10,000-sample logic benchmark | Median **0.0354 ms**, p95 **0.0462 ms**, mean **0.0376 ms** |

Benchmark scope is **landmark classification plus action logic only**, using synthetic landmarks and a recording mouse. It excludes webcam capture, MediaPipe inference, IPC, preview rendering, Windows input and display latency. It is not an FPS estimate or a measured speedup over the uploaded project.

The JUnit report is `test-results.xml`. Tests do not inject real desktop mouse events or acquire a physical camera. UI screenshots were generated from the actual PySide6 widgets; the displayed preview account is a test fixture, not a default account in the application.

## What the tests cover

- Finger masks, full/simple profiles, scale/rotation geometry, pinches, invalid/missing landmarks and fixed main-hand ownership.
- One mouse-down/one mouse-up, continuous drag movement, hover/drop anchoring, click suppression while dragging, false release frames, brief tracking loss, prolonged loss and rearming.
- 100 repeated drag/drop cycles with deterministic noisy observations, left/right/double-click rearming, simple-profile short-fist click versus held-fist drag, horizontal/vertical scroll, volume/brightness command routing and cursor bounds/filter behavior.
- Entire synthetic frame → landmarks → classifier → drag controller pipeline, including disconnection while held and inference failure cleanup.
- Camera open/read failures, latest-frame buffering, resource release, bounded preview queues and real MediaPipe/ArUco initialization.
- Spawned engine processes, duplicate Start guards, repeated Start/Stop, camera errors, hung-worker termination and parent-side cleanup of a simulated held button after forced exit. The shared hold flag has no lock that a terminated worker could orphan.
- Account registration, independent salts/hashes, case-insensitive usernames, duplicate/invalid accounts, wrong passwords, persistence, SQL injection strings and absence of plaintext passwords in the database.
- UI registration/login/logout, show-password, invalid credentials, responsive controls, close while active, authenticated Start, repeated runs, single-instance lock and Proton Start/Stop routing.
- Proton file navigation/search escaping, commands and sleep/wake. Desktop adapter ordering, nonblocking system-control dispatch and graceful handling of a simulated WMI denial.

## Environment limitation observed

The installed `screen-brightness-control` package attempts to connect to Windows WMI during import. This sandbox returned **Access is denied** (`-2147024891`). That is recorded as a deferred device check. The app catches device-control errors and displays a warning while other controls continue; the error-handling path is tested. Actual monitor brightness adjustment was **not verified**. No volume change was attempted.

The dependency installation initially failed on long sandbox build/cache paths. Using short writable temporary and pip-cache directories resolved installation. The original scratch `tempCodeRunnerFile.py` contained an indentation error; it is retained as non-executable reference text. One test initially omitted the required `QLockFile.tryLock(0)` argument and was corrected. The final suite has no failures or skips.

## Still requires physical verification

No physical webcam gesture session, actual file/icon drag/drop, empirical hand-recognition accuracy, sustained laptop FPS, camera disconnect/reconnect, physical fail-safe activation, multi-DPI cursor behavior, glove/marker setup, audio endpoint adjustment, monitor brightness change, microphone transcription or spoken response was tested. Follow **WEBCAM_TEST.md** for those checks. The completed source is software-tested, not a claim of hardware certification.
