"""Baixa pose_landmarker_full.task para models/pose. Uso: python scripts/download_pose.py"""
from __future__ import annotations

import os

import requests

from infrastructure.ia.mediapipe_pose import POSE_MODEL, POSE_MODEL_URL


def main() -> None:
    os.makedirs(os.path.dirname(POSE_MODEL), exist_ok=True)
    if os.path.isfile(POSE_MODEL):
        print(POSE_MODEL)
        return
    partial = POSE_MODEL + ".part"
    with requests.get(POSE_MODEL_URL, stream=True, timeout=60) as response:
        response.raise_for_status()
        with open(partial, "wb") as handle:
            for chunk in response.iter_content(chunk_size=1 << 16):
                handle.write(chunk)
    os.replace(partial, POSE_MODEL)
    print(POSE_MODEL)


if __name__ == "__main__":
    main()
