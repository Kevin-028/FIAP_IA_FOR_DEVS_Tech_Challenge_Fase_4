"""YOLOv8n para pessoa e objetos na área crítica."""
from __future__ import annotations

import os

from infrastructure.caminhos import ROOT

YOLO_WEIGHTS = os.path.join(ROOT, "models", "yolo", "yolov8n.pt")

_MODEL = None


def detections_of(frame_bgr) -> list[dict]:
    global _MODEL
    if not os.path.isfile(YOLO_WEIGHTS):
        raise FileNotFoundError(
            "Peso YOLOv8 ausente. Rode: python scripts/download_yolo.py"
        )
    if _MODEL is None:
        from ultralytics import YOLO

        _MODEL = YOLO(YOLO_WEIGHTS)
    height, width = frame_bgr.shape[:2]
    found = []
    prediction = _MODEL.predict(frame_bgr, verbose=False)[0]
    for box in prediction.boxes:
        x1, y1, x2, y2 = box.xyxy[0].tolist()
        found.append({
            "label": _MODEL.names[int(box.cls[0])],
            "bbox": (x1 / width, y1 / height, (x2 - x1) / width, (y2 - y1) / height),
            "conf": float(box.conf[0]),
        })
    return found
