"""Amostra um vídeo e monta o relatório de desvio."""
from __future__ import annotations

import cv2

from domain.plantao.pose import posture_deviations
from domain.plantao.video_report import build_video_report
from domain.plantao.zones import zone_events

SAFE = (0.2, 0.2, 0.6, 0.6)
FIELD = (0.3, 0.3, 0.3, 0.3)


def analyze_video_file(path: str, *, pose_fn, detect_fn, sample_every: int = 5) -> dict:
    capture = cv2.VideoCapture(path)
    frames = []
    events = []
    index = 0
    sampled = 0
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            if index % sample_every == 0:
                sampled += 1
                landmarks = pose_fn(frame)
                if landmarks is not None:
                    frames.append(landmarks)
                events.extend(zone_events(detect_fn(frame), safe_rect=SAFE, field_rect=FIELD))
            index += 1
    finally:
        capture.release()
    return build_video_report(
        exercise="shoulder_abduction",
        frame_count=sampled,
        deviations=posture_deviations(frames),
        zone_events=events,
    )


class AnalisadorDeVideoOpenCV:
    """Porta AnalisadorDeVideo: OpenCV amostra os quadros, MediaPipe Pose e YOLOv8 analisam.

    Sem o peso de um dos modelos, o vídeo ainda sai, com um aviso de qual faltou.
    """

    def analisar(self, caminho: str) -> tuple[dict, str | None]:
        from infrastructure.ia.mediapipe_pose import landmarks_of
        from infrastructure.ia.yolo import detections_of

        aviso = None

        def _detectar(frame):
            nonlocal aviso
            try:
                return detections_of(frame)
            except FileNotFoundError as exc:
                aviso = str(exc)
                return []

        def _pose(frame):
            nonlocal aviso
            try:
                return landmarks_of(frame)
            except FileNotFoundError as exc:
                aviso = str(exc)
                return None

        return analyze_video_file(caminho, pose_fn=_pose, detect_fn=_detectar), aviso
