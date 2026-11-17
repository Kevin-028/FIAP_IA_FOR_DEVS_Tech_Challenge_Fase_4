"""Isolation Forest para outlier multivariado dos sinais vitais (porta DetectorDeOutliers do plantão)."""
from __future__ import annotations

import numpy as np
from sklearn.ensemble import IsolationForest

MINIMO_LINHAS = 24


def isolation_outlier_indexes(matrix) -> list[int]:
    array = np.asarray(matrix, dtype=float)
    if len(array) < MINIMO_LINHAS:
        return []
    if np.all(array.std(axis=0) < 1e-6):
        return []
    model = IsolationForest(n_estimators=50, contamination=0.05, random_state=0)
    flags = model.fit_predict(array)
    return [index for index, flag in enumerate(flags) if flag == -1]


class DetectorIsolationForest:
    """Porta DetectorDeOutliers do plantão."""

    def detectar(self, matriz: list[list[float]]) -> list[int]:
        return isolation_outlier_indexes(matriz)
