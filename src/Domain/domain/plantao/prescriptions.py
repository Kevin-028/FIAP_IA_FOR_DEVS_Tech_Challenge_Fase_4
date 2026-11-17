"""Droga de alerta e salto de dose. Não emite ordem de administrar."""
from __future__ import annotations

HIGH_ALERT_STEMS = (
    "warfarin",
    "varfarina",
    "insulina",
    "insulin",
    "morfina",
    "morphine",
    "fentanil",
    "fentanyl",
)


def prescription_anomalies(rows: list[dict]) -> list[dict]:
    last_dose: dict[str, float] = {}
    found = []
    for row in rows:
        key = row["drug"].casefold()
        if row["action"] in ("start", "change") and any(stem in key for stem in HIGH_ALERT_STEMS):
            found.append({
                "recorded_at": row["recorded_at"],
                "drug": row["drug"],
                "severity": "high",
                "rule": "high_alert_start",
                "detail": f"inicio de {row['drug']}",
            })
        previous = last_dose.get(key)
        if previous and previous > 0 and row["dose_mg"] / previous >= 2:
            found.append({
                "recorded_at": row["recorded_at"],
                "drug": row["drug"],
                "severity": "high",
                "rule": "dose_jump",
                "detail": f"dose de {row['drug']} de {previous:.0f} mg para {row['dose_mg']:.0f} mg",
            })
        last_dose[key] = float(row["dose_mg"])
    return found
