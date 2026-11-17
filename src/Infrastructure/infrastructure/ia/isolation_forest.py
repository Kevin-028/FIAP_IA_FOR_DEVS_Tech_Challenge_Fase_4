"""Isolation Forest treinado no corpus vital (porta MotorDeAnomalia)."""
from __future__ import annotations

import numpy as np
from sklearn.ensemble import IsolationForest

CARACTERISTICAS = ("hr", "sbp", "dbp", "spo2")


def _matriz(linhas: list[dict]) -> np.ndarray:
    return np.array([[linha[c] for c in CARACTERISTICAS] for linha in linhas], dtype=float)


class MotorIsolationForest:
    def treinar(self, linhas: list[dict]) -> dict:
        matriz = _matriz(linhas)
        modelo = IsolationForest(n_estimators=80, contamination=0.05, random_state=0)
        modelo.fit(matriz)
        return {
            "modelo": modelo,
            "media": matriz.mean(axis=0),
            "desvio": np.maximum(matriz.std(axis=0), 1e-6),
            "features": CARACTERISTICAS,
        }

    def picos_anomalos(self, artefato: dict, linhas: list[dict]) -> list[float] | None:
        matriz = _matriz(linhas)
        outliers = artefato["modelo"].predict(matriz) == -1
        if not outliers.any():
            return None
        z = np.abs((matriz - artefato["media"]) / artefato["desvio"])
        return [float(v) for v in z[outliers].mean(axis=0)]
