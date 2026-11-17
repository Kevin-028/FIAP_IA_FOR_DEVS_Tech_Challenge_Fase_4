"""Pontos de interesse clínico citados na fala: remédio, doença, exame, dose, hábito..."""
from __future__ import annotations

import pytest

from domain.atendimento.conversa.entidades import extrair_entidades, resumo


def _pares(texto: str) -> list[tuple[str, str]]:
    return [(e["tipo"], e["texto"]) for e in extrair_entidades(texto)]


def _negadas(texto: str) -> set[str]:
    return {e["texto"] for e in extrair_entidades(texto) if e["negada"]}


def test_relato_completo_do_paciente():
    texto = ("Doutor, eu tenho hipertensão e diabetes, tomo losartana 50 mg duas vezes ao dia e metformina. "
             "Estou com dor no peito há dois dias e sou alérgico a dipirona.")
    assert _pares(texto) == [
        ("Doença / condição", "hipertensão"),
        ("Doença / condição", "diabetes"),
        ("Medicamento", "losartana"),
        ("Dose / posologia", "50 mg"),
        ("Dose / posologia", "duas vezes ao dia"),
        ("Medicamento", "metformina"),
        ("Sintoma", "dor no peito"),
        ("Tempo / evolução", "há dois dias"),
        ("Alergia", "dipirona"),
    ]


@pytest.mark.parametrize("texto, tipo, trecho", [
    ("Vou pedir um hemograma", "Exame", "hemograma"),
    ("fiz uma tomografia mês passado", "Exame", "tomografia"),
    ("tomo rivotril antes de dormir", "Medicamento", "rivotril"),
    ("tomo rivotril antes de dormir", "Dose / posologia", "antes de dormir"),
    ("uso enalapril", "Medicamento", "enalapril"),          # dicionário
    ("comecei a tomar bisoprolol", "Medicamento", "bisoprolol"),
    ("me deram um tal de zofenopril", "Medicamento", "zofenopril"),  # sufixo -pril
    ("de 8 em 8 horas", "Dose / posologia", "de 8 em 8 horas"),
    ("a pressão estava 16 por 10", "Medida relatada", "pressão estava 16 por 10"),
    ("Estava 12 por 8 ontem", "Medida relatada", "12 por 8"),  # "pressão" ficou na pergunta do médico
    ("febre de 38,5 graus", "Medida relatada", "febre de 38,5 graus"),
    ("a dor está 8 de 10", "Medida relatada", "8 de 10"),
    ("minha mãe teve infarto aos 60", "Histórico familiar", "minha mãe teve infarto aos 60"),
    ("fiz uma cirurgia de vesícula", "Cirurgia / procedimento", "fiz uma cirurgia de vesícula"),
    ("bebo cerveja no fim de semana", "Hábito", "bebo"),
    ("inchaço nas pernas", "Sintoma", "inchaço nas pernas"),
    ("dor no joelho", "Sintoma", "dor no joelho"),
    ("tenho pressão alta", "Doença / condição", "pressão alta"),
])
def test_tipos(texto, tipo, trecho):
    assert (tipo, trecho) in _pares(texto)


def test_negacao_vira_informacao_negada():
    assert _negadas("Não tenho asma, não fumo, mas bebo cerveja.") == {"asma", "fumo"}
    assert _negadas("Não, mas tenho diabetes.") == set()  # a vírgula encerra a negação
    assert _negadas("Nunca tive alergia a penicilina") == {"penicilina"}


def test_indices_batem_com_o_texto_original():
    texto = "Tomo AMOXICILINA 500mg há três dias."
    for ent in extrair_entidades(texto):
        assert texto[ent["inicio"]:ent["fim"]] == ent["texto"]


def test_texto_sem_nada_clinico():
    assert extrair_entidades("Bom dia, tudo bem com a senhora?") == []
    assert extrair_entidades("tomo 2 por dia") == []


def test_resumo_esconde_o_generico_coberto_pelo_especifico():
    grupos = resumo(extrair_entidades("Dor no peito, muita dor."))
    assert [i["texto"] for i in grupos[0]["itens"]] == ["Dor no peito"]


def test_resumo_agrupa_sem_repetir_e_marca_o_medico():
    citadas = []
    for ordem, texto, medico in [(1, "Tomo losartana.", False), (2, "Vou manter a losartana e pedir hemograma.", True),
                                 (3, "Não tenho diabetes.", False)]:
        citadas += [{**e, "ordem": ordem, "medico": medico} for e in extrair_entidades(texto)]
    grupos = {g["tipo"]: g["itens"] for g in resumo(citadas)}
    assert grupos["Medicamento"] == [{"texto": "losartana", "negada": False, "vezes": 2, "falas": [1, 2], "medico": False}]
    assert grupos["Exame"][0]["medico"] is True
    assert grupos["Doença / condição"][0]["negada"] is True
    assert list(grupos) == ["Medicamento", "Doença / condição", "Exame"]  # ordem fixa de exibição
