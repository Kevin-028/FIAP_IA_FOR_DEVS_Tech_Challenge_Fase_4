"""MediaPipe Pose: 33 keypoints, substituto executável do OpenPose."""
from __future__ import annotations

_POSE = None


def landmarks_of(frame_bgr):
    global _POSE
    import mediapipe as mp

    if _POSE is None:
        _POSE = mp.solutions.pose.Pose(static_image_mode=True, model_complexity=1)
    rgb = frame_bgr[:, :, ::-1]
    result = _POSE.process(rgb)
    if not result.pose_landmarks:
        return None
    return [(point.x, point.y, point.z) for point in result.pose_landmarks.landmark]
