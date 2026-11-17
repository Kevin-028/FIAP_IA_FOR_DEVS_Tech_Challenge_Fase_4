"""Cascata de dor: PSPI → Wong-Baker e confirmação do estágio 2 com um avaliador falso."""
from __future__ import annotations

import pytest

from domain.atendimento.cascata import SemRostoNosRecortes, avaliar_confirmacao, suspeita
from domain.atendimento.dor_facial import DESCRICAO_WONG_BAKER, classificar_expressao, pspi_de_aus, wong_baker


def _faces(*faces):
    return [{"wong_baker": f, "nivel_dor": "moderada" if f >= 6 else "leve"} for f in faces]


@pytest.mark.parametrize(("faces", "marca"), [
    ((6, 6, 6), True),       # acima do nível 5 em 3 leituras seguidas
    ((10, 8, 6), True),
    ((4, 4, 4), False),      # dor leve não vira marca
    ((6, 6, 4), False),      # precisa das 3 seguidas
    ((6, 6), False),
])
def test_marca_de_atencao_so_acima_do_nivel_5(faces, marca):
    assert suspeita(_faces(*faces)) is marca

NEUTRO_AUS = {"AU04": 0.05, "AU06": 0.1, "AU07": 0.2, "AU09": 0.0, "AU10": 0.05, "AU43": 0.0}
DOR_AUS = {"AU04": 0.8, "AU06": 0.4, "AU07": 0.9, "AU09": 0.6, "AU10": 0.3, "AU43": 0.7}


class AvaliadorFalso:
    """Respostas na ordem em que o serviço envia: neutro (se houver) e depois os suspeitos."""

    def __init__(self, respostas):
        self.respostas = list(respostas)


def confirmar(avaliador, suspeitos, neutro=None):
    if not suspeitos:
        raise ValueError("nenhum recorte suspeito")
    respostas = avaliador.respostas
    aus_neutro = respostas.pop(0) if neutro else None
    return avaliar_confirmacao("falso", respostas[: len(suspeitos)], aus_neutro)


@pytest.mark.parametrize(
    ("relativa", "face"),
    [(0, 0), (0.99, 0), (1, 2), (1.99, 2), (2, 4), (3.99, 4), (4, 6), (5.99, 6), (6, 8), (8.99, 8), (9, 10), (16, 10)],
)
def test_faixas_wong_baker(relativa, face):
    assert wong_baker(relativa) == face


def test_wong_baker_negativo_e_sem_dor():
    assert wong_baker(-3) == 0


def test_toda_face_tem_descricao():
    assert set(DESCRICAO_WONG_BAKER) == {0, 2, 4, 6, 8, 10}


def test_classificacao_inclui_face_wong_baker():
    dor = {"browDownLeft": 0.6, "browDownRight": 0.6, "eyeSquintLeft": 0.7, "eyeSquintRight": 0.7}
    out = classificar_expressao(dor)
    assert out["wong_baker"] == wong_baker(out["dor_relativa"]) and out["wong_baker"] >= 4


def test_pspi_de_aus_segue_a_formula():
    assert pspi_de_aus({}) == 0.0
    assert pspi_de_aus({"AU04": 1.0}) == 5.0
    assert pspi_de_aus({"AU06": 0.4, "AU07": 0.6}) == 3.0  # max(AU6, AU7)
    assert pspi_de_aus({"AU09": 0.2, "AU10": 0.4}) == 2.0  # max(AU9, AU10)
    assert pspi_de_aus({"AU43": 0.7}) == 1.0 and pspi_de_aus({"AU43": 0.4}) == 0.0
    assert pspi_de_aus({k: 1.0 for k in ("AU04", "AU06", "AU07", "AU09", "AU10", "AU43")}) == 16.0


def test_sorriso_largo_nao_conta_bochecha_nem_labio():
    sorriso = {"AU06": 0.77, "AU07": 0.61, "AU10": 0.96, "AU12": 0.99}  # Py-Feat v2 num rosto sorrindo
    assert pspi_de_aus(sorriso) == 3.05  # só AU7
    assert pspi_de_aus({**sorriso, "AU12": 0.3}) == 3.85 + 4.8


def test_confirma_so_dor_moderada():
    leve = {"AU07": 0.6}  # PSPI 3,0: o estágio 1 suspeitaria, o estágio 2 descarta
    assert confirmar(AvaliadorFalso([leve]), [b"s"])["confirmado"] is False
    moderada = {"AU07": 0.7}  # PSPI 3,5
    assert confirmar(AvaliadorFalso([moderada]), [b"s"])["confirmado"] is True


def test_pspi_de_aus_ignora_valores_invalidos():
    assert pspi_de_aus({"AU04": float("nan"), "AU07": None}) == 0.0


def test_confirma_dor_descontando_o_rosto_neutro():
    out = confirmar(AvaliadorFalso([NEUTRO_AUS, DOR_AUS, DOR_AUS, DOR_AUS]), [b"s1", b"s2", b"s3"], neutro=b"n")
    assert out["confirmado"] is True and out["faces_avaliadas"] == 3
    assert out["pspi_base"] == pspi_de_aus(NEUTRO_AUS)
    assert out["dor_relativa"] == round(pspi_de_aus(DOR_AUS) - pspi_de_aus(NEUTRO_AUS), 2)
    assert out["wong_baker"] == wong_baker(out["dor_relativa"]) and out["detector"] == "falso"


def test_descarta_quando_o_rosto_nao_mostra_dor():
    out = confirmar(AvaliadorFalso([NEUTRO_AUS, NEUTRO_AUS]), [b"s1", b"s2"])
    assert out["confirmado"] is False and out["pspi_base"] == 0.0
    assert out["wong_baker"] == 2  # sem rosto neutro, o tônus normal (PSPI 1,5) não é descontado


def test_mediana_resiste_a_um_quadro_ruim():
    out = confirmar(AvaliadorFalso([NEUTRO_AUS, NEUTRO_AUS, DOR_AUS]), [b"a", b"b", b"c"])
    assert out["confirmado"] is False


def test_base_neutra_tem_teto():
    out = confirmar(AvaliadorFalso([DOR_AUS, DOR_AUS]), [b"s"], neutro=b"n")
    assert out["pspi_base"] == 3.0  # quem chega com dor não zera a régua


def test_sem_rosto_nos_suspeitos_e_recusado():
    with pytest.raises(SemRostoNosRecortes):
        confirmar(AvaliadorFalso([None, None]), [b"a", b"b"])
    with pytest.raises(ValueError):
        confirmar(AvaliadorFalso([]), [])


def test_neutro_sem_rosto_usa_base_zero():
    out = confirmar(AvaliadorFalso([None, DOR_AUS]), [b"s"], neutro=b"n")
    assert out["pspi_base"] == 0.0 and out["faces_avaliadas"] == 1
