"""Regras do contexto Anomalia de padrão."""
from __future__ import annotations

import pytest

from domain.anomalia.alerta import AlertaDeAnomalia, leitura_de_anomalia
from domain.anomalia.modelo import ModeloAusente, ModeloDeAnomalia, nomear_sinais


def test_sinais_acima_de_dois_desvios_do_mais_forte_ao_mais_fraco():
    assert nomear_sinais([2.5, 3.0, 1.0, 4.0]) == ["oxigenacao", "pressao_arterial", "batimentos"]


def test_sem_sinal_forte_aponta_o_maior():
    assert nomear_sinais([0.5, 1.2, 0.3, 0.1]) == ["pressao_arterial"]


def test_modelo_exige_corpus_minimo():
    with pytest.raises(ModeloAusente):
        ModeloDeAnomalia.treinado("m", object(), 23, "agora")
    assert ModeloDeAnomalia.treinado("m", object(), 24, "agora").treinado_no_corpus


def test_alerta_so_com_sinais_validos():
    with pytest.raises(ValueError):
        AlertaDeAnomalia.abrir("a", "s", "m", [], "agora")
    with pytest.raises(ValueError):
        AlertaDeAnomalia.abrir("a", "s", "m", ["sepse"], "agora")
    assert AlertaDeAnomalia.abrir("a", "s", "m", ["batimentos"], "agora").estado == "aberto"


def test_leitura_nunca_traz_sepse_nem_diagnostico():
    alerta = AlertaDeAnomalia.abrir("a", "s", "m", ["oxigenacao"], "agora")
    leitura = leitura_de_anomalia("s", "m", alerta)
    assert leitura["resultado"] == "anomala" and leitura["sepse"] is None and leitura["diagnostico"] is None
    assert leitura_de_anomalia("s", "m", None)["resultado"] == "compativel"
