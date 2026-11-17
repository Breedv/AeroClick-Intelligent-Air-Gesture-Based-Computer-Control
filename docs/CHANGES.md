# What changed and why

## Findings in the uploaded files

- The active `src/Gesture_Controller.py` had 147 lines and implemented only PALM motion, FIST click, INDEX right-click and FIRST2 double-click. There were **no `mouseDown` or `mouseUp` calls anywhere in the uploaded Python source**. The README's Pick and Drop behavior was therefore absent from this working tree, rather than simply delayed.
- Its finger bitmask was built index-to-pinky but compared to 1 and 3 for index/two fingers. The correct values are 8 and 12. It used unsigned tip-to-base distance, so a folded fingertip could appear extended; unknown masks became PALM.
- Clicks were emitted every frame. Movement requested a duration and retained PyAutoGUI's default pause. There was no click rearm, drag state, tracking-loss cleanup or finite camera read failure policy.
- Camera acquisition happened in the controller constructor. The Eel launcher started it before any login. Closing used `os._exit(0)` and skipped cleanup. Proton expected `gc_mode` that the shortened controller no longer defined.
- The glove variant initialized ArUco calibration at class import, used removed OpenCV APIs, spun in a busy FPS wait, reinitialized CSRT repeatedly, swapped camera dimensions in cursor movement and lacked robust empty-frame handling.
- A VS Code scratch file had an indentation error. Old pinned packages targeted Python 3.8 and omitted some installation requirements.

## Preserved project lineage

The project was extracted and edited; this is not an unrelated replacement. The original `Gest` / `HLabel` encodings remain. The existing controller responsibilities were split into testable recognition, action, camera and adapter modules. `Gesture_Controller.py` remains a launch compatibility module. The glove's Marker, ROI, Glove and Tracker algorithms, calibration images, diagram, web assets, GPL license and original documentation are retained. Original versions of the replaced Python files are in `docs/original_source/*.txt` for comparison, not execution.

The source README identifies [xenon-19/Gesture-Controlled-Virtual-Mouse](https://github.com/xenon-19/Gesture-Controlled-Virtual-Mouse). Its [original controller](https://raw.githubusercontent.com/xenon-19/Gesture-Controlled-Virtual-Mouse/main/src/Gesture_Controller.py) establishes the full gesture mapping. This mapping was used to restore the features named in the uploaded README. It was not inferred from the new UI. The upload's simpler mapping remains available as a separate profile; FIST click is emitted on short-pose release so a longer FIST can drag without first generating a click.

## Repair details

- `IDLE → PICK_CANDIDATE → DRAGGING → RELEASE_CANDIDATE → IDLE`, using monotonic time plus at least two observations. No sleeps in the action controller.
- 90 ms pick, 120 ms release, 80 ms click validation, 450 ms tracking-loss grace. Simple-profile hold is 300 ms. Thresholds are centralized in `src/config.py`.
- Palm-scale normalized pinch and finger-angle/reach checks, with hysteresis. Explicit UNKNOWN observations do not become movement/release gestures.
- Hover anchoring at pick, time-aware cursor filtering, one-pixel screen inset and one event per actual pixel change.
- Dominant-hand ownership stays fixed. The other hand cannot steal a held drag. Unknown/missing hands freeze movement and long loss releases it.
- Single camera owner and latest-only preview queue. Recognition is a supervised process; native UI is on the Qt main thread. One model per run. A low-rate preview reuses the recognition frame.
- Parent-side shared button state allows release after engine failure. Fail-safe release bypasses PyAutoGUI's corner exception. No claim is made about uncatchable whole-system termination.
- PySide6 frontend replaces the Eel runtime. Password hashing runs in a worker; login precedes camera activation. Registration, error states, Stop, Logout, repeated cycles and close are connected to real services.
- Original Proton commands are integrated; optional microphone/speech dependencies are separate. The glove variant has its own preserved mapping and does not acquire a second camera.

## Deliberate limits

Primary display only. No model training or empirical gesture accuracy claim. The full profile explicitly drops with PALM or V_GEST instead of any non-FIST frame; this prevents accidental drops from transient click/pinch classifications. The uploaded glove mapping has move/double-click only, so Pick and Drop remains a bare-hand feature. Voice recognition retains the original optional online service. Camera, hands, gloves, actual volume/brightness effects and desktop drag/drop require the documented physical acceptance test.
