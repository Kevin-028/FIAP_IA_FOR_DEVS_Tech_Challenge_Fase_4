"""Números medidos da Fase 4, sem Azure e sem baixar o YOLOv8."""
from __future__ import annotations

import json
import os

import numpy as np

from domain.plantao.fusion import fuse
from domain.plantao.movement import movement_anomalies
from domain.plantao.pose import posture_deviations
from domain.plantao.prescriptions import prescription_anomalies
from domain.plantao.video_report import build_video_report
from domain.plantao.vitals import vital_anomalies
from infrastructure.ia.voz import vocal_features
from domain.plantao.zones import zone_events

DATASET_NOTE = (
    "Pacientes p000057 e p000003: PhysioNet Challenge 2019 (HR, O2Sat, SBP, DBP). "
    "Prescricao e movimento sao evolucao clinica do plantao no mesmo ID. "
    "AudioSet nao e consulta medica; o demo usa fala sintetizada."
)


def _overshoot_frame():
    points = [(0.0, 0.0, 0.0)] * 33
    points[11] = (0.4, 0.4, 0.0)
    points[23] = (0.4, 0.8, 0.0)
    points[13] = (0.4, 0.1, 0.0)
    points[12] = (0.6, 0.4, 0.0)
    points[24] = (0.6, 0.8, 0.0)
    points[14] = (0.6, 0.1, 0.0)
    return points


def run() -> dict:
    deviations = posture_deviations([_overshoot_frame()])
    events = zone_events(
        [{"label": "cell phone", "bbox": (0.35, 0.35, 0.1, 0.1), "conf": 0.9}],
        safe_rect=(0.2, 0.2, 0.6, 0.6),
        field_rect=(0.3, 0.3, 0.3, 0.3),
    )
    video = build_video_report(
        exercise="shoulder_abduction",
        frame_count=1,
        deviations=deviations,
        zone_events=events,
    )
    sample_rate = 16000
    tone = 0.2 * np.sin(2 * np.pi * 220 * np.arange(sample_rate) / sample_rate)
    audio_vocal = vocal_features(np.concatenate([tone, np.zeros(sample_rate)]), sample_rate)
    vitals = vital_anomalies([
        {"recorded_at": "2026-04-05T00:00:00+00:00", "hr": 80, "sbp": 120, "dbp": 80, "spo2": 97},
        {"recorded_at": "2026-04-05T01:00:00+00:00", "hr": 132, "sbp": 120, "dbp": 80, "spo2": 88},
    ])
    prescriptions = prescription_anomalies([
        {"recorded_at": "2026-04-01T08:00:00+00:00", "drug": "AAS", "dose_mg": 100, "route": "oral", "action": "start"},
        {"recorded_at": "2026-04-03T08:00:00+00:00", "drug": "varfarina", "dose_mg": 5, "route": "oral", "action": "start"},
        {"recorded_at": "2026-04-03T20:00:00+00:00", "drug": "AAS", "dose_mg": 300, "route": "oral", "action": "change"},
    ])
    movement_rows = [
        {"recorded_at": f"2026-04-05T{hour}:00:00+00:00", "posture": "supine", "zone": "bed"}
        for hour in range(18, 24)
    ]
    movement_rows += [
        {"recorded_at": f"2026-04-06T0{hour}:00:00+00:00", "posture": "supine", "zone": "bed"}
        for hour in range(0, 3)
    ]
    movement_rows.append({
        "recorded_at": "2026-04-06T02:30:00+00:00",
        "posture": "standing",
        "zone": "corridor",
    })
    movement = movement_anomalies(movement_rows)
    fusion = fuse(
        video=video,
        audio={
            "sentiment": "negative",
            "critical_terms": ["falta de ar"],
            "vocal": audio_vocal,
        },
        vitals=vitals,
        prescriptions=prescriptions,
        movement=movement,
        chart_text="paciente sintetico",
    )
    return {
        "video": video,
        "audio_vocal": audio_vocal,
        "vitals": vitals,
        "prescriptions": prescriptions,
        "movement": movement,
        "fusion": fusion,
        "datasets": {
            "urls": ["https://physionet.org/", "https://research.google.com/audioset/"],
            "note": DATASET_NOTE,
        },
    }


def main() -> None:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    folder = os.path.join(root, "hospital_data", "fase4")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, "results.json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(run(), handle, ensure_ascii=False, indent=2)
    print(path)


if __name__ == "__main__":
    main()
