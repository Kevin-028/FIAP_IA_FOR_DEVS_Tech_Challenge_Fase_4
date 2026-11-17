"""Pacientes do PhysioNet Challenge 2019 + evolução clínica do plantão."""
from __future__ import annotations

from datetime import datetime, timedelta

from infrastructure.persistencia.banco import (
    connect,
    init_db,
    insert_movement,
    insert_prescription,
    insert_vital,
)


def _hours(start: str, n: int) -> list[str]:
    base = datetime.fromisoformat(start)
    return [(base + timedelta(hours=i)).replace(microsecond=0).isoformat() for i in range(n)]


def _shift(stamp: str, **delta) -> str:
    return (datetime.fromisoformat(stamp) + timedelta(**delta)).replace(microsecond=0).isoformat()


def seed_clinical(conn, patient_id: str, rows: list[dict], *, alert: bool) -> None:
    conn.execute("DELETE FROM prescriptions WHERE patient_id = ?", (patient_id,))
    conn.execute("DELETE FROM movement_events WHERE patient_id = ?", (patient_id,))
    if not rows:
        return
    first = rows[0]["recorded_at"]
    if alert:
        insert_prescription(conn, patient_id, _shift(first, days=-4), "AAS", 100, "oral", "start")
        insert_prescription(conn, patient_id, _shift(first, days=-3), "AAS", 100, "oral", "change")
        insert_prescription(conn, patient_id, _shift(first, days=-2), "varfarina", 5, "oral", "start")
        insert_prescription(conn, patient_id, _shift(first, days=-1, hours=12), "AAS", 300, "oral", "change")
        bed_start = rows[max(0, len(rows) - 10)]["recorded_at"]
        bed_stamps = _hours(bed_start, 9)
        for stamp in bed_stamps:
            insert_movement(conn, patient_id, stamp, "supine", "bed")
        last_bed = datetime.fromisoformat(bed_stamps[-1])
        corridor = last_bed.replace(hour=2, minute=30, second=0, microsecond=0)
        if corridor <= last_bed:
            corridor = corridor + timedelta(days=1)
        insert_movement(conn, patient_id, corridor.isoformat(), "standing", "corridor")
    else:
        insert_prescription(conn, patient_id, _shift(first, days=-1), "AAS", 100, "oral", "start")
        insert_movement(conn, patient_id, first, "sitting", "chair")
        if len(rows) > 1:
            insert_movement(conn, patient_id, rows[1]["recorded_at"], "sitting", "chair")


def store_patient(conn, item: dict) -> None:
    conn.execute(
        """
        INSERT INTO patients
            (id, display_name, chart_hash, cpf_hash, birth_year, sex, allergies, diagnosis, notes)
        VALUES (?, ?, ?, 'physionet', NULL, NULL, '', ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            display_name = excluded.display_name,
            diagnosis = excluded.diagnosis,
            notes = excluded.notes
        """,
        (item["record"], item["record"], item["record"], item["diagnosis"], item["notes"]),
    )
    conn.execute("DELETE FROM vitals WHERE patient_id = ?", (item["record"],))
    for row in item["rows"]:
        insert_vital(
            conn,
            item["record"],
            row["recorded_at"],
            row["hr"],
            row["sbp"],
            row["dbp"],
            row["spo2"],
        )
    seed_clinical(conn, item["record"], item["rows"], alert=item.get("role") == "alert")
    conn.commit()


def apply(conn) -> None:
    init_db(conn)
    for table in ("vitals", "prescriptions", "movement_events", "modality_reports"):
        conn.execute(f"DELETE FROM {table}")
    from infrastructure.physionet.challenge2019 import demo_series

    series = demo_series()
    if series:
        for item in series.values():
            store_patient(conn, item)
        return
    for patient_id, abnormal in (("PAC-0001", False), ("PAC-0002", True)):
        conn.execute(
            """
            INSERT INTO patients
                (id, display_name, chart_hash, cpf_hash, birth_year, sex, allergies, diagnosis, notes)
            VALUES (?, ?, 'h', 'c', 1980, 'F', '', 'sintetico', 'nota')
            ON CONFLICT(id) DO NOTHING
            """,
            (patient_id, patient_id),
        )
        stamps = _hours("2026-04-05T00:00:00+00:00", 30)
        rows = []
        for index, stamp in enumerate(stamps):
            last = abnormal and index == len(stamps) - 1
            row = {
                "recorded_at": stamp,
                "hr": 132 if last else 80,
                "sbp": 120,
                "dbp": 80,
                "spo2": 88 if last else 97,
            }
            rows.append(row)
            insert_vital(conn, patient_id, stamp, row["hr"], row["sbp"], row["dbp"], row["spo2"])
        seed_clinical(conn, patient_id, rows, alert=abnormal)
    conn.commit()


def main() -> None:
    conn = connect()
    apply(conn)
    conn.close()
    print("Pacientes do Challenge 2019 gravados.")


if __name__ == "__main__":
    main()
