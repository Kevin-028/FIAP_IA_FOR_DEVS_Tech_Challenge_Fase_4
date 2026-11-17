"""Expressão facial e indicador de dor (PSPI) a partir de blendshapes."""
from __future__ import annotations

import pytest

from domain.atendimento.dor_facial import classificar_expressao, linha_de_base, nivel_dor, pspi

NEUTRO = {"eyeSquintLeft": 0.15, "eyeSquintRight": 0.15, "browDownLeft": 0.05, "browDownRight": 0.05}


def _rosto(**valores):
    return {**NEUTRO, **valores}


def _par(nome, valor):
    return {nome + "Left": valor, nome + "Right": valor}


def test_rosto_neutro():
    out = classificar_expressao(NEUTRO, base_pspi=pspi(NEUTRO))
    assert out["expressao"] == "neutra" and out["valencia"] == "neutra" and out["nivel_dor"] == "ausente"


def test_sorriso_e_feliz_e_nao_conta_como_dor():
    rosto = _rosto(**_par("mouthSmile", 0.8), **_par("cheekSquint", 0.7))
    out = classificar_expressao(rosto, base_pspi=pspi(NEUTRO))
    assert out["expressao"] == "feliz" and out["valencia"] == "positiva"
    assert out["nivel_dor"] == "ausente"  # bochecha do sorriso (Duchenne) não soma no PSPI


def test_careta_de_dor():
    rosto = _rosto(**_par("browDown", 0.6), **_par("eyeSquint", 0.7), **_par("noseSneer", 0.4))
    out = classificar_expressao(rosto, base_pspi=pspi(NEUTRO))
    assert out["expressao"] == "dor/desconforto" and out["valencia"] == "negativa"
    assert out["nivel_dor"] == "moderada" and out["dor_pspi"] > 6


def test_tristeza():
    rosto = _rosto(**_par("mouthFrown", 0.6), browInnerUp=0.6)
    assert classificar_expressao(rosto, base_pspi=pspi(NEUTRO))["expressao"] == "triste"


def test_surpresa():
    rosto = _rosto(**_par("eyeWide", 0.7), browInnerUp=0.4)
    assert classificar_expressao(rosto, base_pspi=pspi(NEUTRO))["expressao"] == "surpresa/apreensão"


def test_pspi_componentes_e_olhos_fechados():
    assert pspi({}) == 0.0
    assert pspi(_par("browDown", 1.0)) == 5.0
    assert pspi({**_par("cheekSquint", 0.4), **_par("eyeSquint", 0.6)}) == 3.0  # max(AU6, AU7)
    assert pspi({**_par("noseSneer", 0.2), **_par("mouthUpperUp", 0.4)}) == 2.0  # max(AU9, AU10)
    assert pspi(_par("eyeBlink", 0.9)) == 1.0
    tudo = {**_par("browDown", 1), **_par("eyeSquint", 1), **_par("noseSneer", 1), **_par("eyeBlink", 1)}
    assert pspi(tudo) == 16.0


def test_linha_de_base_e_mediana_limitada():
    assert linha_de_base([]) == 0.0
    assert linha_de_base([1.0, 1.5, 9.0]) == 1.5
    assert linha_de_base([8.0, 8.0, 8.0]) == 3.0  # quem chega com dor não zera a régua


def test_linha_de_base_compensa_rosto_naturalmente_tenso():
    tenso = _rosto(**_par("eyeSquint", 0.45))
    assert classificar_expressao(tenso, base_pspi=0.0)["nivel_dor"] == "leve"
    assert classificar_expressao(tenso, base_pspi=pspi(tenso))["nivel_dor"] == "ausente"


@pytest.mark.parametrize(("relativa", "nivel"), [(0, "ausente"), (1.9, "ausente"), (2, "leve"), (3.5, "moderada")])
def test_niveis_de_dor(relativa, nivel):
    assert nivel_dor(relativa) == nivel
