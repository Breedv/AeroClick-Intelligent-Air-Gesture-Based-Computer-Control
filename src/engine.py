"""Supervised camera/recognition process; Qt never executes camera or ML calls."""
import queue
import time
import traceback
from .camera import CameraError, LatestCamera
from .controller import Controller
from .recognition import Gest, HandRecog, HLabel


def latest_put(channel, item):
    try:
        channel.put_nowait(item)
    except queue.Full:
        try:
            channel.get_nowait()
        except queue.Empty:
            return
        try:
            channel.put_nowait(item)
        except queue.Full:
            pass


def select_hands(result, dominant):
    """Never give a different physical hand ownership when the dominant is lost."""
    major = minor = None
    for hand, label in zip(result.multi_hand_landmarks or [], result.multi_handedness or []):
        classification = label.classification[0]
        if classification.score < 0.65:
            continue
        if classification.label == dominant:
            major = hand
        else:
            minor = hand
    return major, minor


def run_engine(settings, stop, frames, events, held, heartbeat):
    from .desktop import DesktopMouse, SystemControls, emergency_release
    camera = tracker = controls = controller = None
    frames.cancel_join_thread()  # Exit cannot wait for an unread preview frame.
    try:
        import cv2
        import mediapipe as mp
        cv2.setNumThreads(1)
        mouse = DesktopMouse(held)
        controls = SystemControls(lambda msg: events.put(("warning", msg)))
        controller = Controller(mouse, settings, controls)
        if settings.mode == "glove":
            from .Gesture_Controller_Gloved import GlovedTracker
            tracker = GlovedTracker()
        else:
            tracker = mp.solutions.hands.Hands(
                static_image_mode=False, max_num_hands=2, model_complexity=1,
                min_detection_confidence=settings.detection_confidence,
                min_tracking_confidence=settings.tracking_confidence)
        camera = LatestCamera(settings).start()
        rec_major, rec_minor = HandRecog(HLabel.MAJOR), HandRecog(HLabel.MINOR)
        sequence = 0
        started = last_frame = last_preview = time.monotonic()
        fps_start, count, fps = started, 0, 0.0
        announced = False
        while not stop.is_set():
            now = time.monotonic()
            mouse.check_failsafe()
            if now-heartbeat.value > 4:
                raise RuntimeError("Dashboard heartbeat lost; controls stopped.")
            packet = camera.read(sequence)
            if packet is None:
                controller.update(None, None, now)
                if now-last_frame > (8 if not announced else 1.5):
                    raise CameraError("Camera timed out while waiting for a frame.")
                continue
            sequence, captured, frame = packet
            if time.monotonic()-captured > 0.4:
                controller.update(None, None, time.monotonic())
                continue
            last_frame = time.monotonic()
            processing_start = time.perf_counter()
            frame = cv2.flip(frame, 1)
            preview_due = now-last_preview >= 1/settings.preview_fps
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            point = pinch_point = None
            if settings.mode == "glove":
                gesture, point = tracker.process(frame)
                # Original glove mode: two spread fingers move, fist double-click.
                if gesture == Gest.TWO_FINGER_CLOSED:
                    gesture = Gest.FIRST2 if settings.profile == "simple" else gesture
            else:
                rgb.flags.writeable = False
                result = tracker.process(rgb)
                major, minor = select_hands(result, settings.dominant_hand)
                for recognizer, hand in ((rec_major, major), (rec_minor, minor)):
                    recognizer.aspect = frame.shape[1]/frame.shape[0]
                    recognizer.update_hand_result(hand)
                    recognizer.set_finger_state()
                gesture = rec_major.get_gesture(settings.profile) if major else None
                active = major
                # Minor pinch cannot preempt a drag, even on a missed major frame.
                if not controller.held and settings.profile == "full" and minor:
                    minor_gesture = rec_minor.get_gesture()
                    if minor_gesture == Gest.PINCH_MINOR:
                        gesture, active = minor_gesture, minor
                if active:
                    point = (active.landmark[9].x, active.landmark[9].y)
                    pinch_point = (active.landmark[8].x, active.landmark[8].y)
                if preview_due:
                    for hand in result.multi_hand_landmarks or []:
                        mp.solutions.drawing_utils.draw_landmarks(frame, hand, mp.solutions.hands.HAND_CONNECTIONS)
            if stop.is_set():
                break
            now = time.monotonic()
            if now-captured > 0.4:
                gesture, point, pinch_point = None, None, None
            controller.update(gesture, point, now, pinch_point)
            if not announced:
                events.put(("state", "Running"))
                announced = True
            count += 1
            if now-fps_start >= 1:
                fps = count/(now-fps_start)
                fps_start, count = now, 0
            processing_ms = (time.perf_counter()-processing_start)*1000
            if preview_due:
                ok, jpeg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 78])
                if ok:
                    latest_put(frames, {"jpeg": jpeg.tobytes(), "gesture": gesture.name if gesture is not None else "NO HAND",
                                        "drag": controller.state.value, "fps": fps, "ms": processing_ms,
                                        "age_ms": (now-captured)*1000, "time": now})
                last_preview = now
    except CameraError as exc:
        events.put(("camera_error", str(exc)))
    except Exception as exc:
        events.put(("error", f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"))
    finally:
        try:
            if controller:
                controller.close()
        finally:
            emergency_release(held)
            if camera:
                camera.close()
            if tracker:
                tracker.close()
            if controls:
                controls.close()
            events.put(("stopped", ""))
