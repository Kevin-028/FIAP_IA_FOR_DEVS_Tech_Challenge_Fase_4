"""Agregado Modelo de anomalia: só é utilizável se foi treinado no corpus vital (RN-11).

Faixa fixa não é modelo. A saída fala de batimentos, pressão arterial e oxigenação; nunca de sepse (RN-12).
"""
from __future__ import annotations

from dataclasses import dataclass

SINAIS = ("batimentos", "pressao_arterial", "oxigenacao")
MINIMO_CORPUS = 24
Z_SINAL = 2
# ordem das características do artefato: hr, sbp, dbp, spo2
SINAL_POR_CARACTERISTICA = ("batimentos", "pressao_arterial", "pressao_arterial", "oxigenacao")


class ModeloAusente(LookupError):
    pass


class DetectorDeFaixaFixaRecusado(Exception):
    """RN-11: só regras fixas não cumprem a detecção."""


def recusar_faixa_fixa() -> None:
    raise DetectorDeFaixaFixaRecusado("faixa fixa nao foi treinada no corpus")


@dataclass(frozen=True)
class ModeloDeAnomalia:
    id: str
    treinado_no_corpus: bool
    artefato: object
    criado_em: str = ""

    @classmethod
    def treinado(cls, modelo_id: str, artefato: object, linhas_de_treino: int, criado_em: str) -> "ModeloDeAnomalia":
        if linhas_de_treino < MINIMO_CORPUS:
            raise ModeloAusente("corpus insuficiente")
        return cls(modelo_id, True, artefato, criado_em)

    def exigir_utilizavel(self) -> None:
        if not self.treinado_no_corpus:
            raise ModeloAusente(self.id)


def nomear_sinais(pico_por_caracteristica: list[float]) -> list[str]:
    """Z médio dos pontos anômalos por característica → sinais apontados (≥ 2 desvios), o mais forte primeiro."""
    ordem = sorted(range(len(pico_por_caracteristica)), key=lambda i: pico_por_caracteristica[i], reverse=True)
    escolhidos: list[str] = []
    for indice in ordem:
        nome = SINAL_POR_CARACTERISTICA[indice]
        if nome not in escolhidos and pico_por_caracteristica[indice] >= Z_SINAL:
            escolhidos.append(nome)
    return escolhidos or [SINAL_POR_CARACTERISTICA[ordem[0]]]
