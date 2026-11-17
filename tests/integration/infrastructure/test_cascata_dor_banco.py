"""Cascata de dor gravada no SQLite e pelas rotas (estágio 2 falso; o Py-Feat real fica em test_modelos_reais)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from io import BytesIO

import pytest

from domain.atendimento.sessao import SessaoRecusada
from tests.memoria import Estagio2Falso

NEUTRO = {"eyeSquintLeft": 0.15, "eyeSquintRight": 0.15, "browDownLeft": 0.05, "browDownRight": 0.05}
LEVE = {**NEUTRO, "eyeSquintLeft": 0.6, "eyeSquintRight": 0.6}
DOR = {"browDownLeft": 0.6, "browDownRight": 0.6, "eyeSquintLeft": 0.7, "eyeSquintRight": 0.7,
       "noseSneerLeft": 0.4, "noseSneerRight": 0.4}
CONFIRMADO = {"detector": "falso", "pspi": 9.0, "pspi_base": 1.0, "dor_relativa": 8.0, "wong_baker": 8,
              "confirmado": True, "faces_avaliadas": 3}
DESCARTADO = {**CONFIRMADO, "pspi": 1.5, "dor_relativa": 0.5, "wong_baker": 0, "confirmado": False}
DOR_AUS = {"AU04": 0.8, "AU06": 0.4, "AU07": 0.9, "AU09": 0.6, "AU10": 0.3, "AU43": 0.7}
JPEG = b"\xff\xd8\xff\xe0" + b"0" * 64


class Estagio2Constante:
    """Estágio 2 instalado que vê sempre as mesmas AUs."""

    nome = "falso"

    def __init__(self, aus):
        self.aus = aus

    def disponivel(self):
        return True

    def avaliar(self, imagens):
        return [self.aus for _ in imagens]


@pytest.fixture()
def estagio2():
    """Neste arquivo o estágio 2 está instalado; quem precisa do contrário parametriza."""
    return Estagio2Constante(DOR_AUS)


SEM_ESTAGIO2 = pytest.mark.parametrize("estagio2", [Estagio2Falso(disponivel=False)])


@pytest.fixture()
def sessao(servicos):
    servicos.cadastro.cadastrar("pac-k", "Lia Prado")
    servicos.consulta.iniciar("ses-k", "pac-k")
    return "ses-k"


def _segundo(n: int) -> str:
    return (datetime(2026, 11, 15, 10, 0, tzinfo=timezone.utc) + timedelta(seconds=n)).isoformat()


def _leituras(servicos, sessao, rostos, inicio=0):
    return [servicos.camera.registrar_leitura(sessao, r, registrado_em=_segundo(inicio + i))
            for i, r in enumerate(rostos)]


def _alertas_face(servicos, sessao):
    return [a for a in servicos.consulta.metrica(sessao)["alertas_dor"] if a["origem"] == "face"]


def _arquivos(n=3, neutro=True):
    dados = {"suspeitos": [(BytesIO(JPEG), f"s{i}.jpg", "image/jpeg") for i in range(n)]}
    if neutro:
        dados["neutro"] = (BytesIO(JPEG), "n.jpg", "image/jpeg")
    return dados


def test_leitura_traz_face_wong_baker(servicos, sessao):
    saidas = _leituras(servicos, sessao, [NEUTRO] * 5 + [DOR])
    assert saidas[0]["leitura"]["wong_baker"] == 0 and saidas[-1]["leitura"]["wong_baker"] >= 4


def test_dor_acima_do_nivel_5_vira_suspeita_sem_abrir_alerta(servicos, sessao):
    _leituras(servicos, sessao, [NEUTRO] * 5)
    assert not any(s["suspeita"] for s in _leituras(servicos, sessao, [LEVE] * 3, inicio=5))
    saidas = _leituras(servicos, sessao, [DOR] * 3, inicio=8)
    assert [s["suspeita"] for s in saidas] == [False, False, True]
    assert _alertas_face(servicos, sessao) == []  # com estágio 2, quem abre o alerta é a confirmação


@SEM_ESTAGIO2
def test_sem_estagio2_mantem_o_alerta_do_estagio1(servicos, sessao):
    _leituras(servicos, sessao, [NEUTRO] * 5)
    saidas = _leituras(servicos, sessao, [DOR] * 3, inicio=5)
    assert saidas[-1]["alerta_dor"] is True and saidas[-1]["suspeita"] is True  # marca gravada mesmo sem validador


def test_confirmacao_abre_um_alerta_e_cada_suspeita_continua_marcada(servicos, sessao):
    _leituras(servicos, sessao, [NEUTRO] * 5 + [DOR] * 3)
    out = servicos.cascata.registrar_confirmacao(sessao, CONFIRMADO, registrado_em=_segundo(8))
    assert out["alerta_dor"] is True and out["confirmacao"]["wong_baker"] == 8
    alertas = _alertas_face(servicos, sessao)
    assert len(alertas) == 1 and "Wong-Baker 8" in alertas[0]["descricao_sinal"]
    assert servicos.cascata.registrar_confirmacao(sessao, CONFIRMADO, registrado_em=_segundo(9))["alerta_dor"] is False
    seguintes = _leituras(servicos, sessao, [DOR] * 3, inicio=9)
    assert seguintes[-1]["suspeita"] is True  # com alerta aberto, a suspeita ainda vira marca para o médico
    assert len(_alertas_face(servicos, sessao)) == 1


def test_descarte_fica_registrado_sem_alerta_e_a_suspeita_segue_marcada(servicos, sessao):
    _leituras(servicos, sessao, [NEUTRO] * 5 + [DOR] * 3)
    out = servicos.cascata.registrar_confirmacao(sessao, DESCARTADO, registrado_em=_segundo(8))
    assert out["alerta_dor"] is False and out["confirmacao"]["confirmado"] is False
    assert _alertas_face(servicos, sessao) == []
    assert _leituras(servicos, sessao, [DOR], inicio=9)[0]["suspeita"] is True  # o validador não silencia a câmera


def test_confirmacao_recusada_com_dados_invalidos_ou_sessao_encerrada(servicos, sessao):
    with pytest.raises(ValueError):
        servicos.cascata.registrar_confirmacao(sessao, {**CONFIRMADO, "wong_baker": 5})
    servicos.consulta.encerrar_sessao(sessao)
    with pytest.raises(SessaoRecusada):
        servicos.cascata.registrar_confirmacao(sessao, CONFIRMADO)


def test_autorrelato_guarda_a_estimativa_mais_recente(servicos, sessao):
    _leituras(servicos, sessao, [NEUTRO] * 5)
    sem_confirmacao = servicos.cascata.registrar_autorrelato(sessao, 4, registrado_em=_segundo(5))
    assert sem_confirmacao["estimado"] == 0 and sem_confirmacao["origem_estimativa"] == "estagio1"
    servicos.cascata.registrar_confirmacao(sessao, CONFIRMADO, registrado_em=_segundo(6))
    com_confirmacao = servicos.cascata.registrar_autorrelato(sessao, 6, registrado_em=_segundo(7))
    assert com_confirmacao["estimado"] == 8 and com_confirmacao["origem_estimativa"] == "estagio2"
    assert com_confirmacao["wong_baker"] == 6


def test_autorrelato_sem_leitura_e_valor_invalido(servicos, sessao):
    out = servicos.cascata.registrar_autorrelato(sessao, 10)
    assert out["estimado"] is None and out["origem_estimativa"] is None
    for invalido in (3, -2, 12, "4", None, True):
        with pytest.raises(ValueError):
            servicos.cascata.registrar_autorrelato(sessao, invalido)


def test_rota_confirmar_com_estagio2(client, servicos, sessao):
    r = client.post(f"/api/sessoes/{sessao}/face/confirmar", data=_arquivos(), content_type="multipart/form-data")
    assert r.status_code == 200
    body = r.get_json()
    assert body["confirmacao"]["detector"] == "falso" and body["confirmacao"]["pspi_base"] == 3.0  # base com teto
    assert body["alerta_dor"] is True and body["confirmacao"]["wong_baker"] == 10


def test_rota_confirmar_recusa_entradas_ruins(client, servicos, sessao):
    url = f"/api/sessoes/{sessao}/face/confirmar"
    assert client.post(url, data={}, content_type="multipart/form-data").status_code == 400
    assert client.post(url, data=_arquivos(n=6), content_type="multipart/form-data").status_code == 400
    texto = {"suspeitos": [(BytesIO(b"nao e imagem"), "s.txt", "text/plain")]}
    assert client.post(url, data=texto, content_type="multipart/form-data").status_code == 400
    grande = {"suspeitos": [(BytesIO(JPEG + b"0" * 300_000), "s.jpg", "image/jpeg")]}
    assert client.post(url, data=grande, content_type="multipart/form-data").status_code == 400
    outra = client.post("/api/sessoes/nao-existe/face/confirmar", data=_arquivos(), content_type="multipart/form-data")
    assert outra.status_code == 400


@SEM_ESTAGIO2
def test_rota_confirmar_sem_estagio2_responde_503(client, servicos, sessao):
    r = client.post(f"/api/sessoes/{sessao}/face/confirmar", data=_arquivos(), content_type="multipart/form-data")
    assert r.status_code == 503


def test_rota_face_informa_estagio2_e_suspeita(client, servicos, sessao):
    body = client.post(f"/api/sessoes/{sessao}/face", json={"blendshapes": NEUTRO}).get_json()
    assert body["estagio2"] is True and body["suspeita"] is False and "wong_baker" in body["leitura"]


def test_rota_autorrelato(client, servicos, sessao):
    url = f"/api/sessoes/{sessao}/autorrelato"
    assert client.post(url, json={"wong_baker": 6}).get_json()["wong_baker"] == 6
    assert client.post(url, json={"wong_baker": 7}).status_code == 400
    assert client.post("/api/sessoes/nao-existe/autorrelato", json={"wong_baker": 2}).status_code == 400


def test_pagina_mostra_escala_wong_baker(client, servicos, sessao):
    html = client.get(f"/consulta/{sessao}").data.decode()
    assert 'id="wong-baker"' in html and html.count('class="wb-face') == 6
