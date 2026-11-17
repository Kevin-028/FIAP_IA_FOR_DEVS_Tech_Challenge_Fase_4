"""Regras clínicas para FC, pressão e SpO2, mais o filtro de outlier multivariado.

O detector de outlier (Isolation Forest) é uma porta: o domínio só decide o que conta como anomalia.
"""
from __future__ import annotations

from statistics import fmean, pstdev
from typing import Callable, Sequence

MINIMO_PARA_OUTLIER = 24
Z_MINIMO = 3
DetectorDeOutliers = Callable[[list[list[float]]], Sequence[int]]

_RULES = (
    ("spo2", "spo2_low", lambda row: row["spo2"] < 92),
    ("hr", "hr_high", lambda row: row["hr"] > 120),
    ("hr", "hr_low", lambda row: row["hr"] < 45),
    ("sbp", "sbp_high", lambda row: row["sbp"] > 180),
    ("sbp", "sbp_low", lambda row: row["sbp"] < 90),
    ("dbp", "dbp_high", lambda row: row["dbp"] > 110),
    ("dbp", "dbp_low", lambda row: row["dbp"] < 50),
)
_COLUNAS = ("hr", "sbp", "dbp", "spo2")


def matriz_vital(rows: list[dict]) -> list[list[float]]:
    return [[float(row[c]) for c in _COLUNAS] for row in rows]


def _zscore_maximo(matriz: list[list[float]]) -> list[float]:
    colunas = list(zip(*matriz))
    medias = [fmean(c) for c in colunas]
    escalas = [max(pstdev(c), 1e-6) for c in colunas]
    return [max(abs((v - m) / s) for v, m, s in zip(linha, medias, escalas)) for linha in matriz]


def vital_anomalies(rows: list[dict], outliers: DetectorDeOutliers | None = None) -> list[dict]:
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
    if outliers is None or len(rows) < MINIMO_PARA_OUTLIER:
        return found
    matriz = matriz_vital(rows)
    zscore = _zscore_maximo(matriz)
    for index in outliers(matriz):
        if index in covered or zscore[index] < Z_MINIMO:
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


# faixas do monitor (mínimo, máximo); as mesmas das regras acima
FAIXAS = {"spo2": (92, None), "hr": (45, 120), "sbp": (90, 180), "dbp": (50, 110)}
NOMES = {"spo2": "SpO2", "hr": "FC", "sbp": "PAS", "dbp": "PAD"}


def avaliar_medicao(row: dict, achados_da_serie: list[dict]) -> dict:
    """Leitura ao vivo de uma medição: fora da faixa (regra), fora do padrão (Isolation Forest) ou normal."""
    motivos = []
    for sinal, (minimo, maximo) in FAIXAS.items():
        valor = row.get(sinal)
        if valor is None:
            continue
        if minimo is not None and valor < minimo:
            motivos.append(f"{NOMES[sinal]} {valor:g} abaixo de {minimo}")
        elif maximo is not None and valor > maximo:
            motivos.append(f"{NOMES[sinal]} {valor:g} acima de {maximo}")
    if motivos:
        return {"estado": "fora_da_faixa", "motivos": motivos}
    atipica = any(a.get("rule") == "isolation_forest" and a.get("recorded_at") == row.get("recorded_at")
                  for a in achados_da_serie)
    if atipica:
        return {"estado": "fora_do_padrao", "motivos": ["Combinação atípica para este paciente"]}
    return {"estado": "normal", "motivos": []}
