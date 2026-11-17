"""Regras da câmera e da cascata de dor facial (ADR-002), sem banco nem modelo de IA.

Estágio 1: face Wong-Baker acima de 5 em SUSPEITA leituras seguidas vira marca de atenção
gravada para o médico e pede o veredito do estágio 2 (ADR-004).
Estágio 2 (preciso): PSPI das AUs, mediana dos recortes menos o rosto neutro; confirma dor moderada.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from statistics import median

from domain.atendimento.dor_facial import BASE_MAXIMA, DESCRICAO_WONG_BAKER, DOR_MODERADA, pspi_de_aus, wong_baker

ESTAVEL = 2                   # leituras seguidas com a mesma expressão para virar evento
DOR_SUSTENTADA = 3            # leituras seguidas com dor moderada para abrir alerta (só estágio 1)
SUSPEITA = 3                  # leituras seguidas acima do nível: marca de atenção + estágio 2
NIVEL_DA_MARCA = 5            # só faces Wong-Baker acima de 5 (6, 8, 10) viram marca de atenção
JANELA_FALA_S = 8             # expressão vale para a fala dita até 8 s depois
JANELA_ESTIMATIVA_S = 60      # confirmação do estágio 2 vale como estimativa por até 1 min
RECENTES = max(ESTAVEL, DOR_SUSTENTADA, SUSPEITA)


class SemRostoNosRecortes(Exception):
    """O estágio 2 não encontrou rosto em nenhum recorte suspeito."""


def rotulo(leitura: dict) -> str:
    if leitura["nivel_dor"] != "ausente" and leitura["expressao"] != "dor/desconforto":
        return f"{leitura['expressao']} · dor {leitura['nivel_dor']}"
    if leitura["expressao"] == "dor/desconforto":
        return f"dor/desconforto ({leitura['nivel_dor']})"
    return leitura["expressao"]


def _decorrido(desde: str, ate: str) -> timedelta:
    return datetime.fromisoformat(ate) - datetime.fromisoformat(desde)


def evento_de_expressao(recentes: list[dict], anterior: str, atual: str) -> str | None:
    """Descrição do evento quando a expressão ficou estável e mudou; None se nada mudou."""
    estavel = len(recentes) >= ESTAVEL and len({r["expressao"] for r in recentes[:ESTAVEL]}) == 1
    if not estavel or atual == anterior:
        return None
    return f"Rosto do paciente: {atual}" if atual != "neutra" else "Rosto do paciente voltou ao neutro"


def dor_sustentada(recentes: list[dict]) -> bool:
    return len(recentes) >= DOR_SUSTENTADA and all(r["nivel_dor"] == "moderada" for r in recentes[:DOR_SUSTENTADA])


def suspeita(recentes: list[dict]) -> bool:
    """Face Wong-Baker acima do nível 5 em SUSPEITA leituras seguidas; vale com ou sem validador e com alerta aberto."""
    return len(recentes) >= SUSPEITA and all(r["wong_baker"] > NIVEL_DA_MARCA for r in recentes[:SUSPEITA])


def expressao_vale_para_fala(registrada_em: str, agora: str) -> bool:
    return _decorrido(registrada_em, agora) <= timedelta(seconds=JANELA_FALA_S)


def confirmacao_vale_como_estimativa(registrada_em: str, agora: str) -> bool:
    return _decorrido(registrada_em, agora) <= timedelta(seconds=JANELA_ESTIMATIVA_S)


def avaliar_confirmacao(detector: str, aus_suspeitos: list[dict | None], aus_neutro: dict | None) -> dict:
    pspis = [pspi_de_aus(aus) for aus in aus_suspeitos if aus]
    if not pspis:
        raise SemRostoNosRecortes("estágio 2 não encontrou rosto nos recortes")
    base = round(min(BASE_MAXIMA, pspi_de_aus(aus_neutro)), 2) if aus_neutro else 0.0
    valor = round(median(pspis), 2)
    relativa = round(max(0.0, valor - base), 2)
    return {
        "detector": detector,
        "pspi": valor,
        "pspi_base": base,
        "dor_relativa": relativa,
        "wong_baker": wong_baker(relativa),
        # estágio 1 suspeita a partir de dor leve (sensível); estágio 2 só confirma dor moderada (preciso)
        "confirmado": relativa >= DOR_MODERADA,
        "faces_avaliadas": len(pspis),
    }


def face_wong_baker(valor) -> int:
    if isinstance(valor, bool) or not isinstance(valor, int) or valor not in DESCRICAO_WONG_BAKER:
        raise ValueError("face Wong-Baker deve ser 0, 2, 4, 6, 8 ou 10")
    return valor


def descricao_alerta_confirmado(confirmacao: dict) -> str:
    face = confirmacao["wong_baker"]
    return (f"dor no rosto confirmada pelo estágio 2: Wong-Baker {face} ({DESCRICAO_WONG_BAKER[face]}), "
            f"PSPI +{confirmacao['dor_relativa']:.1f} sobre o rosto neutro")
