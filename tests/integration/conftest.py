"""Integração: cada teste usa um SQLite temporário já populado, nunca o banco do app.

O injector de teste é o mesmo da Web (web.dependencias), só que com o banco temporário e o
estágio 2 trocado por um falso (desligado por padrão, como numa máquina sem Py-Feat).
"""
from __future__ import annotations

import os
import shutil
from types import SimpleNamespace

import pytest

AZURE_VARS = ("AZURE_SPEECH_KEY", "AZURE_SPEECH_REGION", "AZURE_LANGUAGE_KEY", "AZURE_LANGUAGE_ENDPOINT")


@pytest.fixture(scope="session")
def banco_modelo(tmp_path_factory) -> str:
    """Banco populado uma vez (seed do plantão); cada teste recebe uma cópia."""
    from infrastructure.persistencia.banco import connect
    from infrastructure.persistencia.seed import apply

    caminho = str(tmp_path_factory.mktemp("seed") / "modelo.db")
    conn = connect(caminho)
    apply(conn)
    conn.commit()
    conn.close()
    return caminho


@pytest.fixture()
def caminho_banco(banco_modelo, tmp_path) -> str:
    caminho = str(tmp_path / "hospital.db")
    shutil.copy(banco_modelo, caminho)
    return caminho


@pytest.fixture(autouse=True)
def sem_azure(request, monkeypatch):
    """Sem o marcador azure, nenhum teste pode alcançar o Azure por acidente."""
    if "azure" in request.keywords:
        return
    for nome in AZURE_VARS:
        monkeypatch.delenv(nome, raising=False)


@pytest.fixture()
def conn(caminho_banco):
    """Conexão própria do teste, para conferir o que os casos de uso gravaram."""
    from infrastructure.persistencia.banco import connect, init_db

    db = connect(caminho_banco)
    init_db(db)
    yield db
    db.close()


@pytest.fixture()
def estagio2():
    from tests.memoria import Estagio2Falso

    return Estagio2Falso(disponivel=False)


@pytest.fixture()
def analisador():
    """None = adaptador real do Azure (sem chave nos testes); um teste pode parametrizar um falso."""
    return None


def _modulo_de_teste(estagio2, analisador=None):
    from injector import InstanceProvider, Module

    from application.atendimento.portas import AnalisadorDeTexto, Estagio2

    class ModuloDeTeste(Module):
        def configure(self, binder):
            binder.bind(Estagio2, to=InstanceProvider(estagio2))
            if analisador is not None:
                binder.bind(AnalisadorDeTexto, to=InstanceProvider(analisador))

    return ModuloDeTeste()


@pytest.fixture()
def servicos(caminho_banco, estagio2, analisador):
    """Casos de uso reais sobre o SQLite temporário, montados pelo injector da Web."""
    from application.anomalia.servico import ServicoAnomalia
    from application.atendimento.servico_cadastro import ServicoCadastro
    from application.atendimento.servico_camera import ServicoCamera
    from application.atendimento.servico_cascata import ServicoCascataDor
    from application.atendimento.servico_consulta import ServicoConsulta
    from application.atendimento.servico_conversa import ServicoConversa
    from application.plantao.servico import ServicoAlertasPlantao, ServicoPlantao
    from infrastructure.persistencia.conexao import ProvedorDeConexao
    from web.dependencias import criar_injetor

    injetor = criar_injetor(caminho_banco, _modulo_de_teste(estagio2, analisador))
    yield SimpleNamespace(
        injetor=injetor,
        cadastro=injetor.get(ServicoCadastro), consulta=injetor.get(ServicoConsulta),
        camera=injetor.get(ServicoCamera), cascata=injetor.get(ServicoCascataDor),
        conversa=injetor.get(ServicoConversa), anomalia=injetor.get(ServicoAnomalia),
        plantao=injetor.get(ServicoPlantao), alertas=injetor.get(ServicoAlertasPlantao),
    )
    injetor.get(ProvedorDeConexao).fechar()


@pytest.fixture()
def app(caminho_banco, estagio2, analisador):
    from web.app import create_app

    aplicacao = create_app(caminho_banco, _modulo_de_teste(estagio2, analisador))
    aplicacao.config.update(TESTING=True)
    return aplicacao


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def wav_silencio(tmp_path) -> str:
    import wave

    import numpy as np

    caminho = str(tmp_path / "silencio.wav")
    with wave.open(caminho, "w") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(16000)
        handle.writeframes(np.zeros(16000, dtype=np.int16).tobytes())
    return caminho


@pytest.fixture(scope="session")
def foto_com_pessoas():
    cv2 = pytest.importorskip("cv2")
    ultralytics = pytest.importorskip("ultralytics")
    caminho = os.path.join(os.path.dirname(ultralytics.__file__), "assets", "bus.jpg")
    if not os.path.isfile(caminho):
        pytest.skip("imagem de exemplo do ultralytics ausente")
    return cv2.imread(caminho)
