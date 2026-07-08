"""
Real-time Face Detection + Hand/Fingertip Landmark Detection + Air Paint
--------------------------------------------------------------------------
Uses the modern MediaPipe Tasks API:
    - FaceDetector      -> pixelates (censors) every detected face
    - HandLandmarker     -> draws full hand skeleton (21 landmarks per hand,
                             including all fingertips)

Also includes an "air paint" mode: draw on screen using your index
fingertip, change colors with number keys, and clear the canvas with
either a closed fist gesture or a key press.

All detectors run on the same webcam feed, frame by frame, in a single
OpenCV window.

Models are downloaded automatically on first run (see MODEL_URLS below)
and cached locally in the "models/" folder next to this script.

Controls:
    q       -> quit
    p       -> toggle paint mode on/off
    c       -> clear the paint canvas
    1-5     -> change paint color
    (fist)  -> hold a closed fist to clear the canvas (while paint mode is on)
"""

import os
import sys
import time
import urllib.request

import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(SCRIPT_DIR, "models")

FACE_MODEL_PATH = os.path.join(MODELS_DIR, "blaze_face_short_range.tflite")
HAND_MODEL_PATH = os.path.join(MODELS_DIR, "hand_landmarker.task")

# Each model has one or more candidate URLs. Some MediaPipe model paths
# occasionally return 403 on "latest" (e.g. hand_landmarker); a pinned
# version number (e.g. "/1/") is used as a reliable fallback.
MODEL_URLS = {
    FACE_MODEL_PATH: [
        "https://storage.googleapis.com/mediapipe-models/face_detector/"
        "blaze_face_short_range/float16/1/blaze_face_short_range.tflite",
        "https://storage.googleapis.com/mediapipe-models/face_detector/"
        "blaze_face_short_range/float16/latest/blaze_face_short_range.tflite",
    ],
    HAND_MODEL_PATH: [
        "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
        "hand_landmarker/float16/1/hand_landmarker.task",
        "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
        "hand_landmarker/float16/latest/hand_landmarker.task",
    ],
}

NUM_HANDS = 2
MIN_FACE_DETECTION_CONFIDENCE = 0.5
MIN_HAND_DETECTION_CONFIDENCE = 0.5
MIN_HAND_PRESENCE_CONFIDENCE = 0.5
MIN_HAND_TRACKING_CONFIDENCE = 0.5

# --- Face censoring (pixelation) ---
CENSOR_FACE = True          # set to False to go back to drawing a plain box
PIXELATION_BLOCKS = 12      # lower = blockier / stronger censor, higher = finer detail
FACE_BOX_PADDING = 0.25     # extra margin around the detected face box (fraction of box size)

# --- Air paint mode (draw with the index fingertip) ---
PAINT_LINE_THICKNESS = 6
FIST_PINCH_FRAMES = 5        # consecutive frames a fist must be held before the canvas clears
PAINT_COLORS = [
    (0, 255, 140),   # 1 - phosphor green
    (0, 255, 255),   # 2 - cyan
    (255, 100, 0),   # 3 - electric blue
    (0, 0, 255),     # 4 - red
    (255, 0, 255),   # 5 - magenta
]

CAM_INDEX = 0
CAM_WIDTH = 1280
CAM_HEIGHT = 720

# Fingertip landmark indices in MediaPipe's 21-point hand model
FINGERTIP_IDS = {
    "THUMB_TIP": 4,
    "INDEX_FINGER_TIP": 8,
    "MIDDLE_FINGER_TIP": 12,
    "RING_FINGER_TIP": 16,
    "PINKY_TIP": 20,
}

# Colors (BGR) - phosphor terminal style
COLOR_FACE_BOX = (0, 255, 140)
COLOR_FACE_KEYPOINT = (0, 255, 255)
COLOR_HAND_CONNECTION = (0, 255, 140)
COLOR_HAND_LANDMARK = (0, 200, 255)
COLOR_FINGERTIP = (0, 0, 255)
COLOR_TEXT = (0, 255, 140)

# Hand skeleton connections (pairs of landmark indices), standard MediaPipe layout
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),          # thumb
    (0, 5), (5, 6), (6, 7), (7, 8),          # index finger
    (5, 9), (9, 10), (10, 11), (11, 12),     # middle finger
    (9, 13), (13, 14), (14, 15), (15, 16),   # ring finger
    (13, 17), (17, 18), (18, 19), (19, 20),  # pinky
    (0, 17),                                  # palm base
]


# ---------------------------------------------------------------------------
# Model download helper
# ---------------------------------------------------------------------------

def ensure_models_downloaded():
    """Download required .tflite / .task model files if not already present."""
    os.makedirs(MODELS_DIR, exist_ok=True)

    for model_path, candidate_urls in MODEL_URLS.items():
        if os.path.exists(model_path) and os.path.getsize(model_path) > 1024:
            continue

        print(f"[INFO] Downloading model: {os.path.basename(model_path)}")

        last_error = None
        for url in candidate_urls:
            try:
                urllib.request.urlretrieve(url, model_path)
                print(f"[INFO] Saved to: {model_path}")
                break
            except Exception as e:
                last_error = e
                print(f"[WARNING] Failed from {url}")
                print(f"[WARNING] {e}")
                if os.path.exists(model_path):
                    os.remove(model_path)
        else:
            print(f"[ERROR] All download attempts failed for {os.path.basename(model_path)}")
            print(f"[ERROR] {last_error}")
            print(
                "[ERROR] Check your internet connection, or download the file "
                "manually and place it in the 'models' folder using this exact name: "
                f"{os.path.basename(model_path)}"
            )
            sys.exit(1)


# ---------------------------------------------------------------------------
# Detector setup
# ---------------------------------------------------------------------------

def build_face_detector():
    base_options = mp_python.BaseOptions(model_asset_path=FACE_MODEL_PATH)
    options = mp_vision.FaceDetectorOptions(
        base_options=base_options,
        running_mode=mp_vision.RunningMode.VIDEO,
        min_detection_confidence=MIN_FACE_DETECTION_CONFIDENCE,
    )
    return mp_vision.FaceDetector.create_from_options(options)


def build_hand_landmarker():
    base_options = mp_python.BaseOptions(model_asset_path=HAND_MODEL_PATH)
    options = mp_vision.HandLandmarkerOptions(
        base_options=base_options,
        running_mode=mp_vision.RunningMode.VIDEO,
        num_hands=NUM_HANDS,
        min_hand_detection_confidence=MIN_HAND_DETECTION_CONFIDENCE,
        min_hand_presence_confidence=MIN_HAND_PRESENCE_CONFIDENCE,
        min_tracking_confidence=MIN_HAND_TRACKING_CONFIDENCE,
    )
    return mp_vision.HandLandmarker.create_from_options(options)


# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------

def pixelate_region(frame, x1, y1, x2, y2, blocks=PIXELATION_BLOCKS):
    """Pixelate the rectangular region of `frame` given by (x1, y1)-(x2, y2) in place."""
    h, w = frame.shape[:2]

    # Clamp coordinates to stay inside the frame
    x1 = max(0, min(x1, w - 1))
    y1 = max(0, min(y1, h - 1))
    x2 = max(0, min(x2, w))
    y2 = max(0, min(y2, h))

    if x2 <= x1 or y2 <= y1:
        return

    roi = frame[y1:y2, x1:x2]
    roi_h, roi_w = roi.shape[:2]

    # Downscale then upscale with nearest-neighbor interpolation -> blocky pixelation
    small_w = max(1, roi_w // blocks)
    small_h = max(1, roi_h // blocks)

    temp = cv2.resize(roi, (small_w, small_h), interpolation=cv2.INTER_LINEAR)
    pixelated = cv2.resize(temp, (roi_w, roi_h), interpolation=cv2.INTER_NEAREST)

    frame[y1:y2, x1:x2] = pixelated


def censor_face_detections(frame, detection_result):
    """Pixelate every detected face region to censor identity."""
    for detection in detection_result.detections:
        bbox = detection.bounding_box
        x, y, bw, bh = bbox.origin_x, bbox.origin_y, bbox.width, bbox.height

        # Add padding so the pixelation fully covers the face, including edges/hair
        pad_x = int(bw * FACE_BOX_PADDING)
        pad_y = int(bh * FACE_BOX_PADDING)

        x1 = x - pad_x
        y1 = y - pad_y
        x2 = x + bw + pad_x
        y2 = y + bh + pad_y

        pixelate_region(frame, x1, y1, x2, y2)


def draw_face_boxes_only(frame, detection_result):
    """Fallback (non-censoring) view: draw bounding box + keypoints, no pixelation."""
    h, w = frame.shape[:2]

    for detection in detection_result.detections:
        bbox = detection.bounding_box
        x, y, bw, bh = bbox.origin_x, bbox.origin_y, bbox.width, bbox.height

        cv2.rectangle(frame, (x, y), (x + bw, y + bh), COLOR_FACE_BOX, 2)

        score = detection.categories[0].score if detection.categories else 0.0
        label = f"FACE {score * 100:.1f}%"
        cv2.putText(
            frame, label, (x, max(y - 10, 0)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLOR_FACE_BOX, 2, cv2.LINE_AA,
        )

        for keypoint in detection.keypoints:
            kp_x = int(keypoint.x * w)
            kp_y = int(keypoint.y * h)
            cv2.circle(frame, (kp_x, kp_y), 3, COLOR_FACE_KEYPOINT, -1)


def draw_hand_landmarks(frame, detection_result):
    """Draw full hand skeleton and highlight fingertips for every detected hand."""
    h, w = frame.shape[:2]

    if not detection_result.hand_landmarks:
        return

    for hand_index, hand_landmarks in enumerate(detection_result.hand_landmarks):
        points = [(int(lm.x * w), int(lm.y * h)) for lm in hand_landmarks]

        # Skeleton connections
        for start_idx, end_idx in HAND_CONNECTIONS:
            cv2.line(frame, points[start_idx], points[end_idx], COLOR_HAND_CONNECTION, 2)

        # All landmarks
        for point in points:
            cv2.circle(frame, point, 4, COLOR_HAND_LANDMARK, -1)

        # Fingertips highlighted + labeled
        for tip_name, tip_idx in FINGERTIP_IDS.items():
            tip_point = points[tip_idx]
            cv2.circle(frame, tip_point, 8, COLOR_FINGERTIP, 2)

        # Handedness label (Left / Right) near the wrist
        if detection_result.handedness:
            handedness = detection_result.handedness[hand_index][0].category_name
            wrist_point = points[0]
            cv2.putText(
                frame, handedness.upper(),
                (wrist_point[0] - 20, wrist_point[1] + 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLOR_HAND_LANDMARK, 2, cv2.LINE_AA,
            )


def draw_fps(frame, fps):
    cv2.putText(
        frame, f"FPS: {fps:.1f}", (15, 30),
        cv2.FONT_HERSHEY_SIMPLEX, 0.7, COLOR_TEXT, 2, cv2.LINE_AA,
    )


# ---------------------------------------------------------------------------
# Air paint mode: draw with the index fingertip, clear with a fist gesture
# ---------------------------------------------------------------------------

# For each non-thumb finger: (tip_idx, pip_idx) - a finger counts as "up" if
# the tip is above (smaller y) than its PIP joint by a margin.
FINGER_TIP_PIP_PAIRS = [
    (8, 6),    # index
    (12, 10),  # middle
    (16, 14),  # ring
    (20, 18),  # pinky
]


def is_index_finger_up(landmarks_px):
    """Return True if the index fingertip is extended (raised) above its PIP joint."""
    tip_y = landmarks_px[8][1]
    pip_y = landmarks_px[6][1]
    return tip_y < pip_y - 10  # small margin to avoid jitter around the threshold


def is_fist(landmarks_px):
    """Return True if all four non-thumb fingers are curled down (a closed fist)."""
    for tip_idx, pip_idx in FINGER_TIP_PIP_PAIRS:
        tip_y = landmarks_px[tip_idx][1]
        pip_y = landmarks_px[pip_idx][1]
        if tip_y < pip_y - 10:
            # this finger is extended -> not a fist
            return False
    return True


def draw_paint_hint(frame):
    """Shown when paint mode is off, so the user always sees how to enable it."""
    h, w = frame.shape[:2]
    cv2.putText(
        frame, "PAINT: OFF (press 'p' to enable)", (15, h - 20),
        cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLOR_TEXT, 2, cv2.LINE_AA,
    )


def draw_paint_ui(frame, paint_color, paint_enabled):
    """Show the current paint mode status and color swatch in the corner."""
    h, w = frame.shape[:2]
    status = "PAINT: ON" if paint_enabled else "PAINT: OFF (press 'p')"
    cv2.putText(
        frame, status, (15, h - 45),
        cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLOR_TEXT, 2, cv2.LINE_AA,
    )
    cv2.rectangle(frame, (15, h - 35), (45, h - 15), paint_color, -1)
    cv2.rectangle(frame, (15, h - 35), (45, h - 15), (255, 255, 255), 1)
    cv2.putText(
        frame, "1-5 color | fist to clear | c clear",
        (55, h - 20),
        cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLOR_TEXT, 1, cv2.LINE_AA,
    )


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def main():
    ensure_models_downloaded()

    print("[INFO] Loading face detector...")
    face_detector = build_face_detector()

    print("[INFO] Loading hand landmarker...")
    hand_landmarker = build_hand_landmarker()

    print(f"[INFO] Opening webcam (index {CAM_INDEX})...")
    cap = cv2.VideoCapture(CAM_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAM_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM_HEIGHT)

    if not cap.isOpened():
        print("[ERROR] Could not open webcam. Check CAM_INDEX or camera permissions.")
        sys.exit(1)

    window_name = "Face + Hand Detector"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

    prev_time = time.time()

    # Paint mode state
    paint_enabled = False
    paint_color = PAINT_COLORS[0]
    canvas = None            # created lazily once we know the frame size
    prev_index_point = None  # last index fingertip position, for drawing a continuous line
    fist_hold_counter = 0    # consecutive frames a fist has been held (debounce for clearing)

    print("[INFO] Running. Press 'q' to quit, 'p' to toggle paint mode, 'c' to clear canvas.")

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("[WARNING] Failed to read frame from webcam.")
                break

            frame = cv2.flip(frame, 1)  # mirror view, more intuitive for the user

            if canvas is None:
                canvas = np.zeros_like(frame)

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

            timestamp_ms = int(time.time() * 1000)

            face_result = face_detector.detect_for_video(mp_image, timestamp_ms)
            hand_result = hand_landmarker.detect_for_video(mp_image, timestamp_ms)

            if CENSOR_FACE:
                censor_face_detections(frame, face_result)
            else:
                draw_face_boxes_only(frame, face_result)

            draw_hand_landmarks(frame, hand_result)

            # --- Air paint logic ---
            if paint_enabled and hand_result.hand_landmarks:
                h, w = frame.shape[:2]
                # Use the first detected hand for drawing
                hand_landmarks = hand_result.hand_landmarks[0]
                points_px = [(int(lm.x * w), int(lm.y * h)) for lm in hand_landmarks]

                if is_fist(points_px):
                    fist_hold_counter += 1
                    prev_index_point = None  # lift the "pen" while fist is closed
                    if fist_hold_counter == FIST_PINCH_FRAMES:
                        canvas[:] = 0
                        print("[INFO] Canvas cleared (fist gesture).")
                else:
                    fist_hold_counter = 0

                    if is_index_finger_up(points_px):
                        index_point = points_px[8]  # index fingertip
                        if prev_index_point is not None:
                            cv2.line(
                                canvas, prev_index_point, index_point,
                                paint_color, PAINT_LINE_THICKNESS, cv2.LINE_AA,
                            )
                        prev_index_point = index_point
                    else:
                        prev_index_point = None  # pen lifted (index finger not raised)
            else:
                fist_hold_counter = 0
                prev_index_point = None

            # Composite the paint canvas onto the live frame
            mask = canvas.astype(bool).any(axis=2)
            frame[mask] = canvas[mask]

            if paint_enabled:
                draw_paint_ui(frame, paint_color, paint_enabled)
            else:
                draw_paint_hint(frame)

            current_time = time.time()
            fps = 1.0 / max(current_time - prev_time, 1e-6)
            prev_time = current_time
            draw_fps(frame, fps)

            cv2.imshow(window_name, frame)

            key = cv2.waitKey(1) & 0xFF
            if key != 255:  # 255 means "no key pressed this frame"
                print(f"[DEBUG] Key pressed: {key} ('{chr(key) if 32 <= key <= 126 else '?'}')")

            if key == ord("q"):
                print("[INFO] Quit key pressed. Exiting.")
                break
            elif key == ord("p"):
                paint_enabled = not paint_enabled
                prev_index_point = None
                print(f"[INFO] Paint mode {'enabled' if paint_enabled else 'disabled'}.")
            elif key == ord("c"):
                canvas[:] = 0
                print("[INFO] Canvas cleared (key press).")
            elif key in (ord("1"), ord("2"), ord("3"), ord("4"), ord("5")):
                color_index = key - ord("1")
                paint_color = PAINT_COLORS[color_index]
                print(f"[INFO] Paint color changed to slot {color_index + 1}.")

    finally:
        cap.release()
        cv2.destroyAllWindows()
        face_detector.close()
        hand_landmarker.close()


if __name__ == "__main__":
    main()
