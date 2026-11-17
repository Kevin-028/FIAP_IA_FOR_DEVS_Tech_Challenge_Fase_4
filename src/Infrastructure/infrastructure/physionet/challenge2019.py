"""Lê os .psv do Challenge 2019 e escolhe a série estável e a série com alerta."""
from __future__ import annotations

import csv
import json
import os
from datetime import datetime, timedelta, timezone

from infrastructure.caminhos import ROOT

DATA = os.path.join(ROOT, "hospital_data", "fase4", "challenge-2019", "training")
CHOICE = os.path.join(ROOT, "hospital_data", "fase4", "challenge2019_demo.json")
BASE = datetime(2019, 4, 1, tzinfo=timezone.utc)
DEMO_HOURS = 36


def _num(value: str | None):
    if value is None:
        return None
    text = value.strip()
    if text in ("", "NaN", "nan"):
        return None
    return float(text)


def read_record(path: str) -> list[dict]:
    rows = []
    with open(path, encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="|"):
            hr, spo2, sbp, dbp = (_num(row.get(name)) for name in ("HR", "O2Sat", "SBP", "DBP"))
            if None in (hr, spo2, sbp, dbp):
                continue
            hour = int(float(row.get("ICULOS") or len(rows) + 1))
            rows.append({
                "recorded_at": (BASE + timedelta(hours=hour)).isoformat(),
                "hr": int(round(hr)),
                "sbp": int(round(sbp)),
                "dbp": int(round(dbp)),
                "spo2": int(round(spo2)),
            })  # SepsisLabel nunca é lido: o sistema não fala de sepse (RN-12)
    return rows


def _abnormal(row: dict) -> bool:
    return (
        row["spo2"] < 92
        or row["hr"] > 120
        or row["hr"] < 45
        or row["sbp"] > 180
        or row["sbp"] < 90
        or row["dbp"] > 110
        or row["dbp"] < 50
    )


def demo_window(rows: list[dict], *, alert: bool) -> list[dict]:
    if not rows:
        return []
    if not alert:
        return rows[:DEMO_HOURS]
    index = next((i for i, row in enumerate(rows) if row["spo2"] < 92), None)
    if index is None:
        index = next((i for i, row in enumerate(rows) if _abnormal(row)), 0)
    start = max(0, index - 24)
    return rows[start:start + DEMO_HOURS]


def find_path(record: str) -> tuple[str, str, str] | None:
    name = record.strip()
    if name.lower().endswith(".psv"):
        name = name[:-4]
    if name and not name.startswith("p"):
        name = "p" + name
    for folder in ("training_setA", "training_setB"):
        path = os.path.join(DATA, folder, name + ".psv")
        if os.path.isfile(path):
            return name, folder, path
    return None


def series_of(record: str, *, role: str | None = None) -> dict | None:
    found = find_path(record)
    if found is None:
        return None
    record_id, folder, path = found
    full = read_record(path)
    if not full:
        return None
    alert = role == "alert" or (role is None and any(_abnormal(row) for row in full))
    rows = demo_window(full, alert=alert)
    return {
        "record": record_id,
        "set": folder,
        "role": "alert" if alert else "stable",
        "rows": rows,
        "diagnosis": "Sinais vitais fora da faixa" if alert else "Sinais vitais estáveis",
        "notes": (
            f"PhysioNet Challenge 2019, {folder}. "
            f"{len(rows)} horas com HR, O2Sat, SBP e DBP."
        ),
    }


def choose() -> dict:
    stable = None
    alert = None
    for folder in ("training_setA", "training_setB"):
        directory = os.path.join(DATA, folder)
        if not os.path.isdir(directory):
            continue
        for name in sorted(os.listdir(directory)):
            if not name.endswith(".psv"):
                continue
            rows = read_record(os.path.join(directory, name))
            if len(rows) < 24:
                continue
            flags = [_abnormal(row) for row in rows]
            record = name[:-4]
            if alert is None and any(flags) and any(row["spo2"] < 92 for row in rows):
                alert = record
            if stable is None and not any(flags):
                stable = record
            if stable and alert:
                break
        if stable and alert:
            break
    if not stable or not alert:
        raise SystemExit("Ainda nao ha arquivos suficientes em hospital_data/fase4/challenge-2019.")
    return {
        stable: {**series_of(stable, role="stable"), "role": "stable"},
        alert: {**series_of(alert, role="alert"), "role": "alert"},
    }


def save_choice(choice: dict | None = None) -> dict:
    choice = choice or choose()
    public = {
        key: {"set": value["set"], "role": value["role"], "hours": len(value["rows"])}
        for key, value in choice.items()
    }
    with open(CHOICE, "w", encoding="utf-8") as handle:
        json.dump(public, handle, ensure_ascii=False, indent=2)
    return choice


def default_patient() -> str:
    if not os.path.isfile(CHOICE):
        return "p000003"
    with open(CHOICE, encoding="utf-8") as handle:
        public = json.load(handle)
    for record, meta in public.items():
        if meta.get("role") == "alert":
            return record
    return next(iter(public), "p000003")


def demo_series() -> dict | None:
    if not os.path.isfile(CHOICE):
        return None
    with open(CHOICE, encoding="utf-8") as handle:
        public = json.load(handle)
    series = {}
    for record, meta in public.items():
        item = series_of(record, role=meta.get("role"))
        if item is None or item["set"] != meta.get("set"):
            return None
        item["role"] = meta.get("role") or item["role"]
        series[record] = item
    return series


class FonteChallenge2019:
    """Porta FonteDeSeries: registros PhysioNet escolhidos para o plantão de demonstração."""

    def serie(self, record: str) -> dict | None:
        return series_of(record)

    def paciente_padrao(self) -> str:
        return default_patient()
