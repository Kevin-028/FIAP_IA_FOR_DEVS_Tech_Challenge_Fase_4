"""Grava achados da fusão na fila de alertas já existente."""
from __future__ import annotations

from hospital.db import emit_alert


def publish(conn, patient_id: str, result: dict) -> list[str]:
    if result.get("level") != "high":
        return []
    created = []
    thread_id = f"fase4-{patient_id}"
    for finding in result["findings"]:
        if emit_alert(
            conn,
            patient_id=patient_id,
            thread_id=thread_id,
            severity=finding["severity"],
            reason=finding["reason"],
            source=finding["source"],
        ):
            created.append(finding["reason"])
    return created
