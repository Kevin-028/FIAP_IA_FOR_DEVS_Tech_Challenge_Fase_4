"""Fila do validador: toda marca é avaliada, uma de cada vez, com os quadros dela, e o veredito cai na marca certa."""
from __future__ import annotations

from tests.memoria import Atendimento, Estagio2Falso

QUADROS = [b"\xff\xd8\xff" + bytes([i]) for i in range(12)]   # centro do recorte: quadros 5, 6 e 7
NEUTRO = b"\xff\xd8\xffN"
DOR_AUS = {"AU04": 0.8, "AU06": 0.4, "AU07": 0.9, "AU09": 0.6, "AU10": 0.3, "AU43": 0.7}
NEUTRO_AUS = {"AU04": 0.05, "AU07": 0.2}


def _recorte(marca: int) -> list[bytes]:
    return [q + bytes([marca]) for q in QUADROS]


def _respostas(*rostos):
    """Cada avaliação manda neutro + 3 quadros do centro do recorte."""
    return [aus for rosto in rostos for aus in (NEUTRO_AUS, rosto, rosto, rosto)]


def test_marca_fica_disponivel_e_entra_na_fila_sem_esperar_o_validador():
    app = Atendimento(estagio2=Estagio2Falso(_respostas(DOR_AUS)))
    sessao = app.sessao_em_andamento()
    marca = app.validacao.receber(sessao, QUADROS, 3.0, NEUTRO)
    assert marca["avaliando"] is True and app.fila.pendentes() == 1
    assert app.estagio2.chamadas == []  # nada roda antes da vez dele na fila


def test_todas_as_marcas_sao_avaliadas_em_ordem_e_cada_veredito_na_sua_marca():
    app = Atendimento(estagio2=Estagio2Falso(_respostas(DOR_AUS, NEUTRO_AUS, DOR_AUS)))
    sessao = app.sessao_em_andamento()
    marcas = [app.validacao.receber(sessao, _recorte(i), 3.0, NEUTRO)["id"] for i in range(3)]
    assert app.fila.pendentes() == 3
    app.fila.executar_todas()
    vereditos = [app.duvidas.obter(m)["veredito"] for m in marcas]
    assert vereditos == ["confirmada", "descartada", "confirmada"]
    assert app.estagio2.chamadas == [4, 4, 4]
    for i, imagens in enumerate(app.estagio2.vistas):  # carimbo: o validador viu o centro do recorte da própria marca
        assert imagens == [NEUTRO] + _recorte(i)[5:8]
    confirmacoes = {app.duvidas.obter(m)["confirmacao_id"] for m in marcas}
    assert len(confirmacoes) == 3


def test_sem_validador_instalado_a_marca_fica_sem_resultado():
    app = Atendimento()  # estágio 2 indisponível
    sessao = app.sessao_em_andamento()
    marca = app.validacao.receber(sessao, QUADROS, 3.0)["id"]
    app.fila.executar_todas()
    assert app.duvidas.obter(marca)["veredito"] == "sem_resultado"


def test_falha_do_validador_nao_trava_a_fila():
    app = Atendimento(estagio2=Estagio2Falso(_respostas(DOR_AUS)))
    sessao = app.sessao_em_andamento()
    app.estagio2.falhar_na_chamada = 1
    primeira = app.validacao.receber(sessao, _recorte(0), 3.0, NEUTRO)["id"]
    segunda = app.validacao.receber(sessao, _recorte(1), 3.0, NEUTRO)["id"]
    app.fila.executar_todas()
    assert app.duvidas.obter(primeira)["veredito"] == "sem_resultado"
    assert app.duvidas.obter(segunda)["veredito"] == "confirmada"


def test_marca_e_avaliada_mesmo_se_a_consulta_encerrar_antes_da_vez_dela():
    app = Atendimento(estagio2=Estagio2Falso(_respostas(DOR_AUS)))
    sessao = app.sessao_em_andamento()
    marca = app.validacao.receber(sessao, QUADROS, 3.0, NEUTRO)["id"]
    app.consulta.encerrar_sessao(sessao)
    app.fila.executar_todas()
    assert app.duvidas.obter(marca)["veredito"] == "confirmada"
    assert app.alertas.itens == {}  # consulta encerrada: registra o veredito, não abre alerta
