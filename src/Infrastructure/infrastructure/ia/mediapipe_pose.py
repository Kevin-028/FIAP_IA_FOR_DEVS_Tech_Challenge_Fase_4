"""MediaPipe Pose Landmarker (Tasks API): 33 keypoints, substituto executável do OpenPose."""
from __future__ import annotations

import os

from infrastructure.caminhos import ROOT

POSE_MODEL = os.path.join(ROOT, "models", "pose", "pose_landmarker_full.task")
POSE_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
    "pose_landmarker_full/float16/latest/pose_landmarker_full.task"
)

_LANDMARKER = None


def _landmarker():
    global _LANDMARKER
    if _LANDMARKER is None:
        if not os.path.isfile(POSE_MODEL):
            raise FileNotFoundError(
                "Modelo MediaPipe Pose ausente. Rode: python scripts/download_pose.py"
            )
        from mediapipe.tasks.python import BaseOptions
        from mediapipe.tasks.python.vision import (
            PoseLandmarker,
            PoseLandmarkerOptions,
            RunningMode,
        )

        options = PoseLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=POSE_MODEL),
            running_mode=RunningMode.IMAGE,
            num_poses=1,
        )
        _LANDMARKER = PoseLandmarker.create_from_options(options)
    return _LANDMARKER


def landmarks_of(frame_bgr):
    import mediapipe as mp
    import numpy as np

    rgb = np.ascontiguousarray(frame_bgr[:, :, ::-1])
    image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    result = _landmarker().detect(image)
    if not result.pose_landmarks:
        return None
    return [(point.x, point.y, point.z) for point in result.pose_landmarks[0]]
