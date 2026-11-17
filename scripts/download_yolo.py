"""Baixa yolov8n.pt para models/yolo. Uso: python scripts/download_yolo.py"""
from __future__ import annotations

import os
import shutil

from infrastructure.ia.yolo import YOLO_WEIGHTS


def main() -> None:
    os.makedirs(os.path.dirname(YOLO_WEIGHTS), exist_ok=True)
    if os.path.isfile(YOLO_WEIGHTS):
        print(YOLO_WEIGHTS)
        return
    from ultralytics import YOLO

    model = YOLO("yolov8n.pt")
    source = getattr(model, "ckpt_path", None) or os.path.join(os.getcwd(), "yolov8n.pt")
    if os.path.abspath(source) != os.path.abspath(YOLO_WEIGHTS) and os.path.isfile(source):
        shutil.copy(source, YOLO_WEIGHTS)
    if not os.path.isfile(YOLO_WEIGHTS):
        raise SystemExit("yolov8n.pt nao encontrado em models/yolo")
    print(YOLO_WEIGHTS)


if __name__ == "__main__":
    main()
