"""Agregado Alerta de anomalia: nasce aberto, aponta uma série do corpus e ao menos um sinal. Sem paciente."""
from __future__ import annotations

from dataclasses import dataclass

from domain.anomalia.modelo import SINAIS


@dataclass(frozen=True)
class AlertaDeAnomalia:
    id: str
    serie_id: str
    modelo_id: str
    sinais: tuple[str, ...]
    criado_em: str
    estado: str = "aberto"

    @classmethod
    def abrir(cls, alerta_id: str, serie_id: str, modelo_id: str, sinais: list[str], criado_em: str) -> "AlertaDeAnomalia":
        if not sinais or any(s not in SINAIS for s in sinais):
            raise ValueError("alerta de anomalia aponta batimentos, pressao_arterial ou oxigenacao")
        return cls(alerta_id, serie_id, modelo_id, tuple(sinais), criado_em)


def leitura_de_anomalia(serie_id: str, modelo_id: str, alerta: AlertaDeAnomalia | None) -> dict:
    """Contrato à parte da métrica da sessão: sem paciente, diagnóstico ou sepse."""
    return {
        "serie_id": serie_id,
        "modelo_id": modelo_id,
        "resultado": "anomala" if alerta else "compativel",
        "sinais": list(alerta.sinais) if alerta else [],
        "alerta_id": alerta.id if alerta else None,
        "diagnostico": None,
        "sepse": None,
    }
