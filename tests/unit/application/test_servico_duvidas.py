"""Marcas de atenção com repositórios e armazém em memória: gravar na suspeita, veredito depois, médico classifica."""
from __future__ import annotations

import pytest

from application.atendimento.servico_duvidas import DuvidaInexistente
from domain.atendimento.sessao import SessaoRecusada
from tests.memoria import Atendimento

QUADROS = [b"\xff\xd8\xff" + bytes([i]) for i in range(12)]
LEVE = {"browDownLeft": 0.3, "browDownRight": 0.3, "eyeSquintLeft": 0.3, "eyeSquintRight": 0.3}


def _confirmar(app, sessao, relativa, confirmado):
    resultado = {"detector": "falso", "pspi": relativa, "pspi_base": 0.0, "dor_relativa": relativa,
                 "wong_baker": 2 if relativa < 2 else 4, "confirmado": confirmado, "faces_avaliadas": 3}
    return app.cascata.registrar_confirmacao(sessao, resultado)["confirmacao"]["id"]


def test_marca_fica_disponivel_na_hora_avaliando():
    app = Atendimento()
    sessao = app.sessao_em_andamento()
    marca = app.duvidas.registrar(sessao, QUADROS, 3.0)
    assert marca["avaliando"] and marca["veredito_texto"] == "Avaliando…" and marca["quadros"] == 12
    assert app.armazem.quadros[marca["id"]] == QUADROS and app.duvidas.pendentes() == 1
    assert app.duvidas.quadro(marca["id"], 11) == QUADROS[11] and app.duvidas.quadro(marca["id"], 12) is None
    assert [d["id"] for d in app.duvidas.da_sessao(sessao)] == [marca["id"]]


def test_marca_guarda_a_estimativa_do_estagio1():
    app = Atendimento()
    sessao = app.sessao_em_andamento()
    app.camera.registrar_leitura(sessao, LEVE)
    marca = app.duvidas.registrar(sessao, QUADROS, 3.0)
    assert marca["wong_baker_estimado"] is not None and marca["dor_relativa"] is not None


def test_veredito_do_validador_entra_depois():
    app = Atendimento()
    sessao = app.sessao_em_andamento()
    marca = app.duvidas.registrar(sessao, QUADROS, 3.0)["id"]
    visao = app.duvidas.registrar_veredito(sessao, marca, _confirmar(app, sessao, 0.5, False))
    assert visao["veredito"] == "descartada" and visao["veredito_texto"] == "Validador descartou (+0.5)"
    with pytest.raises(ValueError):  # um veredito por marca
        app.duvidas.registrar_veredito(sessao, marca, None)


def test_sem_validador_a_marca_continua_valendo():
    app = Atendimento()
    sessao = app.sessao_em_andamento()
    marca = app.duvidas.registrar(sessao, QUADROS, 2.5)["id"]
    visao = app.duvidas.registrar_veredito(sessao, marca, None)
    assert visao["veredito"] == "sem_resultado" and visao["pendente"]


def test_veredito_recusa_confirmacao_ou_marca_de_outra_consulta():
    app = Atendimento()
    sessao = app.sessao_em_andamento()
    marca = app.duvidas.registrar(sessao, QUADROS, 3.0)["id"]
    with pytest.raises(ValueError):
        app.duvidas.registrar_veredito(sessao, marca, "nao-existe")
    with pytest.raises(DuvidaInexistente):
        app.duvidas.registrar_veredito("outra", marca, None)


def test_veredito_chega_mesmo_com_a_consulta_encerrada():
    app = Atendimento()
    sessao = app.sessao_em_andamento()
    marca = app.duvidas.registrar(sessao, QUADROS, 3.0)["id"]
    confirmacao = _confirmar(app, sessao, 8.0, True)
    app.consulta.encerrar_sessao(sessao)
    assert app.duvidas.registrar_veredito(sessao, marca, confirmacao)["veredito"] == "confirmada"
    with pytest.raises(SessaoRecusada):  # gravar recorte novo, não
        app.duvidas.registrar(sessao, QUADROS, 3.0)


def test_recorte_fora_das_regras_nao_grava_nada():
    app = Atendimento()
    sessao = app.sessao_em_andamento()
    with pytest.raises(ValueError):
        app.duvidas.registrar(sessao, QUADROS[:1], 3.0)
    with pytest.raises(ValueError):
        app.duvidas.registrar(sessao, QUADROS, 5.0)
    assert app.armazem.quadros == {}


def test_medico_classifica_e_a_fila_avanca():
    app = Atendimento()
    sessao = app.sessao_em_andamento()
    primeira = app.duvidas.registrar(sessao, QUADROS, 3.0)["id"]
    app.relogio.avancar(30)
    segunda = app.duvidas.registrar(sessao, QUADROS, 2.5)["id"]
    assert app.duvidas.proxima_pendente() == primeira
    visao = app.duvidas.classificar(primeira, 6, "dor", "careta ao levantar")
    assert visao["categoria_texto"] == "Dor" and visao["paciente_nome"] == "Ana Lima" and not visao["pendente"]
    assert app.duvidas.proxima_pendente(depois_de=primeira) == segunda
    assert [d["id"] for d in app.duvidas.listar(False)] == [primeira]
    with pytest.raises(DuvidaInexistente):
        app.duvidas.classificar("nao-existe", 0, "sem_dor")
