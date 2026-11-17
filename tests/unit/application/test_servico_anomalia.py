"""ServicoAnomalia com motor, corpus e repositórios falsos: nenhum banco nem scikit-learn."""
from __future__ import annotations

import pytest

from application.anomalia.servico import ServicoAnomalia
from domain.anomalia.modelo import DetectorDeFaixaFixaRecusado, ModeloAusente, ModeloDeAnomalia
from tests.fakes import IdsSequenciais, RelogioFixo, UnidadeDeTrabalhoFalsa

LINHA = {"hr": 80, "sbp": 120, "dbp": 80, "spo2": 98}


class MotorFalso:
    def __init__(self, picos=None):
        self.picos = picos
        self.treinado_com = None

    def treinar(self, linhas):
        self.treinado_com = len(linhas)
        return {"artefato": True}

    def picos_anomalos(self, artefato, linhas):
        return self.picos


class CorpusFalso:
    def __init__(self, n):
        self.n = n

    def linhas_de_treino(self):
        return [LINHA] * self.n

    def serie(self, serie_id):
        return [LINHA] * 3 if serie_id == "p000057" else None


class Modelos:
    def __init__(self):
        self.itens = {}

    def adicionar(self, modelo):
        self.itens[modelo.id] = modelo

    def obter(self, modelo_id):
        return self.itens.get(modelo_id)

    def listar(self):
        return [{"id": m.id, "criado_em": m.criado_em} for m in self.itens.values()]


class Alertas:
    def __init__(self):
        self.itens = []

    def adicionar(self, alerta):
        self.itens.append(alerta)

    def listar(self):
        return [{"id": a.id, "serie_id": a.serie_id} for a in self.itens]


def _servico(motor=None, corpus=None):
    modelos, alertas, uow = Modelos(), Alertas(), UnidadeDeTrabalhoFalsa()
    servico = ServicoAnomalia(modelos, alertas, motor or MotorFalso(), corpus or CorpusFalso(30),
                              uow, RelogioFixo(), IdsSequenciais("alerta"))
    return servico, modelos, alertas, uow


def test_treina_no_corpus_e_grava_o_modelo():
    servico, modelos, _, uow = _servico()
    assert servico.treinar("m1") == "m1"
    assert modelos.obter("m1").treinado_no_corpus is True and uow.commits == 1


def test_corpus_insuficiente_nao_vira_modelo():
    servico, modelos, _, _ = _servico(corpus=CorpusFalso(10))
    with pytest.raises(ModeloAusente):
        servico.treinar("m1")
    assert modelos.itens == {}


def test_serie_compativel_nao_abre_alerta():
    servico, _, alertas, _ = _servico(motor=MotorFalso(picos=None))
    servico.treinar("m1")
    leitura = servico.avaliar_serie("m1", "p000057", [LINHA] * 3)
    assert leitura["resultado"] == "compativel" and leitura["alerta_id"] is None and alertas.itens == []
    assert leitura["sepse"] is None and leitura["diagnostico"] is None


def test_serie_anomala_abre_alerta_com_sinais():
    servico, _, alertas, _ = _servico(motor=MotorFalso(picos=[0.5, 1.0, 1.0, 4.0]))
    servico.treinar("m1")
    leitura = servico.avaliar_serie("m1", "p000003", [LINHA] * 3)
    assert leitura["resultado"] == "anomala" and leitura["sinais"] == ["oxigenacao"]
    assert alertas.itens[0].serie_id == "p000003" and alertas.itens[0].estado == "aberto"
    assert servico.alertas() == [{"id": "alerta-1", "serie_id": "p000003"}]


def test_modelo_ausente_ou_nao_treinado_e_recusado():
    servico, modelos, _, _ = _servico()
    with pytest.raises(ModeloAusente):
        servico.avaliar_serie("nao-existe", "p1", [LINHA])
    modelos.adicionar(ModeloDeAnomalia("faixa", False, None))
    with pytest.raises(ModeloAusente):
        servico.avaliar_serie("faixa", "p1", [LINHA])


def test_faixa_fixa_nao_substitui_modelo():
    servico, _, _, _ = _servico()
    with pytest.raises(DetectorDeFaixaFixaRecusado):
        servico.avaliar_faixa_fixa()


def test_serie_do_corpus_ou_ausente():
    servico, _, _, _ = _servico()
    servico.treinar("m1")
    assert servico.avaliar_serie_do_corpus("m1", "p000057")["resultado"] == "compativel"
    assert servico.avaliar_serie_do_corpus("m1", "nao-existe") is None
