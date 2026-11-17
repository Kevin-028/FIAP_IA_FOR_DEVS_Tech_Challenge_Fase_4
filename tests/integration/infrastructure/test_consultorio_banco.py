"""Consultório no SQLite: cadastro, sessão, transcrição, dor e modelo treinado (casos de uso reais)."""
from __future__ import annotations

import sqlite3

import pytest

from domain.atendimento.paciente import ExclusaoDePacienteRecusada, NomeInvalido, PacienteInexistente
from domain.atendimento.sessao import SessaoRecusada
from tests.memoria import AnalisadorFalso


@pytest.fixture()
def sessao(servicos):
    servicos.cadastro.cadastrar("pac-1", "Bia Souza")
    servicos.consulta.iniciar("ses-1", "pac-1")
    return "ses-1"


def _ficha(servicos):
    return [(p["id"], p["nome"]) for p in servicos.cadastro.listar()]


def test_cadastro_lista_corrige_e_recusa_exclusao(conn, servicos):
    servicos.cadastro.cadastrar("pac-ana", "Ana Lima")
    servicos.cadastro.corrigir("pac-ana", "Ana Lima Souza")
    assert ("pac-ana", "Ana Lima Souza") in _ficha(servicos)
    with pytest.raises(NomeInvalido):
        servicos.cadastro.cadastrar("pac-x", "   ")
    with pytest.raises(PacienteInexistente):
        servicos.cadastro.corrigir("ninguem", "X")
    with pytest.raises(ExclusaoDePacienteRecusada):
        servicos.cadastro.excluir("pac-ana")
    with pytest.raises(sqlite3.DatabaseError):
        conn.execute("DELETE FROM pacientes WHERE id = 'pac-ana'")  # trigger também recusa
    assert ("pac-ana", "Ana Lima Souza") in _ficha(servicos)


def test_sessao_reune_fala_movimento_e_dor(servicos, sessao):
    with pytest.raises(PacienteInexistente):
        servicos.consulta.iniciar("ses-vazia", "ninguem")
    servicos.consulta.registrar_observacao(sessao, {
        "texto": "sinto uma pontada e estou mancando", "face_dor": True, "alteracao_vocal": "cansaco",
        "postura": "mancando", "face": "dor na face", "sentimento": "negative", "termos_criticos": "pontada",
    })
    leitura = servicos.consulta.metrica(sessao)
    assert {"face", "movimentacao", "relato"} <= {a["origem"] for a in leitura["alertas_dor"]}
    assert servicos.consulta.relatorio(sessao)["desvios"]["postura"] == "mancando"


def test_ciclo_do_alerta_de_dor(servicos, sessao):
    servicos.consulta.registrar_observacao(sessao, {"texto": "pontada"})
    alerta = servicos.consulta.metrica(sessao)["alertas_dor"][0]["id"]
    servicos.consulta.dar_ciencia_dor(alerta)
    servicos.consulta.dar_ciencia_dor(alerta)  # idempotente
    servicos.consulta.encerrar_dor(alerta)
    assert servicos.consulta.metrica(sessao)["alertas_dor"][0]["estado"] == "encerrado"
    with pytest.raises(SessaoRecusada):
        servicos.consulta.encerrar_dor(alerta)


@pytest.mark.parametrize("analisador", [AnalisadorFalso({"sentiment": "negative", "key_phrases": ["pontada no peito"]})])
def test_transcricao_grava_falas_pontos_e_dor_sem_duplicar(servicos, sessao):
    conversa = servicos.conversa
    conversa.definir_papel(sessao, "Guest-1", "medico")
    conversa.definir_papel(sessao, "Guest-2", "paciente")
    assert conversa.registrar_fala(sessao, "Sente dor no peito?", locutor="Guest-1")["pontos"] == []
    out = conversa.registrar_fala(sessao, "Sinto uma pontada no peito há dois dias.", locutor="Guest-2",
                                  offset_ms=4200)
    assert {"Dor", "Tempo de evolução", "Sentimento negativo"} <= {p["categoria"] for p in out["pontos"]}
    conversa.registrar_fala(sessao, "A pontada continua.", locutor="Guest-2")

    dados = conversa.transcricao(sessao)
    assert [f["ordem"] for f in dados["falas"]] == [1, 2, 3]
    assert dados["falas"][1]["papel"] == "paciente" and dados["falas"][1]["offset_ms"] == 4200
    assert dados["pontos"][0]["severidade"] in ("alta", "media")
    leitura = servicos.consulta.metrica(sessao)
    assert len([a for a in leitura["alertas_dor"] if a["origem"] == "relato"]) == 1
    assert "Dor" in leitura["fala"]["termos_criticos"] and leitura["fala"]["sentimento"] == "negative"


def test_papel_pode_ser_corrigido(servicos, sessao):
    servicos.conversa.definir_papel(sessao, "Guest-1", "medico")
    servicos.conversa.definir_papel(sessao, "Guest-1", "paciente")
    assert servicos.conversa.transcricao(sessao)["locutores"] == {"Guest-1": "paciente"}
    with pytest.raises(ValueError):
        servicos.conversa.definir_papel(sessao, "Guest-1", "enfermeiro")


@pytest.mark.parametrize("analisador", [AnalisadorFalso(erro=RuntimeError("timeout"))])
def test_falha_do_azure_nao_para_a_transcricao(servicos, sessao):
    out = servicos.conversa.registrar_fala(sessao, "Estou com febre.", locutor="Guest-2")
    assert out["aviso"] and {p["categoria"] for p in out["pontos"]} == {"Febre"}


def test_fala_vazia_e_sessao_encerrada_sao_recusadas(servicos, sessao):
    with pytest.raises(ValueError):
        servicos.conversa.registrar_fala(sessao, "   ")
    servicos.consulta.encerrar_sessao(sessao)
    with pytest.raises(SessaoRecusada):
        servicos.conversa.registrar_fala(sessao, "oi")
    with pytest.raises(SessaoRecusada):
        servicos.conversa.transcricao("nao-existe")


def test_modelo_treinado_no_corpus_nao_devolve_sepse(servicos):
    servicos.anomalia.treinar("modelo-1")
    leitura = servicos.anomalia.avaliar_serie_do_corpus("modelo-1", "p000057")
    assert leitura["sepse"] is None and leitura["diagnostico"] is None
    assert leitura["resultado"] in ("compativel", "anomala")
