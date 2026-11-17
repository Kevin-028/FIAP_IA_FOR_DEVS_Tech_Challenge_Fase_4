"""Agregado Alerta de dor (ADR-001): nasce aberto; ciência não encerra; encerrado não reabre (RN-16, RN-17)."""
from __future__ import annotations

from dataclasses import dataclass, replace

from domain.atendimento.sessao import SessaoRecusada

ORIGENS = ("face", "movimentacao", "relato")
ABERTO, CIENTE, ENCERRADO = "aberto", "ciente", "encerrado"


class AlertaDeDorRecusado(SessaoRecusada):
    """Alerta inexistente ou já encerrado (recusa do ciclo da consulta)."""


@dataclass(frozen=True)
class AlertaDeDor:
    id: str
    sessao_id: str
    origem: str
    descricao_sinal: str
    estado: str
    criado_em: str
    ciente_em: str | None = None
    encerrado_em: str | None = None

    @classmethod
    def abrir(cls, alerta_id: str, sessao_id: str, origem: str, descricao: str, quando: str) -> "AlertaDeDor":
        if origem not in ORIGENS:
            raise ValueError(f"origem do alerta de dor deve ser uma de {ORIGENS}")
        return cls(alerta_id, sessao_id, origem, descricao, ABERTO, quando)

    @property
    def ativo(self) -> bool:
        return self.estado != ENCERRADO

    def dar_ciencia(self, quando: str) -> "AlertaDeDor":
        if not self.ativo:
            raise AlertaDeDorRecusado(self.id)
        if self.estado == CIENTE:
            return self
        return replace(self, estado=CIENTE, ciente_em=quando)

    def encerrar(self, quando: str) -> "AlertaDeDor":
        if not self.ativo:
            raise AlertaDeDorRecusado(self.id)
        return replace(self, estado=ENCERRADO, ciente_em=self.ciente_em or quando, encerrado_em=quando)
