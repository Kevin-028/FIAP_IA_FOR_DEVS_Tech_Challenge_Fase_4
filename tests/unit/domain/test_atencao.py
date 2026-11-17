"""Pontos de atenção marcados numa fala da consulta."""
from __future__ import annotations

import pytest

from domain.atendimento.conversa.atencao import pontos_por_azure, pontos_por_regra


def _categorias(texto: str) -> set[str]:
    return {p["categoria"] for p in pontos_por_regra(texto)}


def test_alarmes_com_trecho_original_e_especifico_cobre_generico():
    pontos = pontos_por_regra("Doutor, faz três dias que sinto dor no peito e falta de ar.")
    cats = {p["categoria"]: p for p in pontos}
    assert {"Dor torácica", "Dificuldade respiratória", "Tempo de evolução"} <= set(cats)
    assert "Dor" not in cats
    assert cats["Dor torácica"]["trecho"] == "dor no peito"
    assert cats["Tempo de evolução"]["trecho"] == "faz três dias"
    assert cats["Dor torácica"]["severidade"] == "alta"


def test_pontos_em_ordem_do_texto_e_um_por_categoria():
    pontos = pontos_por_regra("Tenho febre, muita febre e tosse.")
    assert [p["categoria"] for p in pontos] == ["Febre", "Tosse"]
    assert pontos[0]["inicio"] < pontos[1]["inicio"]


@pytest.mark.parametrize(
    ("texto", "categoria"),
    [
        ("Penso em me matar às vezes", "Risco à vida"),
        ("Sinto um aperto no peito", "Dor torácica"),
        ("Fico sem fôlego", "Dificuldade respiratória"),
        ("Acordei com a boca torta", "Sinal neurológico"),
        ("Ontem desmaiei no ônibus", "Perda de consciência"),
        ("Tive uma convulsão", "Convulsão"),
        ("Saiu sangue na urina", "Sangramento"),
        ("Ele está meio confuso", "Alteração cognitiva"),
        ("Esqueci de tomar o remédio", "Falha de adesão"),
        ("Sou alérgica a penicilina", "Alergia"),
        ("A dor está 9 de 10", "Intensidade da dor"),
        ("Está doendo aqui", "Dor"),
        ("Tive calafrios", "Febre"),
        ("Ando muito cansada", "Fadiga"),
        ("Sinto tontura ao levantar", "Tontura"),
        ("Estou enjoada", "Náusea ou vômito"),
        ("Estou tossindo muito", "Tosse"),
        ("Tomo insulina", "Medicação"),
        ("Começou desde ontem", "Tempo de evolução"),
    ],
)
def test_cada_categoria(texto, categoria):
    assert categoria in _categorias(texto)


@pytest.mark.parametrize(
    ("texto", "ausente"),
    [
        ("Não tive febre nenhuma.", "Febre"),
        ("Estou sem dor hoje.", "Dor"),
        ("Nunca desmaiei.", "Perda de consciência"),
        ("Não tenho alergia.", "Alergia"),
    ],
)
def test_negacao_nao_marca(texto, ausente):
    assert ausente not in _categorias(texto)


def test_negacao_que_faz_parte_do_sintoma_ainda_marca():
    assert "Dificuldade respiratória" in _categorias("Às vezes não consigo respirar direito.")
    assert "Falha de adesão" in _categorias("Não tomei o remédio ontem.")


def test_escala_baixa_nao_e_intensidade_alta():
    assert "Intensidade da dor" not in _categorias("A dor está 3 de 10")


def test_texto_neutro_sem_pontos():
    assert pontos_por_regra("Bom dia, tudo bem com a família.") == []


def test_texto_com_acentos_e_maiusculas():
    pontos = pontos_por_regra("FALTA DE AR E PRESSÃO NO PEITO")
    assert pontos[0]["trecho"] == "FALTA DE AR"


def test_azure_negativo_vira_ponto_e_positivo_nao():
    assert pontos_por_azure("x", "positive", []) == []
    assert pontos_por_azure("x", "neutral", []) == []
    ponto = pontos_por_azure("estou muito mal", "negative", ["mal", "a", "b", "c"])[0]
    assert ponto["origem"] == "azure" and ponto["trecho"] == "mal, a, b"
    assert pontos_por_azure("frase longa", "negative", [])[0]["trecho"] == "frase longa"
