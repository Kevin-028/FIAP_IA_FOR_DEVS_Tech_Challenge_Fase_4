"""Um ponto de monitoramento por vez."""
from __future__ import annotations

from hospital.db import insert_movement, insert_vital, list_movement, list_prescriptions, list_vitals
from multimodal.fusion import fuse
from multimodal.movement import movement_anomalies
from multimodal.prescriptions import prescription_anomalies
from multimodal.publish import publish
from multimodal.vitals import vital_anomalies


def reset_monitor(conn, patient_id: str) -> None:
    conn.execute("DELETE FROM vitals WHERE patient_id = ?", (patient_id,))
    conn.execute("DELETE FROM movement_events WHERE patient_id = ?", (patient_id,))
    conn.execute("DELETE FROM alerts WHERE thread_id = ?", (f"fase4-{patient_id}",))
    conn.commit()


def tick(conn, patient_id: str, *, vital, movement, video=None, audio=None, chart_text: str = "") -> dict:
    if vital is not None:
        insert_vital(
            conn,
            patient_id,
            vital["recorded_at"],
            vital["hr"],
            vital["sbp"],
            vital["dbp"],
            vital["spo2"],
        )
    if movement is not None:
        insert_movement(
            conn,
            patient_id,
            movement["recorded_at"],
            movement["posture"],
            movement["zone"],
        )
    conn.commit()
    result = fuse(
        video=video,
        audio=audio,
        vitals=vital_anomalies(list_vitals(conn, patient_id)),
        prescriptions=prescription_anomalies(list_prescriptions(conn, patient_id)),
        movement=movement_anomalies(list_movement(conn, patient_id)),
        chart_text=chart_text,
    )
    return {"level": result["level"], "new_alerts": publish(conn, patient_id, result), "fusion": result}
