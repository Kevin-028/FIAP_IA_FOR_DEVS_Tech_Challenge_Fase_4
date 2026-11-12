"""Imobilidade prolongada e saída noturna do leito."""
from __future__ import annotations

from datetime import datetime

_NIGHT = {22, 23, 0, 1, 2, 3, 4, 5}


def movement_anomalies(rows: list[dict]) -> list[dict]:
    ordered = sorted(rows, key=lambda row: row["recorded_at"])
    found = []
    group: list[dict] = []

    def _close(items: list[dict]) -> None:
        if len(items) < 2:
            return
        start = datetime.fromisoformat(items[0]["recorded_at"])
        end = datetime.fromisoformat(items[-1]["recorded_at"])
        hours = int((end - start).total_seconds() // 3600)
        if hours >= 4:
            last = items[-1]
            found.append({
                "recorded_at": last["recorded_at"],
                "severity": "high",
                "rule": "immobility",
                "detail": f"{last['posture']}/{last['zone']} por {hours} h",
            })

    for row in ordered:
        if group and (row["posture"], row["zone"]) != (group[-1]["posture"], group[-1]["zone"]):
            _close(group)
            group = []
        group.append(row)
        stamp = datetime.fromisoformat(row["recorded_at"])
        if row["zone"] == "corridor" and stamp.hour in _NIGHT:
            found.append({
                "recorded_at": row["recorded_at"],
                "severity": "high",
                "rule": "night_exit",
                "detail": "saida noturna no corredor",
            })
    _close(group)
    return found
