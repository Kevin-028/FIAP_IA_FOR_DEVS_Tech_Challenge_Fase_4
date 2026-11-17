"""Formatação para as telas: horários locais e seção ativa do menu."""
from __future__ import annotations

from datetime import datetime

SECOES = (("/pacientes", "pacientes"), ("/consulta", "pacientes"), ("/sessoes", "pacientes"),
          ("/alertas", "alertas"), ("/revisao", "revisao"), ("/internacao", "internacao"), ("/sistema", "sistema"), ("/anomalia", "sistema"))


def _instante(valor) -> datetime | None:
    try:
        instante = datetime.fromisoformat(str(valor))
    except (TypeError, ValueError):
        return None
    return instante.astimezone() if instante.tzinfo else instante


def hora(valor) -> str:
    instante = _instante(valor)
    return instante.strftime("%H:%M") if instante else (valor or "—")


def data_hora(valor) -> str:
    instante = _instante(valor)
    return instante.strftime("%d/%m/%Y %H:%M") if instante else (valor or "—")


def secao_do_caminho(caminho: str) -> str:
    if caminho in ("", "/"):
        return "hoje"
    return next((secao for prefixo, secao in SECOES if caminho.startswith(prefixo)), "")
