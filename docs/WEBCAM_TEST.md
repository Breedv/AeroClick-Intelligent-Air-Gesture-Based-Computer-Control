# Physical Windows acceptance test — still required

The automated tests use synthetic landmarks and a mocked mouse. A real MediaPipe model is initialized on a blank frame, but this does **not** verify your hand, lighting, webcam, or Windows drag/drop. Run this procedure on your laptop before treating the application as validated for daily use.

## Preparation

1. Follow README setup and run `python tools\check_install.py`.
2. Use the primary monitor. Create a temporary folder containing disposable files `A.txt`, `B.txt` and an empty subfolder. Test on copies, not important files.
3. Launch `python main.py`; confirm Login appears and camera LED remains off. Register a local test account, logout, reject a wrong password, then login correctly.
4. Select **Original full gestures**, **Bare hand**, your physical main hand and the working camera/backend. Start. Confirm one camera preview, Running status and responsive controls. Show PALM or V_GEST to arm the session.
5. Use even lighting and keep your whole hand in view, approximately palm-facing. Record camera model, resolution, Windows scaling, processor and lighting. Do not assume the default thresholds suit every camera/hand.

## Pick / drag / drop (highest priority)

| Step | Expected observation |
|---|---|
| Hover over A.txt using V_GEST | Stable cursor over file |
| Close fist and hold >90 ms | PICK_CANDIDATE then DRAGGING; file selected once |
| Move the closed fist | File follows continuously; no click spam or jump when picking |
| Keep fist still | Button remains held; no repeated mouse-down |
| Briefly show a conflicting click pose | No click and no release |
| Show PALM for >120 ms at destination | RELEASE_CANDIDATE then IDLE; file drops once at the current location |
| Repeat using V_GEST as release | Same single release and return to movement |
| Repeat 20 times, including moving into the test subfolder | Every file ends at the intended target; no stuck left button |
| Start a fist drag on empty folder space | Selection rectangle works for multiple items |

During an active drag, briefly occlude the hand for about 200 ms, then restore the same fist: the cursor should freeze, the button should stay held, and reacquisition should not jump. Hide it for over 450 ms: the button should release. Keep the fist on return: no fresh pick until a neutral/move pose rearms control.

## Other gestures

- V_GEST → MID: one left click. Hold MID for two seconds: no repeats. Return to V_GEST and repeat.
- V_GEST → INDEX: one right click. V_GEST → index/middle together: one double-click. Confirm these also work after a completed drag.
- PALM: neutral while idle. Unknown partial poses should not trigger clicks.
- Other-hand pinch: move horizontally and vertically in an application supporting those scroll directions. No cursor movement should occur solely from that pinch. Main hand disappearing during a drag must not let the other hand take over.
- Main-hand pinch: horizontal brightness and vertical volume adjustment. Test reversible small changes and restore settings afterward. If the hardware cannot expose brightness, expect an explicit warning while cursor control remains functional.
- Switch to **Uploaded simple gestures** after stopping. Verify PALM movement; a short fist then PALM clicks once; a fist held over 300 ms drags; PALM drops; INDEX and FIRST2 retain right/double clicks.

## Lifecycle and failure handling

1. Stop while dragging: left button released, camera LED off, Ready status. Restart and repeat at least 10 cycles.
2. Logout while dragging: engine stops before Login appears; no further cursor actions. Log in again and Start.
3. Close the window while dragging: camera and mouse release; app process exits.
4. Move the physical mouse into a primary-screen corner: fail-safe stops the engine and releases a drag.
5. Test a wrong camera index and a busy camera: show Camera Error, with Start available after cleanup. Fix the index and restart successfully.
6. For an external webcam, unplug it during a drag: expect error/timeout and release. Reconnect and restart. Do not disable Windows security/privacy settings to force access.
7. Launch a second application instance: it should report the first is already open, not start a second engine.
8. Leave control active for 15 minutes, including pauses. Observe CPU/memory and compare FPS over time. Record processing duration and frame age, and any stale preview or shutdown delay. No sustained performance claim is made until this is measured.

## Additional retained features

- Glove mode: test the actual colored glove/ArUco marker, correct marker orientation, ROI/color segmentation, marker disappearance and reacquisition, move and double-click. The original glove variant does not implement bare-hand FIST dragging.
- Proton: test local text commands, bounded file navigation, optional microphone transcription and speech replies. Network speech recognition and browser search require connectivity. Start/Stop must control the same dashboard engine. Confirm logout waits for pending microphone/speech work to complete.

Record pass/fail and notes for each step. If a pose misclassifies, use the preview's actual gesture name to diagnose it. Adjust centralized thresholds only with a repeatable test, then rerun the software tests and this checklist. Test with different lighting, distances, both main-hand selections and your Windows display scaling.
