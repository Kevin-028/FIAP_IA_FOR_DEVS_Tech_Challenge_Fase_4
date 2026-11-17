"""Quem é o médico e quem é o paciente, pelo jeito de falar.

O Azure Speech separa as vozes (Guest-1, Guest-2), mas não diz o papel de cada uma.
Cada fala recebe uma pontuação: positiva soa como médico (pergunta, conduz, pede exame),
negativa soa como paciente (relata sintoma em primeira pessoa, chama "doutor").
A média por locutor decide o papel. É heurística: o médico pode corrigir à mão.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from domain.atendimento.conversa.atencao import _sem_acento, pontos_por_regra

_MEDICO: tuple[tuple[float, re.Pattern], ...] = tuple(
    (peso, re.compile(padrao))
    for peso, padrao in (
        (1.0, r"\?\s*$"),
        (1.0, r"^(?:e |entao |certo,? |ok,? |bom,? |muito bem,? )?(?:o que|como|quando|onde|qual|quais|quanto|quantos|quantas"
              r"|ha quanto tempo|desde quando|voce|o senhor|a senhora|tem |sente |teve |esta |toma |costuma )"),
        (2.0, r"\b(?:vou|vamos|irei) (?:pedir|solicitar|prescrever|receitar|examinar|encaminhar|auscultar|medir|verificar"
              r"|avaliar|aumentar|reduzir|suspender|trocar|ajustar|repetir|internar)"),
        (2.0, r"\b(?:me conta|me conte|me fala|me diga|me descreva|pode me dizer|consegue me dizer|me mostra)"),
        (2.0, r"o que (?:te |lhe |o |a )?(?:traz|trouxe)"),
        (2.0, r"\b(?:respire fundo|pode se deitar|deite|abra a boca|levante o braco|tussa)"),
        (1.0, r"\b(?:exames?|hemograma|eletrocardiograma|raio[- ]x|tomografia|ressonancia|receita|prescricao|diagnostico"
              r"|retorno|encaminhamento|orientacao|recomendo|posologia)\b"),
        (0.5, r"\b(?:o senhor|a senhora|voce)\b"),
        (1.5, r"\b(?:bom dia|boa tarde|boa noite)\b.*\b(?:sente|traz|trouxe|ajudar|tudo bem)"),
    )
)

_PACIENTE: tuple[tuple[float, re.Pattern], ...] = tuple(
    (peso, re.compile(padrao))
    for peso, padrao in (
        (2.0, r"\b(?:doutor|doutora|dr|dra)\b"),
        (1.0, r"\b(?:estou|to|tou|ando|fiquei|sinto|senti|sentindo|tenho|tive|comecei|acordei|doi|doendo)\b"),
        (1.0, r"\b(?:minha|meu|minhas|meus) (?:dor|dores|peito|cabeca|barriga|braco|perna|pressao|coracao|estomago"
              r"|costas|garganta|filh\w*|remedios?|exames?)"),
        (0.5, r"\b(?:eu nao sei|nao sei se|acho que)\b"),
        (0.5, r"^(?:sim|nao|ah|olha|entao|e que)\b"),
    )
)

PRIOR_ABERTURA = 0.75  # quem abre a consulta costuma ser o médico
MARGEM = 1.0           # diferença mínima entre médias (maior que o prior: só abrir a consulta não decide)
SOZINHO = 1.5          # um só locutor: precisa de evidência forte


def pontuar_fala(texto: str) -> float:
    normal = _sem_acento(texto).strip()
    medico = sum(peso for peso, padrao in _MEDICO if padrao.search(normal))
    paciente = sum(peso for peso, padrao in _PACIENTE if padrao.search(normal))
    sintomas = [p for p in pontos_por_regra(texto) if p["categoria"] != "Tempo de evolução"]
    if sintomas and not normal.endswith("?"):
        paciente += min(1.0, 0.5 * len(sintomas))
    return medico - paciente


@dataclass
class Evidencia:
    locutor: str
    soma: float
    falas: int
    primeira_ordem: int

    @property
    def media(self) -> float:
        return self.soma / self.falas if self.falas else 0.0


def _confianca(margem: float) -> float:
    return round(max(0.5, min(0.99, 0.5 + margem / 4)), 2)


def classificar_locutores(evidencias: list[Evidencia], manuais: dict[str, str] | None = None) -> dict[str, tuple[str, float]]:
    """Devolve {locutor: (papel, confiança)} só para quem dá para decidir."""
    manuais = manuais or {}
    if not evidencias:
        return {}
    abertura = min(e.primeira_ordem for e in evidencias)
    medias = {e.locutor: e.media + (PRIOR_ABERTURA if e.primeira_ordem == abertura else 0.0) for e in evidencias}
    ordem = sorted(medias, key=medias.get, reverse=True)
    papeis_manuais = set(manuais.values())

    if "medico" in papeis_manuais:
        # o médico já está fixado: o mais "paciente" dos demais é o paciente
        resultado = {}
        for indice, locutor in enumerate(reversed(ordem)):
            papel = "paciente" if indice == 0 and "paciente" not in papeis_manuais else "acompanhante"
            resultado[locutor] = (papel, _confianca(abs(medias[locutor]) + 1))
        return resultado

    if len(ordem) == 1:
        locutor = ordem[0]
        valor = medias[locutor]
        if valor >= SOZINHO:
            return {locutor: ("medico", _confianca(valor - SOZINHO + 1))}
        if valor <= -SOZINHO and "paciente" not in papeis_manuais:
            return {locutor: ("paciente", _confianca(-valor - SOZINHO + 1))}
        return {}

    margem = medias[ordem[0]] - medias[ordem[1]]
    if margem < MARGEM:
        return {}
    confianca = _confianca(margem)
    resultado = {ordem[0]: ("medico", confianca)}
    # entre os demais, quem mais relata sintomas é o paciente; o resto acompanha
    for indice, locutor in enumerate(reversed(ordem[1:])):
        papel = "paciente" if indice == 0 and "paciente" not in papeis_manuais else "acompanhante"
        resultado[locutor] = (papel, confianca)
    return resultado
