"""Pesos de modelo e bases baixados (porta InventarioDeModelos da tela Sistema)."""
from __future__ import annotations

import os

from infrastructure.caminhos import HOSPITAL_DATA
from infrastructure.ia.mediapipe_pose import POSE_MODEL
from infrastructure.ia.yolo import YOLO_WEIGHTS

AMOSTRA_WAV = os.path.join(HOSPITAL_DATA, "fase4", "samples", "consulta.wav")


def _arquivo(nome: str, caminho: str, comando: str) -> dict:
    ok = os.path.isfile(caminho)
    return {"nome": nome, "ok": ok, "detalhe": "Baixado" if ok else f"Rode {comando}"}


class InventarioLocal:
    def itens(self) -> list[dict]:
        return [
            _arquivo("MediaPipe Pose (vídeo)", POSE_MODEL, "python scripts/download_pose.py"),
            _arquivo("YOLOv8 (vídeo)", YOLO_WEIGHTS, "python scripts/download_yolo.py"),
            _arquivo("Áudio de demonstração", AMOSTRA_WAV, "python scripts/make_demo_audio.py"),
        ]
