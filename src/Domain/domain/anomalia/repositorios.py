"""Contratos de persistência do contexto Anomalia de padrão (implementados na Infrastructure)."""
from __future__ import annotations

from typing import Protocol

from domain.anomalia.alerta import AlertaDeAnomalia
from domain.anomalia.modelo import ModeloDeAnomalia


class RepositorioModelo(Protocol):
    def adicionar(self, modelo: ModeloDeAnomalia) -> None: ...

    def obter(self, modelo_id: str) -> ModeloDeAnomalia | None: ...

    def listar(self) -> list[dict]: ...


class RepositorioAlertaAnomalia(Protocol):
    def adicionar(self, alerta: AlertaDeAnomalia) -> None: ...

    def listar(self) -> list[dict]:
        """Mais recente primeiro, com os sinais apontados."""
