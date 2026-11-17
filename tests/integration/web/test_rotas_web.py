"""Rotas Flask ponta a ponta, com banco temporário e sem Azure."""
from __future__ import annotations

from uuid import uuid4

import pytest
from flask import template_rendered

from infrastructure.persistencia.banco import emit_alert, get_alert

PAGINAS = ("/", "/pacientes", "/alertas", "/alertas?aba=internacao", "/alertas?aba=anomalia", "/internacao",
           "/internacao/exames", "/internacao/monitor", "/sistema")
SECAO_POR_ROTA = {
    "/": "hoje",
    "/pacientes": "pacientes",
    "/alertas": "alertas",
    "/internacao": "internacao",
    "/internacao/monitor": "internacao",
    "/sistema": "sistema",
}


@pytest.mark.parametrize("url", PAGINAS)
def test_paginas_abrem(client, url):
    assert client.get(url).status_code == 200


def test_internacao_mostra_paciente_demo(client):
    assert b"p000003" in client.get("/internacao").data


@pytest.mark.parametrize(("antiga", "nova"), [("/fase4", "/internacao"), ("/fase4/video", "/internacao/exames"),
                                              ("/fase4/audio", "/internacao/exames"), ("/fase4/anomalias", "/internacao"),
                                              ("/fase4/monitor", "/internacao/monitor"), ("/anomalia", "/sistema")])
def test_enderecos_antigos_redirecionam(client, antiga, nova):
    r = client.get(antiga + "?patient_id=p000003" if antiga.startswith("/fase4") else antiga)
    assert r.status_code == 301 and r.headers["Location"].split("?")[0].endswith(nova)


def test_menu_marca_a_secao_da_rota(client, app):
    for url, secao in SECAO_POR_ROTA.items():
        capturados = []

        def _capturar(sender, template, context, **extra):
            capturados.append(dict(context))

        with template_rendered.connected_to(_capturar, app):
            assert client.get(url).status_code == 200
        assert capturados[0]["secao"] == secao, url
        link = {"hoje": "/"}.get(secao, f"/{secao}")
        assert f'class="menu-link ativo" href="{link}"' in client.get(url).data.decode()


def test_rotas_ack_close(client, conn):
    reason = f"alerta ui {uuid4()}"
    emit_alert(conn, patient_id="p000003", thread_id=f"fase4-ui-{uuid4()}", severity="high",
               reason=reason, source="fase4.vitals")
    alert_id = int(conn.execute("SELECT id FROM alerts WHERE reason = ?", (reason,)).fetchone()["id"])
    assert client.post(f"/alertas/{alert_id}/ack", data={"next": "/alertas"}).status_code == 302
    assert get_alert(conn, alert_id)["status"] == "acked"
    assert client.post(f"/alertas/{alert_id}/close", data={"next": "/alertas"}).status_code == 302
    assert get_alert(conn, alert_id)["status"] == "closed"


def test_publicar_anomalias_do_paciente_de_risco(client):
    body = client.post("/api/fase4/anomalias/alertas", json={"patient_id": "p000003"}).get_json()
    assert body["prescribes"] is False and body["level"] == "high" and body["new_alerts"]
    assert client.get("/alertas").status_code == 200


def test_monitor_serie_reset_e_tick(client):
    serie = client.get("/api/fase4/monitor/serie?patient_id=p000003").get_json()
    assert serie["vitals"]
    assert client.post("/api/fase4/monitor/reset", json={"patient_id": "p000003"}).get_json()["ok"]
    assert client.get("/api/fase4/monitor/serie?patient_id=p000003").get_json()["vitals"] == []
    ponto = {"recorded_at": "2026-04-05T05:00:00+00:00", "hr": 132, "sbp": 120, "dbp": 80, "spo2": 88}
    out = client.post("/api/fase4/monitor/tick", json={"patient_id": "p000003", "vital": ponto}).get_json()
    assert out["level"] == "high" and out["prescribes"] is False


def test_audio_sem_azure_devolve_503_com_traco_vocal(client, wav_silencio):
    with open(wav_silencio, "rb") as handle:
        r = client.post("/api/fase4/audio", data={"patient_id": "p000003", "file": (handle, "c.wav")},
                        content_type="multipart/form-data")
    assert r.status_code == 503
    body = r.get_json()
    assert body["error"] == "azure_nao_configurado" and "fatigue" in body["vocal"]


def test_audio_sem_arquivo_e_400(client):
    assert client.post("/api/fase4/audio", data={}).status_code == 400


def test_video_sem_arquivo_e_400(client):
    assert client.post("/api/fase4/video/arquivo", data={}).status_code == 400


def test_token_speech_sem_azure_e_503(client):
    r = client.get("/api/azure/speech-token")
    assert r.status_code == 503 and "AZURE_SPEECH_KEY" in r.get_json()["missing"]


def test_fluxo_completo_da_consulta_ao_vivo(client, conn):
    client.post("/pacientes", data={"nome": "Caio Reis"})
    paciente_id = conn.execute("SELECT id FROM pacientes WHERE nome = 'Caio Reis'").fetchone()["id"]

    inicio = client.post("/sessoes", data={"paciente_id": paciente_id})
    assert inicio.status_code == 302 and inicio.headers["Location"].endswith("/preparar")
    sessao = inicio.headers["Location"].rstrip("/").split("/")[-2]
    assert client.get(f"/consulta/{sessao}/preparar").status_code == 200
    pagina = client.get(f"/consulta/{sessao}")
    assert pagina.status_code == 200 and b"Iniciar consulta ao vivo" in pagina.data

    base = f"/api/sessoes/{sessao}"
    medico = client.post(f"{base}/falas", json={"texto": "Teve desmaio?", "locutor": "Guest-1"})
    assert medico.status_code == 200
    client.post(f"{base}/locutores", json={"locutor": "Guest-1", "papel": "medico"})
    r = client.post(f"{base}/falas", json={"texto": "Desmaiei ontem e a dor está 8 de 10",
                                            "locutor": "Guest-2", "offset_ms": 1500})
    categorias = {p["categoria"] for p in r.get_json()["pontos"]}
    assert {"Perda de consciência", "Intensidade da dor"} <= categorias
    assert client.post(f"{base}/falas", json={"texto": "  "}).status_code == 400
    assert client.post(f"{base}/locutores", json={"locutor": "Guest-2", "papel": "x"}).status_code == 400

    dados = client.get(f"{base}/transcricao").get_json()
    assert len(dados["falas"]) == 2
    assert dados["locutores"] == {"Guest-1": "medico", "Guest-2": "paciente"}  # Guest-2 deduzido
    assert dados["locutores_detalhe"]["Guest-2"]["origem"] == "auto"
    assert client.get(f"{base}/metrica").get_json()["alertas_dor"]  # "8 de 10" abre alerta de dor

    revisao = client.get(f"/consulta/{sessao}/encerrar").data.decode()
    assert "Encerrar e ver relatório" in revisao and "Perda de consciência" in revisao
    client.post(f"/sessoes/{sessao}/encerrar")
    assert client.get(f"/consulta/{sessao}").headers["Location"].endswith(f"/consulta/{sessao}/relatorio")
    assert client.post(f"{base}/falas", json={"texto": "oi"}).status_code == 400
    rel = client.get(f"/consulta/{sessao}/relatorio")
    assert "Transcrição completa".encode() in rel.data and b"Desmaiei ontem" in rel.data
    assert "Pontos de atenção".encode() in rel.data


def test_sessao_inexistente(client):
    assert client.get("/api/sessoes/nao-existe/transcricao").status_code == 404
    assert client.get("/consulta/nao-existe").status_code == 302


def test_cadastro_abre_a_ficha_e_busca_ignora_acento(client):
    r = client.post("/pacientes", data={"nome": "Lúcia Prado"})
    assert r.status_code == 302 and "/pacientes/" in r.headers["Location"]
    ficha = client.get(r.headers["Location"]).data.decode()
    assert "Lúcia Prado" in ficha and "Iniciar consulta" in ficha and "Primeira consulta" in ficha
    assert "Lúcia Prado" in client.get("/pacientes?q=lucia").data.decode()
    assert client.post("/pacientes", data={"nome": "  "}).status_code == 400


def test_hoje_mostra_consulta_em_andamento_e_alerta_de_dor(client, conn):
    client.post("/pacientes", data={"nome": "Rui Alves"})
    paciente_id = conn.execute("SELECT id FROM pacientes WHERE nome = 'Rui Alves'").fetchone()["id"]
    sessao = client.post("/sessoes", data={"paciente_id": paciente_id}).headers["Location"].split("/")[-2]
    client.post(f"/api/sessoes/{sessao}/observacao", json={"mancando": True})
    hoje = client.get("/").data.decode()
    assert "Rui Alves" in hoje and f"/consulta/{sessao}" in hoje and "Movimentação" in hoje
    alertas = client.get("/alertas").data.decode()
    assert "Rui Alves" in alertas and "Abrir consulta" in alertas
    assert "Continuar consulta" in client.get(f"/pacientes/{paciente_id}").data.decode()


def test_sistema_lista_servicos_sem_azure(client):
    pagina = client.get("/sistema").data.decode()
    assert "Azure Speech" in pagina and "Falta no .env" in pagina and "Treinar novo modelo" in pagina


@pytest.mark.parametrize("url", ["/", "/pacientes", "/alertas", "/internacao", "/sistema"])
def test_seletor_de_tema_em_todas_as_paginas(client, url):
    html = client.get(url).data.decode()
    assert 'id="tema"' in html and 'data-tema="claro"' in html and 'data-tema="escuro"' in html
    assert 'localStorage.getItem("tema")' in html  # aplicado no <head>, antes de desenhar


def test_css_tem_tema_claro_escuro_e_automatico(client):
    css = client.get("/static/css/clinica.css").data.decode()
    assert ':root[data-tema="escuro"]' in css and ':root:not([data-tema="claro"])' in css
