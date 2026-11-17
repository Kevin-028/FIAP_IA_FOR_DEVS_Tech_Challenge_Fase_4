"""Identificação automática de médico e paciente pelo jeito de falar."""
from __future__ import annotations

import pytest

from domain.atendimento.conversa.interlocutores import Evidencia, classificar_locutores, pontuar_fala


@pytest.mark.parametrize(
    "fala",
    [
        "Bom dia, o que trouxe a senhora aqui hoje?",
        "Há quanto tempo a senhora sente isso?",
        "Vou pedir um eletrocardiograma e um hemograma.",
        "Me conta como começou essa dor.",
        "Respire fundo, por favor.",
        "Toma algum remédio?",
    ],
)
def test_falas_tipicas_do_medico_pontuam_positivo(fala):
    assert pontuar_fala(fala) > 0


@pytest.mark.parametrize(
    "fala",
    [
        "Doutor, estou com dor no peito faz três dias.",
        "Sinto uma pontada aqui do lado.",
        "Minha pressão subiu ontem.",
        "Tive febre a noite toda.",
        "Ah, eu acho que comecei a sentir na segunda.",
    ],
)
def test_falas_tipicas_do_paciente_pontuam_negativo(fala):
    assert pontuar_fala(fala) < 0


def test_pergunta_do_medico_sobre_sintoma_nao_vira_paciente():
    assert pontuar_fala("A senhora tem dor no peito ou falta de ar?") > 0


def _ev(locutor, falas, primeira):
    return Evidencia(locutor, sum(pontuar_fala(f) for f in falas), len(falas), primeira)


def test_conversa_com_duas_vozes():
    medico = _ev("Guest-1", ["Bom dia, o que trouxe o senhor?", "Vou pedir exames."], 1)
    paciente = _ev("Guest-2", ["Doutor, estou com tosse.", "Tenho febre desde ontem."], 2)
    papeis = classificar_locutores([medico, paciente])
    assert papeis["Guest-1"][0] == "medico" and papeis["Guest-2"][0] == "paciente"
    assert 0.5 <= papeis["Guest-1"][1] <= 0.99


def test_ordem_das_vozes_nao_importa_quando_a_fala_e_clara():
    paciente = _ev("Guest-1", ["Doutor, sinto muita dor de cabeça.", "Minha visão está turva."], 1)
    medico = _ev("Guest-2", ["Há quanto tempo o senhor sente isso?", "Vou examinar."], 2)
    papeis = classificar_locutores([paciente, medico])
    assert papeis["Guest-2"][0] == "medico" and papeis["Guest-1"][0] == "paciente"


def test_terceira_voz_vira_acompanhante():
    papeis = classificar_locutores([
        _ev("Guest-1", ["O que trouxe vocês aqui?", "Vou pedir exames."], 1),
        _ev("Guest-2", ["Doutor, estou com dor nas costas."], 2),
        _ev("Guest-3", ["Ele não dorme bem."], 3),
    ])
    assert papeis["Guest-3"][0] == "acompanhante"


def test_sem_evidencia_suficiente_nao_decide():
    assert classificar_locutores([_ev("Guest-1", ["Ok."], 1), _ev("Guest-2", ["Certo."], 2)]) == {}
    assert classificar_locutores([_ev("Guest-1", ["Ok."], 1)]) == {}
    assert classificar_locutores([]) == {}


def test_uma_voz_so_com_evidencia_forte():
    assert classificar_locutores([_ev("Guest-1", ["Doutor, estou com dor no peito."], 1)])["Guest-1"][0] == "paciente"
    assert classificar_locutores([_ev("Guest-1", ["Bom dia, o que trouxe a senhora? Vou examinar."], 1)])["Guest-1"][0] == "medico"


def test_medico_manual_faz_o_restante_ser_paciente():
    papeis = classificar_locutores([_ev("Guest-2", ["Ok."], 2)], manuais={"Guest-1": "medico"})
    assert papeis == {"Guest-2": ("paciente", papeis["Guest-2"][1])}
