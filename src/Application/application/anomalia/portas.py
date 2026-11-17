"""Portas do contexto Anomalia de padrão."""
from __future__ import annotations

from typing import Protocol


class MotorDeAnomalia(Protocol):
    """Modelo estatístico treinado no corpus (Isolation Forest na Infrastructure)."""

    def treinar(self, linhas: list[dict]) -> object:
        """Devolve o artefato treinado nas linhas hr, sbp, dbp, spo2."""

    def picos_anomalos(self, artefato: object, linhas: list[dict]) -> list[float] | None:
        """Z médio dos pontos anômalos por característica (hr, sbp, dbp, spo2); None se a série é compatível."""


class CorpusVital(Protocol):
    """ACL do corpus PhysioNet: entrega só hr, sbp, dbp e spo2. O SepsisLabel não atravessa."""

    def linhas_de_treino(self) -> list[dict]: ...

    def serie(self, serie_id: str) -> list[dict] | None:
        """Linhas de uma série do corpus (ex.: p000057); None se não existe."""
