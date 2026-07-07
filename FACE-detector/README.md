# Face + Hand/Fingertip Detector

Real-time face detection and hand skeleton (fingertip) tracking from a webcam feed,
in a single script, using the MediaPipe **Tasks API**.

## Setup

```bash
pip install -r requirements.txt
```

## Run

```bash
python detector.py
```

On the **first run**, the script automatically downloads two small model files
into a local `models/` folder:

- `blaze_face_short_range.tflite` — face detector
- `hand_landmarker.task` — hand landmark model (21 points per hand)

This requires an internet connection the first time only. After that, the models
are cached locally and no further downloads happen.

## Controls

- Press `q` in the video window to quit.

## What it draws

- **Face:** bounding box + confidence score + face keypoints (eyes, nose, mouth, ears).
- **Hands:** full 21-point skeleton per hand, all landmarks marked, fingertips
  (thumb, index, middle, ring, pinky) highlighted with a larger red circle,
  and a Left/Right label near the wrist.
- **FPS counter** in the top-left corner.

## Configuration

All tunable values are at the top of `detector.py`:

- `CAM_INDEX` — change if you have multiple cameras (0, 1, 2, ...)
- `CAM_WIDTH` / `CAM_HEIGHT` — capture resolution
- `NUM_HANDS` — max number of hands to track simultaneously (default: 2)
- `MIN_FACE_DETECTION_CONFIDENCE`, `MIN_HAND_DETECTION_CONFIDENCE`, etc. — detection thresholds

## Notes

- If the webcam doesn't open, try changing `CAM_INDEX` to `1` or `2`.
- If detection feels laggy, lower `CAM_WIDTH`/`CAM_HEIGHT` (e.g. 640x480).
- Model download URLs point to Google's official MediaPipe model storage
  (`storage.googleapis.com`). If that domain is blocked on your network,
  download the two files manually from the MediaPipe docs and place them in
  the `models/` folder using the exact filenames above.
