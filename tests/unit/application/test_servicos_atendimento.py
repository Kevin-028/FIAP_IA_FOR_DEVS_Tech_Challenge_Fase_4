"""Casos de uso do Atendimento com repositórios em memória (sem SQLite, Azure ou Py-Feat)."""
from __future__ import annotations

import pytest

from application.atendimento.portas import Estagio2Indisponivel
from domain.atendimento.alerta_dor import AlertaDeDorRecusado
from domain.atendimento.cascata import SemRostoNosRecortes
from domain.atendimento.paciente import ExclusaoDePacienteRecusada, NomeInvalido, PacienteInexistente
from domain.atendimento.sessao import SessaoRecusada
from tests.memoria import AnalisadorFalso, Atendimento, Estagio2Falso

NEUTRO = {"eyeSquintLeft": 0.15, "eyeSquintRight": 0.15, "browDownLeft": 0.05, "browDownRight": 0.05}
LEVE = {**NEUTRO, "eyeSquintLeft": 0.6, "eyeSquintRight": 0.6}
DOR = {"browDownLeft": 0.6, "browDownRight": 0.6, "eyeSquintLeft": 0.7, "eyeSquintRight": 0.7,
       "noseSneerLeft": 0.4, "noseSneerRight": 0.4}
DOR_AUS = {"AU04": 0.8, "AU06": 0.4, "AU07": 0.9, "AU09": 0.6, "AU10": 0.3, "AU43": 0.7}
NEUTRO_AUS = {"AU04": 0.05, "AU07": 0.2}


def _leituras(app, sessao, rostos):
    saidas = []
    for rosto in rostos:
        saidas.append(app.camera.registrar_leitura(sessao, rosto))
        app.relogio.avancar(1)
    return saidas


def test_cadastro_corrige_e_recusa_exclusao():
    app = Atendimento()
    app.cadastro.cadastrar("p1", "  Ana  ")
    app.cadastro.corrigir("p1", "Ana Lima")
    assert app.cadastro.listar() == [{"id": "p1", "nome": "Ana Lima"}]
    with pytest.raises(NomeInvalido):
        app.cadastro.corrigir("nao-existe", " ")
    with pytest.raises(PacienteInexistente):
        app.cadastro.corrigir("nao-existe", "Bia")
    with pytest.raises(ExclusaoDePacienteRecusada):
        app.cadastro.excluir("p1")


def test_sessao_so_nasce_de_paciente_cadastrado():
    app = Atendimento()
    with pytest.raises(PacienteInexistente):
        app.consulta.iniciar("s1", "fantasma")


def test_observacao_retem_leitura_e_abre_um_alerta_por_origem():
    app = Atendimento()
    sessao = app.sessao_em_andamento()
    metrica = app.consulta.registrar_observacao(sessao, {"texto": "senti uma pontada", "mancando": True,
                                                         "face_dor": True})
    assert metrica["fala"]["transcricao"] == "senti uma pontada"
    assert sorted(a["origem"] for a in metrica["alertas_dor"]) == ["face", "movimentacao", "relato"]


def test_ciclo_do_alerta_de_dor_e_sessao_encerrada():
    app = Atendimento()
    sessao = app.sessao_em_andamento()
    alerta_id = app.consulta.registrar_observacao(sessao, {"mancando": True})["alertas_dor"][0]["id"]
    app.consulta.dar_ciencia_dor(alerta_id)
    app.consulta.encerrar_dor(alerta_id)
    with pytest.raises(AlertaDeDorRecusado):
        app.consulta.dar_ciencia_dor(alerta_id)
    app.consulta.encerrar_sessao(sessao)
    with pytest.raises(SessaoRecusada):
        app.consulta.registrar_observacao(sessao, {"texto": "oi"})
    assert app.consulta.relatorio(sessao)["estado"] == "encerrada"


def test_sem_estagio2_dor_moderada_sustentada_abre_alerta():
    app = Atendimento()
    sessao = app.sessao_em_andamento()
    saidas = _leituras(app, sessao, [NEUTRO] * 5 + [DOR] * 3)
    assert saidas[-1]["alerta_dor"] is True and saidas[-1]["estagio2"] is False
    assert saidas[-1]["suspeita"] is True  # sem validador a marca de atenção também é gravada (ADR-004)


def test_com_estagio2_so_dor_acima_do_nivel_5_vira_suspeita_e_nao_abre_alerta():
    app = Atendimento(estagio2=Estagio2Falso())
    sessao = app.sessao_em_andamento()
    leves = _leituras(app, sessao, [NEUTRO] * 5 + [LEVE] * 3)
    assert not any(s["suspeita"] for s in leves)  # face 4: não grava
    saidas = _leituras(app, sessao, [DOR] * 3)
    assert [s["suspeita"] for s in saidas] == [False, False, True]
    assert app.alertas.itens == {}


def test_confirmacao_chama_o_detector_uma_vez_e_abre_alerta():
    estagio2 = Estagio2Falso([NEUTRO_AUS, DOR_AUS, DOR_AUS, DOR_AUS])
    app = Atendimento(estagio2=estagio2)
    sessao = app.sessao_em_andamento()
    out = app.cascata.confirmar(sessao, [b"s1", b"s2", b"s3"], b"neutro")
    assert estagio2.chamadas == [4]  # neutro + suspeitos num lote só
    assert out["alerta_dor"] is True and out["confirmacao"]["confirmado"] is True
    assert "Wong-Baker" in next(iter(app.alertas.itens.values())).descricao_sinal


def test_confirmacao_sem_estagio2_ou_sem_rosto():
    app = Atendimento()
    sessao = app.sessao_em_andamento()
    with pytest.raises(Estagio2Indisponivel):
        app.cascata.confirmar(sessao, [b"s"])
    app = Atendimento(estagio2=Estagio2Falso([None]))
    sessao = app.sessao_em_andamento()
    with pytest.raises(SemRostoNosRecortes):
        app.cascata.confirmar(sessao, [b"s"])


def test_autorrelato_guarda_estimativa_da_camera():
    app = Atendimento()
    sessao = app.sessao_em_andamento()
    _leituras(app, sessao, [NEUTRO] * 5)
    relato = app.cascata.registrar_autorrelato(sessao, 6)
    assert relato["estimado"] == 0 and relato["origem_estimativa"] == "estagio1"
    with pytest.raises(ValueError):
        app.cascata.registrar_autorrelato(sessao, 5)


def test_fala_do_paciente_abre_dor_por_relato_e_pergunta_do_medico_nao():
    app = Atendimento()
    sessao = app.sessao_em_andamento()
    app.conversa.registrar_fala(sessao, "Bom dia, o que trouxe a senhora aqui? Tem dor no peito?", locutor="G1")
    app.conversa.registrar_fala(sessao, "Doutor, estou com dor no peito faz dois dias.", locutor="G2")
    dados = app.conversa.transcricao(sessao)
    assert dados["locutores"] == {"G1": "medico", "G2": "paciente"}
    assert [a.origem for a in app.alertas.itens.values()] == ["relato"]


def test_falha_do_analisador_nao_para_a_conversa():
    app = Atendimento(analisador=AnalisadorFalso(erro=RuntimeError("fora do ar")))
    sessao = app.sessao_em_andamento()
    out = app.conversa.registrar_fala(sessao, "estou bem", locutor="G2")
    assert out["aviso"].startswith("Azure Text Analytics indisponivel") and out["fala"]["sentimento"] == ""
