"""Marca de atenção da dor: o recorte nasce na suspeita, o validador opina depois e o médico classifica."""
from __future__ import annotations

import pytest

from domain.atendimento.duvida import DuvidaDeDor, perto_do_limiar, quadros_do_validador


def _marca(**kw):
    dados = dict(duvida_id="d1", sessao_id="s1", criado_em="t0", duracao_s=3.0, quadros=12,
                 wong_baker_estimado=2, dor_relativa=1.5)
    return DuvidaDeDor.registrar(**{**dados, **kw})


def _confirmacao(relativa, confirmado, face=6):
    return {"id": "c1", "dor_relativa": relativa, "confirmado": confirmado, "wong_baker": face}


def test_marca_nasce_avaliando_e_pendente_para_o_medico():
    marca = _marca()
    assert marca.avaliando and marca.pendente and marca.veredito_texto == "Avaliando…"
    assert marca.confirmacao_id is None


def test_marca_sem_leitura_do_estagio1_ainda_vale():
    marca = _marca(wong_baker_estimado=None, dor_relativa=None)
    assert marca.wong_baker_estimado is None and marca.avaliando


def test_recorte_deve_ter_entre_2_e_4_segundos_e_quadros():
    assert _marca(quadros=40).quadros == 40  # 4 s a 10 quadros por segundo
    for invalido in ({"duracao_s": 1.9}, {"duracao_s": 4.1}, {"quadros": 1}, {"quadros": 41}):
        with pytest.raises(ValueError):
            _marca(**invalido)


@pytest.mark.parametrize(("total", "indices"), [
    (40, [19, 20, 21]),   # o centro do recorte é o momento da suspeita
    (17, [7, 8, 9]),
    (3, [0, 1, 2]),
    (2, [0, 1]),
])
def test_validador_avalia_os_quadros_do_momento_da_suspeita(total, indices):
    assert quadros_do_validador(total) == indices


@pytest.mark.parametrize(("relativa", "perto"), [(0.5, False), (2.5, True), (3.5, True), (4.5, True), (4.6, False)])
def test_perto_do_limiar_e_a_um_ponto_da_dor_moderada(relativa, perto):
    assert perto_do_limiar(relativa) is perto


def test_veredito_do_validador_confirma_ou_descarta():
    confirmada = _marca().com_veredito(_confirmacao(8.0, True, face=8), "t1")
    assert (confirmada.veredito, confirmada.veredito_face, confirmada.confirmacao_id) == ("confirmada", 8, "c1")
    assert confirmada.veredito_texto == "Validador confirmou dor · face 8" and not confirmada.avaliando
    descartada = _marca().com_veredito(_confirmacao(0.5, False, face=0), "t1")
    assert descartada.veredito_texto == "Validador descartou (+0.5)"
    limite = _marca().com_veredito(_confirmacao(3.0, False, face=4), "t1")
    assert limite.veredito_texto.endswith("· perto do limiar")


def test_validador_sem_resultado_e_veredito_unico():
    sem = _marca().sem_resultado("t1")
    assert sem.veredito == "sem_resultado" and sem.veredito_texto == "Validador sem resultado"
    with pytest.raises(ValueError):
        sem.com_veredito(_confirmacao(8.0, True), "t2")


def test_medico_classifica_mesmo_antes_do_validador():
    classificada = _marca().classificar(6, "dor", "  careta ao mexer o braço ", "t1")
    assert not classificada.pendente and classificada.avaliando
    assert (classificada.face_classificada, classificada.categoria, classificada.observacao) == (6, "dor", "careta ao mexer o braço")
    reclassificada = classificada.classificar(0, "outra_expressao", "", "t2")  # pode revisar a própria decisão
    assert reclassificada.categoria == "outra_expressao" and reclassificada.observacao is None
    com_veredito = reclassificada.com_veredito(_confirmacao(8.0, True), "t3")
    assert com_veredito.categoria == "outra_expressao"  # o veredito não apaga a decisão do médico


def test_classificacao_invalida_e_recusada():
    marca = _marca()
    for face, categoria, nota in ((5, "dor", ""), (4, "talvez", ""), (4, "dor", "x" * 501)):
        with pytest.raises(ValueError):
            marca.classificar(face, categoria, nota, "t1")
