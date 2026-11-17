"""Regras da conversa ao vivo: papéis, termos críticos e resumo clínico."""
from __future__ import annotations

from domain.atendimento.conversa.entidades import resumo

PAPEIS = ("medico", "paciente", "acompanhante")
CATEGORIAS_DE_DOR = {"Dor", "Intensidade da dor", "Dor torácica"}
SEM_PAPEL_AUTOMATICO = ("", "Unknown")


def papel_valido(locutor: str, papel: str) -> str:
    if not (locutor or "").strip() or papel not in PAPEIS:
        raise ValueError("locutor e papel (medico, paciente, acompanhante) sao obrigatorios")
    return papel


def pontos_visiveis(pontos: list[dict], papeis: dict[str, str]) -> list[dict]:
    """Pergunta do médico não é queixa: pontos de quem não é médico, com o papel ao lado."""
    return [{**p, "papel": papeis.get(p["locutor"], "")} for p in pontos if papeis.get(p["locutor"]) != "medico"]


def termos_criticos(pontos: list[dict]) -> str:
    termos: list[str] = []
    for ponto in pontos:
        if ponto["categoria"] not in termos:
            termos.append(ponto["categoria"])
    return ", ".join(termos)


def relatos_de_dor(pontos: list[dict]) -> list[str]:
    """Só fala do paciente abre alerta de dor por relato."""
    return [p["trecho"] for p in pontos if p["categoria"] in CATEGORIAS_DE_DOR and p.get("papel") == "paciente"]


def resumo_clinico(falas: list[dict]) -> list[dict]:
    """Medicamentos, doenças, exames... de toda a conversa, agrupados.

    Pergunta do médico ("tem diabetes?") não entra: não é informação do paciente.
    O que o médico afirma (exame pedido, remédio trocado) entra marcado como dito pelo médico.
    """
    citadas = []
    for fala in falas:
        medico = fala["papel"] == "medico"
        if medico and fala["texto"].rstrip().endswith("?"):
            continue
        for ent in fala["entidades"]:
            citadas.append({**ent, "ordem": fala["ordem"], "medico": medico})
    return resumo(citadas)
