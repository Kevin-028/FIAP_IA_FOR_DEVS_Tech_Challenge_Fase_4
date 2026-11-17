"""Marcas de atenção pela Web: gravar na suspeita, veredito depois, listar, assistir e classificar."""
from __future__ import annotations

import threading
from io import BytesIO

import pytest

from application.portas import FilaDeTrabalho
from tests.memoria import Estagio2Falso
from web.injecao import servico

JPEG = b"\xff\xd8\xff\xe0" + b"0" * 64


@pytest.fixture(autouse=True)
def armazem_temporario(tmp_path, monkeypatch):
    pasta = tmp_path / "duvidas"
    monkeypatch.setattr("infrastructure.persistencia.armazem_quadros.PASTA_PADRAO", str(pasta))
    return pasta


@pytest.fixture()
def consulta(servicos):
    servicos.cadastro.cadastrar("pac-r", "Rita Lopes")
    servicos.consulta.iniciar("ses-r", "pac-r")
    return "ses-r"


DOR_AUS = {"AU04": 0.8, "AU06": 0.4, "AU07": 0.9, "AU09": 0.6, "AU10": 0.3, "AU43": 0.7}
NEUTRO_AUS = {"AU04": 0.05, "AU07": 0.2}
COM_VALIDADOR = pytest.mark.parametrize("estagio2", [Estagio2Falso(
    [aus for rosto in (DOR_AUS, NEUTRO_AUS) for aus in (NEUTRO_AUS, rosto, rosto, rosto)])])


@pytest.fixture()
def fila(app):
    """A fila real do app (thread em segundo plano), para segurar e soltar o validador nos testes."""
    with app.app_context():
        return servico(FilaDeTrabalho)


def _segurar(fila):
    liberar = threading.Event()
    fila.enfileirar(lambda: liberar.wait(5), "segura a fila")
    return liberar


def _enviar(client, n=8, duracao="2.5", sessao="ses-r", marca=0, neutro=True):
    dados = {"duracao_s": duracao,
             "quadros": [(BytesIO(JPEG + bytes([marca, i])), f"{i}.jpg", "image/jpeg") for i in range(n)]}
    if neutro:
        dados["neutro"] = (BytesIO(JPEG + b"N"), "neutro.jpg", "image/jpeg")
    return client.post(f"/api/sessoes/{sessao}/duvidas", data=dados, content_type="multipart/form-data")


def _marcas(client):
    return {m["id"]: m for m in client.get("/api/sessoes/ses-r/duvidas").get_json()}


def test_fluxo_de_revisao(client, consulta, armazem_temporario, fila):
    liberar = _segurar(fila)
    r = _enviar(client, n=40)
    assert r.status_code == 200 and r.get_json()["avaliando"] is True and r.get_json()["na_fila"] == 2
    duvida_id = r.get_json()["id"]
    assert (armazem_temporario / duvida_id / "39.jpg").is_file()  # o recorte inteiro, não só 3 quadros
    lista = client.get("/revisao").data.decode()
    assert "Rita Lopes" in lista and "Avaliando…" in lista and "1 marcas para revisar" in lista
    liberar.set()
    assert fila.aguardar(timeout=5)
    imagem = client.get(f"/revisao/{duvida_id}/quadros/0.jpg")
    assert imagem.status_code == 200 and imagem.mimetype == "image/jpeg" and "no-store" in imagem.headers["Cache-Control"]
    assert client.get(f"/revisao/{duvida_id}/quadros/99.jpg").status_code == 404
    assert "Sua classificação" in client.get(f"/revisao/{duvida_id}").data.decode()
    salvo = client.post(f"/revisao/{duvida_id}", data={"face": "6", "categoria": "dor", "observacao": "careta"})
    assert salvo.status_code == 302 and salvo.headers["Location"].endswith("/revisao")
    assert "Rita Lopes" in client.get("/revisao?aba=classificadas").data.decode()


@COM_VALIDADOR
def test_marcas_seguidas_entram_na_fila_e_cada_uma_recebe_o_seu_veredito(client, consulta, fila, estagio2):
    liberar = _segurar(fila)
    primeira = _enviar(client, marca=1).get_json()["id"]
    segunda = _enviar(client, marca=2).get_json()["id"]
    assert {m["veredito"] for m in _marcas(client).values()} == {"avaliando"}  # disponíveis antes do validador
    liberar.set()
    assert fila.aguardar(timeout=5)
    marcas = _marcas(client)
    assert marcas[primeira]["veredito_texto"] == "Validador confirmou dor · face 10"
    assert marcas[segunda]["veredito"] == "descartada"
    assert estagio2.chamadas[-2:] == [4, 4]
    assert [[q[-1] for q in v[1:]] for v in estagio2.vistas[-2:]] == [[3, 4, 5], [3, 4, 5]]  # centro do recorte
    assert [{q[-2] for q in v[1:]} for v in estagio2.vistas[-2:]] == [{1}, {2}]  # carimbo: cada marca, o seu recorte


def test_sem_validador_a_marca_fica_sem_resultado(client, consulta, fila):
    duvida_id = _enviar(client, neutro=False).get_json()["id"]
    assert fila.aguardar(timeout=5)
    assert _marcas(client)[duvida_id]["veredito_texto"] == "Validador sem resultado"


def test_recorte_fora_das_regras_e_recusado(client, consulta, armazem_temporario):
    assert _enviar(client, n=1).status_code == 400
    assert _enviar(client, duracao="5").status_code == 400
    assert _enviar(client, sessao="nao-existe").status_code == 400
    assert not armazem_temporario.exists() or not any(p.suffix != ".parcial" for p in armazem_temporario.iterdir())


def test_classificacao_invalida_volta_com_erro(client, consulta):
    duvida_id = _enviar(client).get_json()["id"]
    r = client.post(f"/revisao/{duvida_id}", data={"face": "5", "categoria": "dor"})
    assert r.status_code == 302 and "erro=" in r.headers["Location"]


def test_marcas_da_consulta_para_o_medico(client, consulta):
    duvida_id = _enviar(client).get_json()["id"]
    lista = client.get("/api/sessoes/ses-r/duvidas").get_json()
    assert [d["id"] for d in lista] == [duvida_id] and lista[0]["pendente"] is True and lista[0]["quadros"] == 8
    assert client.get("/api/sessoes/outra/duvidas").get_json() == []
    assert 'id="duvidas-consulta"' in client.get("/consulta/ses-r").data.decode()
