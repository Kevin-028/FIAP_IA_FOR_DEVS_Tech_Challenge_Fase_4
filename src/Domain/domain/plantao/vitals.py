"""Regras clínicas e Isolation Forest para FC, pressão e SpO2."""
from __future__ import annotations

import numpy as np
from sklearn.ensemble import IsolationForest

_RULES = (
    ("spo2", "spo2_low", lambda row: row["spo2"] < 92),
    ("hr", "hr_high", lambda row: row["hr"] > 120),
    ("hr", "hr_low", lambda row: row["hr"] < 45),
    ("sbp", "sbp_high", lambda row: row["sbp"] > 180),
    ("sbp", "sbp_low", lambda row: row["sbp"] < 90),
    ("dbp", "dbp_high", lambda row: row["dbp"] > 110),
    ("dbp", "dbp_low", lambda row: row["dbp"] < 50),
)


def isolation_outlier_indexes(matrix) -> list[int]:
    array = np.asarray(matrix, dtype=float)
    if len(array) < 24:
        return []
    if np.all(array.std(axis=0) < 1e-6):
        return []
    model = IsolationForest(n_estimators=50, contamination=0.05, random_state=0)
    flags = model.fit_predict(array)
    return [index for index, flag in enumerate(flags) if flag == -1]


def vital_anomalies(rows: list[dict]) -> list[dict]:
    found = []
    covered = set()
    for index, row in enumerate(rows):
        for signal, rule, check in _RULES:
            if check(row):
                covered.add(index)
                found.append({
                    "recorded_at": row["recorded_at"],
                    "signal": signal,
                    "value": float(row[signal]),
                    "severity": "high",
                    "rule": rule,
                })
    if len(rows) >= 24:
        matrix = np.array([[row["hr"], row["sbp"], row["dbp"], row["spo2"]] for row in rows], dtype=float)
        std = matrix.std(axis=0)
        scale = np.maximum(std, 1e-6)
        zscore = np.max(np.abs((matrix - matrix.mean(axis=0)) / scale), axis=1)
        for index in isolation_outlier_indexes(matrix):
            if index in covered or zscore[index] < 3:
                continue
            row = rows[index]
            found.append({
                "recorded_at": row["recorded_at"],
                "signal": "multivariate",
                "value": float(row["hr"]),
                "severity": "high",
                "rule": "isolation_forest",
            })
    return found
