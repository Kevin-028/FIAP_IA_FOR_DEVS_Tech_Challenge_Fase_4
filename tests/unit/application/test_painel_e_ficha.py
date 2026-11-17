"""Leituras novas para as telas Hoje, ficha do paciente, alertas unificados e Sistema."""
from __future__ import annotations

import pytest

from application.sistema import ServicoSistema
from domain.atendimento.paciente import PacienteInexistente
from tests.memoria import Atendimento


def _consulta(app, paciente_id, nome, sessao_id):
    app.cadastro.cadastrar(paciente_id, nome)
    app.consulta.iniciar(sessao_id, paciente_id)
    app.relogio.avancar(60)


def test_em_andamento_traz_nome_e_alertas_ativos():
    app = Atendimento()
    _consulta(app, "p1", "Ana Lima", "s1")
    _consulta(app, "p2", "Bia Souza", "s2")
    app.consulta.registrar_observacao("s2", {"mancando": True})
    app.consulta.encerrar_sessao("s1")
    andamento = app.consulta.em_andamento()
    assert [(c["sessao_id"], c["paciente_nome"], c["alertas_ativos"]) for c in andamento] == [("s2", "Bia Souza", 1)]


def test_ficha_do_paciente_com_historico_mais_recente_primeiro():
    app = Atendimento()
    _consulta(app, "p1", "Ana Lima", "s1")
    app.consulta.encerrar_sessao("s1")
    app.consulta.iniciar("s2", "p1")
    ficha = app.consulta.ficha("p1")
    assert ficha["paciente"] == {"id": "p1", "nome": "Ana Lima"}
    assert [s["sessao_id"] for s in ficha["sessoes"]] == ["s2", "s1"]
    assert ficha["sessoes"][1]["estado"] == "encerrada" and ficha["em_andamento"] == "s2"
    with pytest.raises(PacienteInexistente):
        app.consulta.ficha("nao-existe")


def test_alertas_de_dor_ativos_com_paciente():
    app = Atendimento()
    _consulta(app, "p1", "Ana Lima", "s1")
    app.consulta.registrar_observacao("s1", {"texto": "uma pontada", "mancando": True})
    alertas = app.consulta.alertas_de_dor_ativos()
    assert {a["origem"] for a in alertas} == {"relato", "movimentacao"}
    assert all(a["paciente_nome"] == "Ana Lima" and a["sessao_id"] == "s1" for a in alertas)
    app.consulta.encerrar_dor(alertas[0]["id"])
    assert len(app.consulta.alertas_de_dor_ativos()) == 1


def test_busca_de_paciente_ignora_acento_e_caixa():
    app = Atendimento()
    app.cadastro.cadastrar("p1", "Ana Lúcia")
    app.cadastro.cadastrar("p2", "Bruno")
    assert [p["id"] for p in app.cadastro.listar("lucia")] == ["p1"]
    assert len(app.cadastro.listar("")) == 2


class _Porta:
    def __init__(self, faltando=(), disponivel=True):
        self._faltando, self._disponivel = list(faltando), disponivel

    def faltando(self):
        return self._faltando

    def disponivel(self):
        return self._disponivel


class _Inventario:
    def itens(self):
        return [{"nome": "MediaPipe Pose", "ok": False, "detalhe": "rode python scripts/download_pose.py"}]


def test_sistema_lista_o_que_falta_configurar():
    sistema = ServicoSistema(_Porta(faltando=["AZURE_SPEECH_KEY"]), _Porta(), _Porta(disponivel=False), _Inventario())
    itens = {i["nome"]: i for i in sistema.diagnostico()}
    assert itens["Azure Speech"]["ok"] is False and "AZURE_SPEECH_KEY" in itens["Azure Speech"]["detalhe"]
    assert itens["Azure Language"]["ok"] is True
    assert itens["Estágio 2 da dor (Py-Feat)"]["ok"] is False
    assert itens["MediaPipe Pose"]["ok"] is False
    assert sistema.pendencias() == 3
