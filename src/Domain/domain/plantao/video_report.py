"""Relatório automático do vídeo clínico."""
from __future__ import annotations

OPENPOSE_NOTE = (
    "MediaPipe Pose cumpre a tarefa de keypoints citada como OpenPose "
    "e roda no Windows sem compilar o OpenPose."
)


def build_video_report(*, exercise: str, frame_count: int, deviations: list, zone_events: list) -> dict:
    hits = len(deviations) + len(zone_events)
    if hits:
        summary = f"Desvio detectado em {hits} evento(s) de {exercise}."
    else:
        summary = f"Sem desvio em {exercise}."
    return {
        "exercise": exercise,
        "models": ["mediapipe-pose", "yolov8n"],
        "openpose_note": OPENPOSE_NOTE,
        "frame_count": frame_count,
        "deviations": deviations,
        "zone_events": list(zone_events),
        "summary": summary,
    }
