"""Câmera e identificação de vozes gravadas no SQLite e pelas rotas."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from domain.atendimento.sessao import SessaoRecusada

NEUTRO = {"eyeSquintLeft": 0.15, "eyeSquintRight": 0.15, "browDownLeft": 0.05, "browDownRight": 0.05}
DOR = {"browDownLeft": 0.6, "browDownRight": 0.6, "eyeSquintLeft": 0.7, "eyeSquintRight": 0.7,
       "noseSneerLeft": 0.4, "noseSneerRight": 0.4}
TRISTE = {**NEUTRO, "mouthFrownLeft": 0.6, "mouthFrownRight": 0.6, "browInnerUp": 0.6}


@pytest.fixture()
def sessao(servicos):
    servicos.cadastro.cadastrar("pac-c", "Davi Melo")
    servicos.consulta.iniciar("ses-c", "pac-c")
    return "ses-c"


def _segundo(n: int) -> str:
    base = datetime(2026, 11, 12, 15, 0, tzinfo=timezone.utc)
    return (base + timedelta(seconds=n)).isoformat()


def _leituras(servicos, sessao, rostos, inicio=0):
    return [servicos.camera.registrar_leitura(sessao, r, registrado_em=_segundo(inicio + i)) for i, r in enumerate(rostos)]


def test_dor_sustentada_abre_um_alerta_e_um_evento(servicos, sessao):
    _leituras(servicos, sessao, [NEUTRO] * 5)
    saidas = _leituras(servicos, sessao, [DOR] * 5, inicio=5)
    assert [s["alerta_dor"] for s in saidas] == [False, False, True, False, False]
    alertas = [a for a in servicos.consulta.metrica(sessao)["alertas_dor"] if a["origem"] == "face"]
    assert len(alertas) == 1 and "PSPI" in alertas[0]["descricao_sinal"]
    tipos = [e["tipo"] for e in servicos.conversa.transcricao(sessao)["eventos_face"]]
    assert tipos.count("dor") == 1 and "expressao" in tipos


def test_expressao_vira_evento_so_quando_estavel(servicos, sessao):
    _leituras(servicos, sessao, [NEUTRO, NEUTRO, TRISTE])
    assert servicos.conversa.transcricao(sessao)["eventos_face"] == []  # uma leitura isolada não basta
    _leituras(servicos, sessao, [TRISTE, NEUTRO, NEUTRO], inicio=3)
    descricoes = [e["descricao"] for e in servicos.conversa.transcricao(sessao)["eventos_face"]]
    assert descricoes == ["Rosto do paciente: triste", "Rosto do paciente voltou ao neutro"]


def test_leitura_atualiza_card_e_expressao_recente(servicos, sessao):
    _leituras(servicos, sessao, [NEUTRO] * 3 + [TRISTE] * 2)
    assert servicos.consulta.metrica(sessao)["imagem"]["face"] == "triste"
    assert servicos.camera.expressao_recente(sessao, agora=_segundo(6)) == "triste"
    assert servicos.camera.expressao_recente(sessao, agora=_segundo(60)) == ""  # leitura velha não vale para a fala
    assert servicos.conversa.transcricao(sessao)["face_atual"]["expressao"] == "triste"


def test_leitura_recusada_sem_dados_ou_sessao_encerrada(servicos, sessao):
    with pytest.raises(ValueError):
        servicos.camera.registrar_leitura(sessao, {})
    servicos.consulta.encerrar_sessao(sessao)
    with pytest.raises(SessaoRecusada):
        servicos.camera.registrar_leitura(sessao, NEUTRO)


def test_vozes_sao_identificadas_sozinhas_e_pergunta_do_medico_nao_vira_ponto(servicos, sessao):
    servicos.conversa.registrar_fala(sessao, "Bom dia, o que trouxe a senhora aqui? Tem dor no peito?", locutor="Guest-1")
    servicos.conversa.registrar_fala(sessao, "Doutor, estou com dor no peito faz dois dias.", locutor="Guest-2")
    servicos.conversa.registrar_fala(sessao, "Vou pedir um eletrocardiograma.", locutor="Guest-1")
    dados = servicos.conversa.transcricao(sessao)
    assert dados["locutores"] == {"Guest-1": "medico", "Guest-2": "paciente"}
    assert all(info["origem"] == "auto" for info in dados["locutores_detalhe"].values())
    falas_com_ponto = {p["ordem"] for p in dados["pontos"]}
    assert falas_com_ponto == {2}  # a pergunta do médico (fala 1) não entra
    relatos = [a for a in servicos.consulta.metrica(sessao)["alertas_dor"] if a["origem"] == "relato"]
    assert len(relatos) == 1


def test_resumo_clinico_da_conversa(servicos, sessao):
    servicos.conversa.registrar_fala(sessao, "Bom dia, o que trouxe a senhora? Tem diabetes?", locutor="Guest-1")
    servicos.conversa.registrar_fala(sessao, "Doutor, tenho hipertensão, tomo losartana 50 mg e não tenho diabetes.", locutor="Guest-2")
    out = servicos.conversa.registrar_fala(sessao, "Vou pedir um eletrocardiograma.", locutor="Guest-1")
    assert ("Exame", "eletrocardiograma") in {(e["tipo"], e["texto"]) for e in out["fala"]["entidades"]}
    dados = servicos.conversa.transcricao(sessao)
    assert dados["falas"][1]["entidades"]  # cada fala traz as entidades para sublinhar na tela
    grupos = {g["tipo"]: {i["texto"]: i for i in g["itens"]} for g in dados["resumo_clinico"]}
    assert set(grupos["Medicamento"]) == {"losartana"} and "50 mg" in grupos["Dose / posologia"]
    assert grupos["Doença / condição"]["diabetes"]["negada"] is True  # a pergunta do médico não entra
    assert grupos["Doença / condição"]["diabetes"]["falas"] == [2]
    assert grupos["Exame"]["eletrocardiograma"]["medico"] is True


def test_correcao_manual_vence_o_automatico(servicos, sessao):
    servicos.conversa.registrar_fala(sessao, "Bom dia, o que trouxe a senhora?", locutor="Guest-1")
    servicos.conversa.registrar_fala(sessao, "Doutor, estou com febre.", locutor="Guest-2")
    servicos.conversa.definir_papel(sessao, "Guest-1", "acompanhante")
    servicos.conversa.registrar_fala(sessao, "Vou pedir exames.", locutor="Guest-1")
    dados = servicos.conversa.transcricao(sessao)
    assert dados["locutores_detalhe"]["Guest-1"] == {"papel": "acompanhante", "origem": "manual", "confianca": None}


def test_fala_guarda_expressao_do_rosto(servicos, sessao):
    agora = datetime.now(timezone.utc).replace(microsecond=0)
    for i in range(3):
        servicos.camera.registrar_leitura(sessao, TRISTE, registrado_em=(agora - timedelta(seconds=3 - i)).isoformat())
    out = servicos.conversa.registrar_fala(sessao, "Estou muito desanimada.", locutor="Guest-2")
    assert out["fala"]["expressao_face"] == "triste"


def test_rota_face(client, servicos, sessao):
    r = client.post(f"/api/sessoes/{sessao}/face", json={"blendshapes": {**NEUTRO, "lixo": "x", "fora": 7}})
    assert r.status_code == 200
    body = r.get_json()
    assert body["leitura"]["expressao"] == "neutra" and "scores" in body["leitura"]
    assert client.post(f"/api/sessoes/{sessao}/face", json={}).status_code == 400
    assert client.post("/api/sessoes/nao-existe/face", json={"blendshapes": NEUTRO}).status_code == 400


def test_pagina_tem_camera_e_conversa(client, servicos, sessao):
    html = client.get(f"/consulta/{sessao}").data.decode()
    assert 'id="btn-camera"' in html and "camera_facial.js" in html and "consulta_ao_vivo.js" in html
    assert 'id="resumo-clinico"' in html
    assert client.get("/static/js/camera_facial.js").status_code == 200
